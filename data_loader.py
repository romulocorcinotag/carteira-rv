"""
Carregamento de dados de carteira para fundos RV.
Fontes: XMLs locais (prioridade) e CVM API (fallback).

MODO CLOUD: Se data/posicoes_consolidado.parquet existir, lê diretamente
dos parquets pré-exportados (sem necessidade de Google Drive ou CVM API).
Use export_data.py para gerar os parquets localmente.
"""

import os
import re
import io
import zipfile
from datetime import datetime, timedelta
from collections import defaultdict
import xml.etree.ElementTree as ET

import pandas as pd
import numpy as np
import requests
import streamlit as st

from sector_map import classificar_setor

# ──────────────────────────────────────────────────────────────────────────────
# Caminhos
# ──────────────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_SCRIPT_DIR, "data")
BASE_GERAL_PATH = r"G:\Drives compartilhados\Gestao_Base_Dados\Acompanhamento\Base Geral.xlsm"
XML_BASE_PATH = r"G:\Drives compartilhados\Arquivos_XML_Fechamento"
CACHE_DIR = os.path.join(_SCRIPT_DIR, "cache")
CVM_ZIP_URL = "https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/cda_fi_{yyyymm}.zip"

NS_GALGO = "http://www.sistemagalgo.com/SchemaPosicaoAtivos"
NS_DOC = "urn:iso:std:iso:20022:tech:xsd:semt.003.001.04"

# Detectar modo cloud: se data/ tem os parquets pré-exportados, usar eles
# Exceto se FORCE_LOCAL_MODE está setado (usado pelo export_data.py)
CLOUD_MODE = (
    os.path.exists(os.path.join(DATA_DIR, "posicoes_consolidado.parquet"))
    and os.environ.get("FORCE_LOCAL_MODE") != "1"
)


# ──────────────────────────────────────────────────────────────────────────────
# Utilitários
# ──────────────────────────────────────────────────────────────────────────────
def _normalizar_cnpj(cnpj: str) -> str:
    """Remove formatação, retorna 14 dígitos."""
    if cnpj is None:
        return ""
    return re.sub(r'\D', '', str(cnpj)).zfill(14)


# ──────────────────────────────────────────────────────────────────────────────
# Carregar fundos RV da Base Geral
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def carregar_fundos_rv() -> pd.DataFrame:
    """Lê aba RV do Base Geral.xlsm (local) ou parquet (cloud)."""
    # Modo cloud: ler do parquet pré-exportado
    parquet_path = os.path.join(DATA_DIR, "fundos_rv.parquet")
    if CLOUD_MODE or not os.path.exists(BASE_GERAL_PATH):
        if os.path.exists(parquet_path):
            return pd.read_parquet(parquet_path)
        raise FileNotFoundError("Nenhuma fonte de dados de fundos disponível. Execute export_data.py localmente.")

    # Modo local: ler do Excel
    import openpyxl
    wb = openpyxl.load_workbook(BASE_GERAL_PATH, read_only=True, data_only=True)
    ws = wb["RV"]
    fundos = []
    for row in ws.iter_rows(min_row=2, max_col=9, values_only=True):
        if row[0] is None:
            break
        fundos.append({
            "nome": row[0],
            "cnpj": row[1],
            "categoria": row[2],
            "tier": row[3],
            "master": row[4],
            "cnpj_foco": row[6],
            "enquadramento": row[7],
            "geri": row[8],
        })
    wb.close()
    df = pd.DataFrame(fundos)
    df["cnpj_norm"] = df["cnpj"].apply(_normalizar_cnpj)
    df["cnpj_foco_norm"] = df["cnpj_foco"].apply(_normalizar_cnpj)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Detectar formato XML
# ──────────────────────────────────────────────────────────────────────────────
def _detect_xml_format(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        head = f.read(1000)
    if "arquivoposicao_4_01" in head:
        return "old"
    if "GalgoAssBalStmt" in head or "semt.003.001" in head:
        return "new"
    return "unknown"


# ──────────────────────────────────────────────────────────────────────────────
# Parse XML formato antigo (arquivoposicao_4_01)
# ──────────────────────────────────────────────────────────────────────────────
def _parse_xml_old(filepath: str) -> dict | None:
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        fundo = root.find("fundo")
        if fundo is None:
            return None
        header = fundo.find("header")
        if header is None:
            return None

        cnpj = _normalizar_cnpj(header.findtext("cnpj", ""))
        dt_str = header.findtext("dtposicao", "")
        pl = float(header.findtext("patliq", "0") or "0")
        dt = datetime.strptime(dt_str, "%Y%m%d") if dt_str else None

        acoes = []
        for acao in fundo.findall("acoes"):
            cod = acao.findtext("codativo", "")
            valor = float(acao.findtext("valorfindisp", "0") or "0")
            if cod and valor > 0:
                acoes.append({"ativo": cod.strip().upper(), "valor": valor})

        return {"cnpj": cnpj, "data": dt, "pl": pl, "acoes": acoes}
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Parse XML formato novo (ISO 20022 / Galgo)
# ──────────────────────────────────────────────────────────────────────────────
def _parse_xml_new(filepath: str) -> dict | None:
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        ns = {"g": NS_GALGO, "d": NS_DOC}

        # Navegar: BsnsMsg/Document/SctiesBalAcctgRpt
        bsns = root.find("g:BsnsMsg", ns)
        if bsns is None:
            return None
        doc = bsns.find("d:Document", ns)
        if doc is None:
            return None
        rpt = doc.find("d:SctiesBalAcctgRpt", ns)
        if rpt is None:
            return None

        # Data
        dt_text = rpt.findtext("d:StmtGnlDtls/d:StmtDtTm/d:Dt", "", ns)
        dt = datetime.strptime(dt_text, "%Y-%m-%d") if dt_text else None

        # PL e CNPJ do fundo: BalForAcct
        bal_acct = rpt.find("d:BalForAcct", ns)
        if bal_acct is None:
            return None

        # CNPJ do fundo
        cnpj = ""
        fin_id = bal_acct.find("d:FinInstrmId", ns)
        if fin_id is not None:
            for othr in fin_id.findall("d:OthrId", ns):
                tp_cd = othr.findtext("d:Tp/d:Cd", "", ns)
                if tp_cd == "CNPJ":
                    cnpj = _normalizar_cnpj(othr.findtext("d:Id", "", ns))
                    break

        # PL
        pl_text = ""
        acct_amts = bal_acct.find("d:AcctBaseCcyAmts", ns)
        if acct_amts is not None:
            amt_el = acct_amts.find("d:HldgVal/d:Amt", ns)
            if amt_el is not None:
                pl_text = amt_el.text or ""
        pl = float(pl_text) if pl_text else 0.0

        # Posições em ações: BalForSubAcct (dentro de SubAcctDtls)
        acoes = []
        all_subs = []
        # Podem estar direto no rpt ou dentro de SubAcctDtls
        all_subs.extend(rpt.findall("d:BalForSubAcct", ns))
        for sad in rpt.findall("d:SubAcctDtls", ns):
            all_subs.extend(sad.findall("d:BalForSubAcct", ns))

        for sub in all_subs:
            fin = sub.find("d:FinInstrmId", ns)
            if fin is None:
                continue

            # Verificar se é ação direta (EQUI na TABELA NIVEL 1, sem ser LOAN)
            ticker = ""
            is_equi = False
            is_loan = False
            for othr in fin.findall("d:OthrId", ns):
                tp_cd = othr.findtext("d:Tp/d:Cd", "", ns)
                tp_prtry = othr.findtext("d:Tp/d:Prtry", "", ns)
                id_val = othr.findtext("d:Id", "", ns)

                if tp_cd == "BVMF":
                    ticker = id_val.strip().upper()
                if tp_prtry == "TABELA NIVEL 1" and id_val == "EQUI":
                    is_equi = True
                if tp_prtry == "TABELA NIVEL 1" and id_val == "LOAN":
                    is_loan = True
                if tp_prtry == "CONTRATO BTC":
                    is_loan = True

            if not ticker or not is_equi or is_loan:
                continue

            # Verificar LONG
            lng = sub.findtext("d:AggtBal/d:ShrtLngInd", "", ns)
            if lng != "LONG":
                continue

            # Valor
            sub_amts = sub.find("d:AcctBaseCcyAmts", ns)
            if sub_amts is None:
                continue
            amt_el = sub_amts.find("d:HldgVal/d:Amt", ns)
            valor = float(amt_el.text) if amt_el is not None and amt_el.text else 0.0

            if valor > 0:
                acoes.append({"ativo": ticker, "valor": valor})

        return {"cnpj": cnpj, "data": dt, "pl": pl, "acoes": acoes}
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Descobrir e mapear XMLs por CNPJ
# ──────────────────────────────────────────────────────────────────────────────
def _listar_xmls() -> list[str]:
    """Lista todos os XMLs da pasta de fechamento (otimizado para rede)."""
    xmls = []
    if not os.path.exists(XML_BASE_PATH):
        return xmls
    # Iterar por ano -> mês (evita walk profundo)
    try:
        anos = [d for d in os.listdir(XML_BASE_PATH) if d.isdigit() and len(d) == 4]
    except OSError:
        return xmls
    for ano in sorted(anos):
        ano_path = os.path.join(XML_BASE_PATH, ano)
        try:
            meses = os.listdir(ano_path)
        except OSError:
            continue
        for mes in sorted(meses):
            mes_path = os.path.join(ano_path, mes)
            if not os.path.isdir(mes_path):
                continue
            try:
                for f in os.listdir(mes_path):
                    if f.lower().endswith(".xml") and not f.startswith("~"):
                        xmls.append(os.path.join(mes_path, f))
            except OSError:
                continue
    return xmls


def _cnpj_from_filename(filename: str) -> str:
    """Tenta extrair CNPJ do prefixo FD/FC/CL no nome do arquivo."""
    base = os.path.basename(filename)
    m = re.match(r'^(?:FD|FC|CL)(\d{14})_', base)
    if m:
        return m.group(1)
    return ""


@st.cache_data(ttl=3600, show_spinner="Mapeando XMLs locais...")
def _descobrir_xmls_por_cnpj(cnpjs_interesse: tuple) -> dict:
    """
    Retorna {cnpj_norm: [lista de paths XML]} para CNPJs de interesse.
    """
    cnpjs_set = set(cnpjs_interesse)
    all_xmls = _listar_xmls()

    # Primeiro: tentar extrair CNPJ do filename (rápido)
    cnpj_to_files = defaultdict(list)
    unmatched = []

    for path in all_xmls:
        cnpj_fn = _cnpj_from_filename(path)
        if cnpj_fn and cnpj_fn in cnpjs_set:
            cnpj_to_files[cnpj_fn].append(path)
        else:
            unmatched.append(path)

    # Segundo: para não-matched do formato antigo (YYYYMMDD_NAME.xml),
    # tentar leitura rápida do header só se o arquivo parece ser formato antigo
    # Limitar a um número razoável para evitar lentidão em rede
    old_format_unmatched = [p for p in unmatched if re.match(r'^\d{8}_', os.path.basename(p))]
    for path in old_format_unmatched:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(2000)
            m = re.search(r'<cnpj>(\d{10,14})</cnpj>', head)
            if m:
                cnpj = m.group(1).zfill(14)
                if cnpj in cnpjs_set:
                    cnpj_to_files[cnpj].append(path)
        except Exception:
            pass

    # Ordenar por data no filename
    for cnpj in cnpj_to_files:
        cnpj_to_files[cnpj].sort()

    return dict(cnpj_to_files)


# ──────────────────────────────────────────────────────────────────────────────
# Carregar todos os dados XML
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Processando XMLs locais...")
def carregar_dados_xml(cnpjs_interesse: tuple) -> pd.DataFrame:
    """Parseia todos os XMLs e retorna DataFrame unificado.

    Deduplicação: para cada (cnpj, data), mantém apenas o XML com maior PL
    (que tende a ser o arquivo mais completo/final vs prévia).
    """
    cnpj_xmls = _descobrir_xmls_por_cnpj(cnpjs_interesse)

    # Parsear todos os XMLs, agrupando por (cnpj, data)
    # Manter apenas o parse com maior PL para cada (cnpj, data)
    best_parses = {}  # (cnpj, data) -> (pl, acoes_list)

    for cnpj, paths in cnpj_xmls.items():
        for path in paths:
            fmt = _detect_xml_format(path)
            if fmt == "old":
                parsed = _parse_xml_old(path)
            elif fmt == "new":
                parsed = _parse_xml_new(path)
            else:
                continue

            if parsed is None or parsed["data"] is None:
                continue

            key = (cnpj, parsed["data"])
            pl = parsed["pl"]
            # Manter o parse com maior PL (mais completo)
            if key not in best_parses or pl > best_parses[key][0]:
                best_parses[key] = (pl, parsed["acoes"])

    # Converter para records
    records = []
    for (cnpj, data), (pl, acoes) in best_parses.items():
        for a in acoes:
            pct = (a["valor"] / pl * 100) if pl > 0 else 0
            records.append({
                "cnpj_fundo": cnpj,
                "data": data,
                "ativo": a["ativo"],
                "valor": a["valor"],
                "pl": pl,
                "pct_pl": pct,
                "setor": classificar_setor(a["ativo"]),
                "fonte": "XML",
            })

    if not records:
        return pd.DataFrame(columns=["cnpj_fundo", "data", "ativo", "valor", "pl", "pct_pl", "setor", "fonte"])

    df = pd.DataFrame(records)
    df["data"] = pd.to_datetime(df["data"])
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Download e parse CVM BLC_4
# ──────────────────────────────────────────────────────────────────────────────
def _download_cvm_blc4(yyyymm: str) -> pd.DataFrame | None:
    """Baixa e cacheia um mês de dados CVM BLC_4."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"cvm_blc4_{yyyymm}.parquet")

    # Verificar cache
    if os.path.exists(cache_path):
        age_hours = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))).total_seconds() / 3600
        # Meses antigos (>3 meses): cache permanente. Recentes: revalidar a cada 24h
        today = datetime.now()
        ref_date = datetime(int(yyyymm[:4]), int(yyyymm[4:6]), 1)
        months_old = (today.year - ref_date.year) * 12 + today.month - ref_date.month
        if months_old > 3 or age_hours < 24:
            try:
                return pd.read_parquet(cache_path)
            except Exception:
                pass

    url = CVM_ZIP_URL.format(yyyymm=yyyymm)
    try:
        resp = requests.get(url, timeout=120)
        if resp.status_code != 200:
            return None

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            # Buscar especificamente o BLC_4 dentro do ZIP
            blc4_name = f"cda_fi_BLC_4_{yyyymm}.csv"
            csv_names = [n for n in zf.namelist() if "BLC_4" in n and n.endswith(".csv")]
            if not csv_names:
                return None
            with zf.open(csv_names[0]) as csvfile:
                df = pd.read_csv(csvfile, sep=";", encoding="latin-1", low_memory=False)

        # Salvar cache
        df.to_parquet(cache_path, index=False)
        return df
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner="Baixando dados CVM (pode levar alguns minutos na primeira vez)...")
def carregar_dados_cvm(cnpjs_interesse: tuple, cnpjs_com_xml: tuple, meses: int = 36) -> pd.DataFrame:
    """Baixa dados CVM para fundos sem XML."""
    cnpjs_alvo = set(cnpjs_interesse) - set(cnpjs_com_xml)
    if not cnpjs_alvo:
        return pd.DataFrame(columns=["cnpj_fundo", "data", "ativo", "valor", "pl", "pct_pl", "setor", "fonte"])

    # Gerar lista de meses
    today = datetime.now()
    meses_list = []
    for i in range(1, meses + 1):
        d = today - timedelta(days=30 * i)
        ym = d.strftime("%Y%m")
        if ym not in meses_list:
            meses_list.append(ym)
    meses_list = sorted(set(meses_list))

    all_records = []
    progress = st.progress(0, text="Baixando dados CVM...")

    for idx, ym in enumerate(meses_list):
        progress.progress((idx + 1) / len(meses_list), text=f"CVM {ym[:4]}/{ym[4:]}...")
        df_cvm = _download_cvm_blc4(ym)
        if df_cvm is None or df_cvm.empty:
            continue

        # Tratar mudança de nome da coluna CNPJ
        cnpj_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in df_cvm.columns else "CNPJ_FUNDO"
        if cnpj_col not in df_cvm.columns:
            continue

        df_cvm["cnpj_norm"] = df_cvm[cnpj_col].apply(_normalizar_cnpj)

        # Filtrar para CNPJs alvo
        df_filtered = df_cvm[df_cvm["cnpj_norm"].isin(cnpjs_alvo)].copy()
        if df_filtered.empty:
            continue

        # Verificar colunas necessárias
        needed = ["DT_COMPTC", "CD_ATIVO", "VL_MERC_POS_FINAL"]
        if not all(c in df_filtered.columns for c in needed):
            continue

        # PL aproximado: soma de TODAS as posições do fundo (não só ações)
        pl_all = df_filtered.groupby("cnpj_norm")["VL_MERC_POS_FINAL"].sum()

        # Filtrar apenas posições em ações/BDRs/certificados (exclui debêntures, opções, futuros)
        mask = df_filtered["VL_MERC_POS_FINAL"] > 0
        if "TP_APLIC" in df_filtered.columns:
            tp_aplic_patterns = r"^A.{1,3}es(?:\s|$)|Brazilian Depository|Certificado"
            mask = mask & df_filtered["TP_APLIC"].str.contains(tp_aplic_patterns, case=False, na=False)
        df_stocks = df_filtered[mask].copy()
        df_stocks = df_stocks[df_stocks["CD_ATIVO"].notna()].copy()
        df_stocks["CD_ATIVO"] = df_stocks["CD_ATIVO"].str.strip().str.upper()
        df_stocks = df_stocks[df_stocks["CD_ATIVO"].str.len() >= 4].copy()

        if df_stocks.empty:
            continue

        # Construir records de forma vetorizada
        df_stocks["pl"] = df_stocks["cnpj_norm"].map(pl_all)
        df_stocks["pct_pl"] = (df_stocks["VL_MERC_POS_FINAL"] / df_stocks["pl"] * 100).fillna(0)
        df_stocks["setor"] = df_stocks["CD_ATIVO"].map(lambda t: classificar_setor(t))
        df_stocks["fonte"] = "CVM"

        month_records = df_stocks.rename(columns={
            "cnpj_norm": "cnpj_fundo",
            "DT_COMPTC": "data",
            "CD_ATIVO": "ativo",
            "VL_MERC_POS_FINAL": "valor",
        })[["cnpj_fundo", "data", "ativo", "valor", "pl", "pct_pl", "setor", "fonte"]].copy()
        month_records["data"] = pd.to_datetime(month_records["data"])
        all_records.append(month_records)

    progress.empty()

    if not all_records:
        return pd.DataFrame(columns=["cnpj_fundo", "data", "ativo", "valor", "pl", "pct_pl", "setor", "fonte"])

    return pd.concat(all_records, ignore_index=True)


# ──────────────────────────────────────────────────────────────────────────────
# Orquestrador principal
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Carregando dados...")
def carregar_todos_dados() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Retorna (df_fundos, df_posicoes) com dados unificados XML + CVM.
    Em modo cloud, lê diretamente dos parquets pré-exportados.
    """
    df_fundos = carregar_fundos_rv()

    # Modo cloud: ler posições consolidadas do parquet
    consolidado_path = os.path.join(DATA_DIR, "posicoes_consolidado.parquet")
    if CLOUD_MODE or not os.path.exists(XML_BASE_PATH):
        if os.path.exists(consolidado_path):
            df_posicoes = pd.read_parquet(consolidado_path)
            df_posicoes["data"] = pd.to_datetime(df_posicoes["data"])
            return df_fundos, df_posicoes
        return df_fundos, pd.DataFrame(columns=["cnpj_fundo", "data", "ativo", "valor", "pl", "pct_pl", "setor", "fonte"])

    # Modo local: processar XMLs + CVM
    # Montar set de CNPJs de interesse (direto + foco)
    cnpjs_direto = set(df_fundos["cnpj_norm"].dropna().tolist())
    cnpjs_foco = set(df_fundos["cnpj_foco_norm"].dropna().tolist()) - {""}
    todos_cnpjs = tuple(cnpjs_direto | cnpjs_foco)

    # 1. Dados XML (prioridade)
    df_xml = carregar_dados_xml(todos_cnpjs)
    cnpjs_com_xml = tuple(set(df_xml["cnpj_fundo"].unique())) if not df_xml.empty else ()

    # 2. Dados CVM (fallback para quem não tem XML)
    df_cvm = carregar_dados_cvm(todos_cnpjs, cnpjs_com_xml, meses=36)

    # 3. Unificar
    df_posicoes = pd.concat([df_xml, df_cvm], ignore_index=True)
    if not df_posicoes.empty:
        df_posicoes = df_posicoes.sort_values(["cnpj_fundo", "data", "ativo"])

    # Mapear CNPJ-foco de volta para o fundo original
    # Criar mapa: cnpj_foco_norm -> cnpj_norm do fundo
    foco_map = {}
    for _, row in df_fundos.iterrows():
        foco = row["cnpj_foco_norm"]
        direto = row["cnpj_norm"]
        if foco and foco != direto and foco != "":
            foco_map[foco] = direto

    # Substituir cnpj_foco pelo cnpj do fundo original nas posições
    # Marcar quais registros vêm de CNPJ-FOCO (master) para priorização
    if not df_posicoes.empty:
        foco_cnpjs_set = set(foco_map.keys())
        df_posicoes["_is_foco"] = df_posicoes["cnpj_fundo"].isin(foco_cnpjs_set)
        df_posicoes["cnpj_fundo"] = df_posicoes["cnpj_fundo"].map(
            lambda x: foco_map.get(x, x)
        )

        # Deduplicar: se um fundo tem dados de CNPJ-FOCO (master) E do CNPJ direto
        # para a mesma data, manter apenas os dados do CNPJ-FOCO (são a carteira real)
        # Também deduplicar por (cnpj_fundo, data, ativo) mantendo a última ocorrência
        df_posicoes = df_posicoes.sort_values(
            ["cnpj_fundo", "data", "_is_foco", "ativo"],
            ascending=[True, True, True, True]
        )
        # Agrupar por (cnpj, data) e manter apenas o grupo com _is_foco=True se existir
        keep_mask = []
        for (cnpj, dt), grp in df_posicoes.groupby(["cnpj_fundo", "data"]):
            if grp["_is_foco"].any() and not grp["_is_foco"].all():
                # Tem ambos: manter apenas os de FOCO (master)
                keep_mask.extend(grp[grp["_is_foco"]].index.tolist())
            else:
                # Só tem um tipo: manter todos
                keep_mask.extend(grp.index.tolist())

        df_posicoes = df_posicoes.loc[keep_mask]
        df_posicoes = df_posicoes.drop(columns=["_is_foco"])

        # Deduplicar por (cnpj_fundo, data, ativo) - manter último (maior PL)
        df_posicoes = df_posicoes.drop_duplicates(
            subset=["cnpj_fundo", "data", "ativo"], keep="last"
        )
        df_posicoes = df_posicoes.sort_values(["cnpj_fundo", "data", "ativo"])

    return df_fundos, df_posicoes
