"""
Carregamento de dados de carteira para fundos RV.
Fontes: XMLs locais (prioridade) e CVM API (fallback).

MODO CLOUD: Se data/posicoes_consolidado.parquet existir, lê diretamente
dos parquets pré-exportados (sem necessidade de Google Drive ou CVM API).
Use export_data.py para gerar os parquets localmente.
"""
from __future__ import annotations

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
XML_MELLON_PATH = r"G:\Drives compartilhados\SisIntegra\AMBIENTE_PRODUCAO\Posicao_XML\Mellon"
CACHE_DIR = os.path.join(_SCRIPT_DIR, "cache")
CVM_ZIP_URL = "https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/cda_fi_{yyyymm}.zip"
CVM_BLC4_ZIP_URL = "https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/cda_fi_BLC_4_{yyyymm}.zip"
CVM_INF_DIARIO_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{yyyymm}.zip"

BENCHMARK_CNPJS = {
    "IBOVESPA": "97543707000186",  # Blackrock Institucional Ibovespa FI Ações (passivo)
    "SMALL CAP": "07177193000108",  # Itaú Institucional Small Cap FIC Ações
}

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
# Fundos TAG adicionais (custódia Mellon — não estão na Base Geral)
# ──────────────────────────────────────────────────────────────────────────────
_MELLON_FUNDOS = [
    # ── FIAs (posições diretas em ações) ──
    {"nome": "SYNTA FIF AÇÕES RESP LTDA", "cnpj": "20.214.858/0001-66",
     "categoria": "Fundos TAG", "tier": 1, "master": None,
     "cnpj_foco": None, "enquadramento": None, "geri": "TAG INVESTIMENTOS"},
    {"nome": "SYNTA FIF EM ACOES II RESP LTDA", "cnpj": "51.564.188/0001-31",
     "categoria": "Fundos TAG", "tier": 1, "master": None,
     "cnpj_foco": None, "enquadramento": None, "geri": "VINCI"},
    {"nome": "MARIA SILVIA FIF AÇÕES IE RESP LTDA", "cnpj": "19.418.925/0001-85",
     "categoria": "Fundos TAG", "tier": 1, "master": None,
     "cnpj_foco": None, "enquadramento": None, "geri": "TAG INVESTIMENTOS"},
    {"nome": "SYNTA FIF MULTIM IE RESP LTDA", "cnpj": "41.054.683/0001-47",
     "categoria": "Fundos TAG", "tier": 1, "master": None,
     "cnpj_foco": None, "enquadramento": None, "geri": "TAG INVESTIMENTOS"},
    # ── Multimercado / RF (sem ações diretas) ──
    {"nome": "SYNTA FIC FIF MULTI RESP LTDA", "cnpj": "09.521.007/0001-23",
     "categoria": "Fundos TAG", "tier": 1, "master": None,
     "cnpj_foco": None, "enquadramento": None, "geri": "TAG INVESTIMENTOS"},
    {"nome": "SYNTA PASSIVO FIF RF RESP LTDA", "cnpj": "32.225.875/0001-88",
     "categoria": "Fundos TAG", "tier": 1, "master": None,
     "cnpj_foco": None, "enquadramento": None, "geri": "TAG INVESTIMENTOS"},
    {"nome": "SYNTA AZ QUEST FIF RF CP RESP LTDA", "cnpj": "19.091.575/0001-95",
     "categoria": "Fundos TAG", "tier": 1, "master": None,
     "cnpj_foco": None, "enquadramento": None, "geri": "AZ QUEST"},
    {"nome": "MARIA SILVIA FIF MULT CRED PRIV IE RESP LTDA", "cnpj": "53.026.176/0001-89",
     "categoria": "Fundos TAG", "tier": 1, "master": None,
     "cnpj_foco": None, "enquadramento": None, "geri": "TAG INVESTIMENTOS"},
]


def _append_mellon_fundos(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona fundos Mellon (TAG) ao DataFrame se não presentes."""
    for sf in _MELLON_FUNDOS:
        cnpj_n = _normalizar_cnpj(sf["cnpj"])
        if cnpj_n not in df["cnpj_norm"].values:
            row = {**sf, "cnpj_norm": cnpj_n, "cnpj_foco_norm": ""}
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    return df


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
            df = pd.read_parquet(parquet_path)
            return _append_mellon_fundos(df)
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
    return _append_mellon_fundos(df)


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
                acoes.append({"ativo": cod.strip().upper(), "valor": valor, "tipo": "acao"})

        # Cotas de fundos investidos (qtd * pu quando valorfindisp=0)
        for cota in fundo.findall("cotas"):
            cnpj_fundo_inv = cota.findtext("cnpjfundo", "")
            isin = cota.findtext("isin", "")
            valorfindisp = float(cota.findtext("valorfindisp", "0") or "0")
            qtd = float(cota.findtext("qtdisponivel", "0") or "0")
            pu = float(cota.findtext("puposicao", "0") or "0")
            valor = valorfindisp if valorfindisp > 0 else qtd * pu
            if valor > 0:
                nome = f"FUNDO {cnpj_fundo_inv}" if cnpj_fundo_inv else isin
                acoes.append({"ativo": nome, "valor": valor, "tipo": "cota",
                              "cnpj_investido": cnpj_fundo_inv, "isin": isin})

        # Títulos públicos
        for tp in fundo.findall("titpublico"):
            cod = tp.findtext("codativo", "")
            isin = tp.findtext("isin", "")
            venc = tp.findtext("dtvencimento", "")
            valor = float(tp.findtext("valorfindisp", "0") or "0")
            if valor > 0:
                nome = f"TITPUB {isin}" if isin else f"TITPUB {cod}"
                if venc:
                    nome += f" ({venc[:4]})"
                acoes.append({"ativo": nome, "valor": valor, "tipo": "titpublico"})

        # Caixa
        for cx in fundo.findall("caixa"):
            saldo = float(cx.findtext("saldo", "0") or "0")
            if saldo > 0:
                acoes.append({"ativo": "CAIXA", "valor": saldo, "tipo": "caixa"})

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


def _listar_xmls_mellon() -> list[str]:
    """Lista XMLs da pasta Mellon (estrutura YYYYMMDD/arquivos)."""
    xmls = []
    if not os.path.exists(XML_MELLON_PATH):
        return xmls
    try:
        pastas = [d for d in os.listdir(XML_MELLON_PATH) if d.isdigit() and len(d) == 8]
    except OSError:
        return xmls
    for pasta in sorted(pastas):
        pasta_path = os.path.join(XML_MELLON_PATH, pasta)
        if not os.path.isdir(pasta_path):
            continue
        try:
            for f in os.listdir(pasta_path):
                if f.lower().endswith(".xml") and not f.startswith("~"):
                    xmls.append(os.path.join(pasta_path, f))
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
    all_xmls = _listar_xmls() + _listar_xmls_mellon()

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

    # Tentar primeiro o ZIP combinado (formato novo), depois o individual (formato antigo)
    df = None
    for url in [
        CVM_ZIP_URL.format(yyyymm=yyyymm),
        CVM_BLC4_ZIP_URL.format(yyyymm=yyyymm),
    ]:
        try:
            resp = requests.get(url, timeout=120)
            if resp.status_code != 200:
                continue
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                csv_names = [n for n in zf.namelist() if "BLC_4" in n and n.endswith(".csv")]
                if not csv_names:
                    continue
                with zf.open(csv_names[0]) as csvfile:
                    df = pd.read_csv(csvfile, sep=";", encoding="latin-1", low_memory=False)
            break
        except Exception:
            continue

    if df is None:
        return None

    # Salvar cache
    df.to_parquet(cache_path, index=False)
    return df


def _download_cvm_pl(yyyymm: str) -> pd.DataFrame | None:
    """Baixa dados de PL (Patrimonio Liquido) do arquivo CDA PL da CVM."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"cvm_pl_{yyyymm}.parquet")

    # Verificar cache
    if os.path.exists(cache_path):
        age_hours = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))).total_seconds() / 3600
        today = datetime.now()
        ref_date = datetime(int(yyyymm[:4]), int(yyyymm[4:6]), 1)
        months_old = (today.year - ref_date.year) * 12 + today.month - ref_date.month
        if months_old > 3 or age_hours < 24:
            try:
                return pd.read_parquet(cache_path)
            except Exception:
                pass

    # PL está dentro do ZIP combinado
    url = CVM_ZIP_URL.format(yyyymm=yyyymm)
    try:
        resp = requests.get(url, timeout=120)
        if resp.status_code != 200:
            return None

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            pl_names = [n for n in zf.namelist() if "_PL_" in n and n.endswith(".csv")]
            if not pl_names:
                return None
            with zf.open(pl_names[0]) as csvfile:
                df = pd.read_csv(csvfile, sep=";", encoding="latin-1", low_memory=False)

        df.to_parquet(cache_path, index=False)
        return df
    except Exception:
        return None


def _download_cvm_blc(blc_num: int, yyyymm: str) -> pd.DataFrame | None:
    """Baixa e cacheia um mês de dados CVM BLC_{blc_num} (genérico)."""
    if blc_num == 4:
        return _download_cvm_blc4(yyyymm)

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"cvm_blc{blc_num}_{yyyymm}.parquet")

    if os.path.exists(cache_path):
        age_hours = (datetime.now() - datetime.fromtimestamp(
            os.path.getmtime(cache_path))).total_seconds() / 3600
        today = datetime.now()
        ref_date = datetime(int(yyyymm[:4]), int(yyyymm[4:6]), 1)
        months_old = (today.year - ref_date.year) * 12 + today.month - ref_date.month
        if months_old > 3 or age_hours < 24:
            try:
                return pd.read_parquet(cache_path)
            except Exception:
                pass

    blc_tag = f"BLC_{blc_num}"
    df = None
    # Tentar ZIP individual (menor) primeiro, depois combinado
    for url in [
        f"https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/cda_fi_BLC_{blc_num}_{yyyymm}.zip",
        CVM_ZIP_URL.format(yyyymm=yyyymm),
    ]:
        try:
            resp = requests.get(url, timeout=180)
            if resp.status_code != 200:
                continue
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                csv_names = [n for n in zf.namelist()
                             if blc_tag in n and n.endswith(".csv")]
                if not csv_names:
                    continue
                with zf.open(csv_names[0]) as csvfile:
                    df = pd.read_csv(csvfile, sep=";", encoding="latin-1",
                                     low_memory=False)
            break
        except Exception:
            continue

    if df is None:
        return None
    df.to_parquet(cache_path, index=False)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Busca sob demanda de carteiras CVM (para explosão de fundos investidos)
# ──────────────────────────────────────────────────────────────────────────────
_COLS_POSICOES = ["cnpj_fundo", "data", "ativo", "valor", "pl", "pct_pl", "setor", "fonte"]


def _processar_blc4_cnpjs(df_blc4: pd.DataFrame, cnpjs: set) -> pd.DataFrame:
    """Extrai TODAS as posições do BLC_4 (demais ativos) para CNPJs específicos.

    BLC_4 contém: ações, BDRs, ETFs, opções, warrants, recebíveis, etc.
    Captura TUDO para permitir explosão 100%.
    """
    cnpj_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in df_blc4.columns else "CNPJ_FUNDO"
    if cnpj_col not in df_blc4.columns or "VL_MERC_POS_FINAL" not in df_blc4.columns:
        return pd.DataFrame()

    df = df_blc4.copy()
    df["cnpj_fundo"] = df[cnpj_col].apply(_normalizar_cnpj)
    df = df[df["cnpj_fundo"].isin(cnpjs)].copy()
    if df.empty:
        return pd.DataFrame()

    df = df[df["VL_MERC_POS_FINAL"] > 0].copy()
    if df.empty:
        return pd.DataFrame()

    # Classificar cada posição pelo TP_APLIC
    tp_col = "TP_APLIC" if "TP_APLIC" in df.columns else None
    cd_col = "CD_ATIVO" if "CD_ATIVO" in df.columns else None
    ds_col = "DS_ATIVO" if "DS_ATIVO" in df.columns else None

    def _make_ativo_setor(row):
        tp = str(row[tp_col]).strip() if tp_col and pd.notna(row.get(tp_col)) else ""
        cd = str(row[cd_col]).strip().upper() if cd_col and pd.notna(row.get(cd_col)) else ""
        ds = str(row[ds_col]).strip() if ds_col and pd.notna(row.get(ds_col)) else ""

        is_stock = bool(re.search(
            r"A.{1,3}es|Brazilian Depository|Certificado|Units", tp, re.IGNORECASE))
        if is_stock and cd and len(cd) >= 4:
            return cd, classificar_setor(cd)
        if re.search(r"Op..es|Termo|Futuro|Swap", tp, re.IGNORECASE):
            return (f"DERIV {cd}" if cd else f"DERIV {ds[:20]}"), "Derivativos"
        if cd and len(cd) >= 4:
            return cd, classificar_setor(cd)
        return (f"OUTROS {ds[:25]}" if ds else f"OUTROS {tp[:20]}"), "Outros"

    result = df.apply(_make_ativo_setor, axis=1, result_type="expand")
    df["ativo"] = result[0]
    df["setor"] = result[1]
    return df[["cnpj_fundo", "DT_COMPTC", "ativo", "VL_MERC_POS_FINAL", "setor"]].rename(
        columns={"DT_COMPTC": "data", "VL_MERC_POS_FINAL": "valor"})


def _processar_blc_generico_cnpjs(df_blc: pd.DataFrame, cnpjs: set,
                                   setor_default: str, prefix: str) -> pd.DataFrame:
    """Processa BLC genérico (5=depósitos, 6=debêntures, 7=agro, 8=exterior)."""
    cnpj_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in df_blc.columns else "CNPJ_FUNDO"
    if cnpj_col not in df_blc.columns or "VL_MERC_POS_FINAL" not in df_blc.columns:
        return pd.DataFrame()

    df = df_blc.copy()
    df["cnpj_fundo"] = df[cnpj_col].apply(_normalizar_cnpj)
    df = df[df["cnpj_fundo"].isin(cnpjs)].copy()
    if df.empty:
        return pd.DataFrame()

    df = df[df["VL_MERC_POS_FINAL"] > 0].copy()
    if df.empty:
        return pd.DataFrame()

    cd_col = "CD_ATIVO" if "CD_ATIVO" in df.columns else None
    ds_col = "DS_ATIVO" if "DS_ATIVO" in df.columns else None

    def _make_ativo(row):
        cd = str(row[cd_col]).strip() if cd_col and pd.notna(row.get(cd_col)) else ""
        ds = str(row[ds_col]).strip()[:25] if ds_col and pd.notna(row.get(ds_col)) else ""
        return f"{prefix} {cd}" if cd else (f"{prefix} {ds}" if ds else prefix)

    df["ativo"] = df.apply(_make_ativo, axis=1)
    df["setor"] = setor_default
    return df[["cnpj_fundo", "DT_COMPTC", "ativo", "VL_MERC_POS_FINAL", "setor"]].rename(
        columns={"DT_COMPTC": "data", "VL_MERC_POS_FINAL": "valor"})


def _processar_blc2_cnpjs(df_blc2: pd.DataFrame, cnpjs: set) -> pd.DataFrame:
    """Extrai cotas de fundos investidos (BLC_2) para CNPJs específicos."""
    cnpj_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in df_blc2.columns else "CNPJ_FUNDO"
    if cnpj_col not in df_blc2.columns or "VL_MERC_POS_FINAL" not in df_blc2.columns:
        return pd.DataFrame()

    df = df_blc2.copy()
    df["cnpj_fundo"] = df[cnpj_col].apply(_normalizar_cnpj)
    df = df[df["cnpj_fundo"].isin(cnpjs)].copy()
    if df.empty:
        return pd.DataFrame()

    df = df[df["VL_MERC_POS_FINAL"] > 0].copy()
    if df.empty:
        return pd.DataFrame()

    # CNPJ do fundo investido
    cnpj_cota_col = None
    for col in ["CNPJ_FUNDO_COTA", "CNPJ_FUNDO_INVEST"]:
        if col in df.columns:
            cnpj_cota_col = col
            break

    nm_col = "NM_FUNDO_COTA" if "NM_FUNDO_COTA" in df.columns else None

    def _make_ativo(row):
        if cnpj_cota_col and pd.notna(row.get(cnpj_cota_col)):
            cnpj_inv = _normalizar_cnpj(str(row[cnpj_cota_col]))
            if cnpj_inv and len(cnpj_inv) == 14 and cnpj_inv != row["cnpj_fundo"]:
                return f"FUNDO {cnpj_inv}"
        if nm_col and pd.notna(row.get(nm_col)):
            return f"FUNDO {str(row[nm_col]).strip()[:40]}"
        return "FUNDO DESCONHECIDO"

    df["ativo"] = df.apply(_make_ativo, axis=1)
    df["setor"] = "Cotas de Fundos"
    return df[["cnpj_fundo", "DT_COMPTC", "ativo", "VL_MERC_POS_FINAL", "setor"]].rename(
        columns={"DT_COMPTC": "data", "VL_MERC_POS_FINAL": "valor"})


def _processar_blc1_cnpjs(df_blc1: pd.DataFrame, cnpjs: set) -> pd.DataFrame:
    """Extrai títulos públicos (BLC_1) para CNPJs específicos."""
    cnpj_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in df_blc1.columns else "CNPJ_FUNDO"
    if cnpj_col not in df_blc1.columns or "VL_MERC_POS_FINAL" not in df_blc1.columns:
        return pd.DataFrame()

    df = df_blc1.copy()
    df["cnpj_fundo"] = df[cnpj_col].apply(_normalizar_cnpj)
    df = df[df["cnpj_fundo"].isin(cnpjs)].copy()
    if df.empty:
        return pd.DataFrame()

    df = df[df["VL_MERC_POS_FINAL"] > 0].copy()
    if df.empty:
        return pd.DataFrame()

    cod_col = "CD_ATIVO" if "CD_ATIVO" in df.columns else ("CD_SELIC" if "CD_SELIC" in df.columns else None)
    ds_col = "DS_ATIVO" if "DS_ATIVO" in df.columns else None

    def _make_ativo(row):
        cod = str(row[cod_col]).strip() if cod_col and pd.notna(row.get(cod_col)) else ""
        ds = str(row[ds_col]).strip()[:25] if ds_col and pd.notna(row.get(ds_col)) else ""
        return f"TITPUB {cod}" if cod else (f"TITPUB {ds}" if ds else "TITPUB")

    df["ativo"] = df.apply(_make_ativo, axis=1)
    df["setor"] = "Renda Fixa"
    return df[["cnpj_fundo", "DT_COMPTC", "ativo", "VL_MERC_POS_FINAL", "setor"]].rename(
        columns={"DT_COMPTC": "data", "VL_MERC_POS_FINAL": "valor"})


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_carteiras_cvm_sob_demanda(cnpjs_alvo: tuple, meses_max: int = 6) -> pd.DataFrame:
    """Busca carteira completa de fundos via CVM (BLC_4 + BLC_2 + BLC_1).

    Para fundos investidos que não estão no universo de acompanhamento.
    Retorna DataFrame no formato df_posicoes.

    BLC_4 = ações/BDRs/ETFs/demais ativos
    BLC_2 = cotas de fundos investidos
    BLC_1 = títulos públicos
    BLC_5 = depósitos a prazo
    BLC_6 = debêntures
    O restante é calculado como 'Outros RF/Caixa'.
    """
    cnpjs_set = {_normalizar_cnpj(c) for c in cnpjs_alvo if c}
    cnpjs_set.discard("")
    if not cnpjs_set:
        return pd.DataFrame(columns=_COLS_POSICOES)

    today = datetime.now()
    all_dfs = []
    cnpjs_encontrados = set()

    for i in range(0, meses_max):
        d = today - timedelta(days=30 * i)
        ym = d.strftime("%Y%m")
        cnpjs_pendentes = cnpjs_set - cnpjs_encontrados
        if not cnpjs_pendentes:
            break

        month_dfs = []
        month_found = set()

        # BLC_4: Ações, BDRs, ETFs
        df_blc4 = _download_cvm_blc4(ym)
        if df_blc4 is not None and not df_blc4.empty:
            recs4 = _processar_blc4_cnpjs(df_blc4, cnpjs_pendentes)
            if not recs4.empty:
                month_dfs.append(recs4)
                month_found.update(recs4["cnpj_fundo"].unique())

        # BLC_2: Cotas de fundos
        df_blc2 = _download_cvm_blc(2, ym)
        if df_blc2 is not None and not df_blc2.empty:
            recs2 = _processar_blc2_cnpjs(df_blc2, cnpjs_pendentes)
            if not recs2.empty:
                month_dfs.append(recs2)
                month_found.update(recs2["cnpj_fundo"].unique())

        # BLC_1: Títulos públicos
        df_blc1 = _download_cvm_blc(1, ym)
        if df_blc1 is not None and not df_blc1.empty:
            recs1 = _processar_blc1_cnpjs(df_blc1, cnpjs_pendentes)
            if not recs1.empty:
                month_dfs.append(recs1)
                month_found.update(recs1["cnpj_fundo"].unique())

        # BLC_5: Depósitos a prazo / BLC_6: Debêntures
        for blc_n, setor_d, pref in [(5, "Renda Fixa", "DEP"), (6, "Renda Fixa", "DEB")]:
            df_blc_n = _download_cvm_blc(blc_n, ym)
            if df_blc_n is not None and not df_blc_n.empty:
                recs_n = _processar_blc_generico_cnpjs(df_blc_n, cnpjs_pendentes, setor_d, pref)
                if not recs_n.empty:
                    month_dfs.append(recs_n)
                    month_found.update(recs_n["cnpj_fundo"].unique())

        if month_dfs:
            df_month = pd.concat(month_dfs, ignore_index=True)

            # PL real do arquivo CDA PL
            df_pl_cvm = _download_cvm_pl(ym)
            pl_map = {}
            if df_pl_cvm is not None and not df_pl_cvm.empty:
                pl_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in df_pl_cvm.columns else "CNPJ_FUNDO"
                if pl_col in df_pl_cvm.columns and "VL_PATRIM_LIQ" in df_pl_cvm.columns:
                    df_pl_cvm["_cnpj"] = df_pl_cvm[pl_col].apply(_normalizar_cnpj)
                    for cnpj in month_found:
                        pl_rows = df_pl_cvm[df_pl_cvm["_cnpj"] == cnpj]
                        if not pl_rows.empty:
                            pl_map[cnpj] = float(pl_rows["VL_PATRIM_LIQ"].iloc[-1])

            # Fallback PL: soma de posições
            pl_approx = df_month.groupby("cnpj_fundo")["valor"].sum().to_dict()

            df_month["pl"] = df_month["cnpj_fundo"].map(
                lambda c: pl_map.get(c, pl_approx.get(c, 0)))

            # Adicionar entrada "Outros RF/Caixa" para o valor não explicado
            for cnpj in month_found:
                pl_total = pl_map.get(cnpj, 0)
                if pl_total > 0:
                    soma_explicada = df_month[df_month["cnpj_fundo"] == cnpj]["valor"].sum()
                    residual = pl_total - soma_explicada
                    if residual > pl_total * 0.01:  # >1% do PL
                        dt_ref = df_month[df_month["cnpj_fundo"] == cnpj]["data"].iloc[0]
                        month_dfs.append(pd.DataFrame([{
                            "cnpj_fundo": cnpj, "data": dt_ref,
                            "ativo": "OUTROS RF/CAIXA", "valor": residual,
                            "setor": "Caixa",
                        }]))

            # Reconcat with residuals
            df_month = pd.concat(month_dfs, ignore_index=True)
            df_month["pl"] = df_month["cnpj_fundo"].map(
                lambda c: pl_map.get(c, pl_approx.get(c, 0)))

            all_dfs.append(df_month)
        cnpjs_encontrados.update(month_found)

    if not all_dfs:
        return pd.DataFrame(columns=_COLS_POSICOES)

    df = pd.concat(all_dfs, ignore_index=True)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["pct_pl"] = np.where(df["pl"] > 0, df["valor"] / df["pl"] * 100, 0)
    df["fonte"] = "CVM_SOB_DEMANDA"

    return df[_COLS_POSICOES].copy()


# ──────────────────────────────────────────────────────────────────────────────
# Download e parse CVM inf_diario (cotas diárias)
# ──────────────────────────────────────────────────────────────────────────────
def _download_cvm_inf_diario(yyyymm: str, cnpjs_filtro: set | None = None) -> pd.DataFrame | None:
    """Baixa e cacheia um mês de dados de cotas diárias (inf_diario).

    Se cnpjs_filtro fornecido, salva apenas esses CNPJs no cache (muito menor).
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    suffix = "_filtered" if cnpjs_filtro else ""
    cache_path = os.path.join(CACHE_DIR, f"cvm_inf_diario_{yyyymm}{suffix}.parquet")

    if os.path.exists(cache_path):
        age_hours = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))).total_seconds() / 3600
        today = datetime.now()
        ref_date = datetime(int(yyyymm[:4]), int(yyyymm[4:6]), 1)
        months_old = (today.year - ref_date.year) * 12 + today.month - ref_date.month
        if months_old > 3 or age_hours < 24:
            try:
                return pd.read_parquet(cache_path)
            except Exception:
                pass

    url = CVM_INF_DIARIO_URL.format(yyyymm=yyyymm)
    try:
        resp = requests.get(url, timeout=120)
        if resp.status_code != 200:
            return None
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
            if not csv_names:
                return None
            with zf.open(csv_names[0]) as csvfile:
                df = pd.read_csv(csvfile, sep=";", encoding="latin-1", low_memory=False)
    except Exception:
        return None

    # Normalizar coluna CNPJ
    cnpj_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in df.columns else "CNPJ_FUNDO"
    if cnpj_col not in df.columns:
        return None
    df["cnpj_norm"] = df[cnpj_col].apply(_normalizar_cnpj)

    # Filtrar se solicitado
    if cnpjs_filtro:
        df = df[df["cnpj_norm"].isin(cnpjs_filtro)].copy()

    # Manter apenas colunas úteis
    cols_keep = ["cnpj_norm", "DT_COMPTC", "VL_QUOTA", "VL_PATRIM_LIQ"]
    cols_available = [c for c in cols_keep if c in df.columns]
    df = df[cols_available].copy()

    df.to_parquet(cache_path, index=False)
    return df


@st.cache_data(ttl=3600, show_spinner="Baixando cotas dos fundos (CVM inf_diario)...")
def carregar_cotas_fundos(cnpjs: tuple, meses: int = 36) -> pd.DataFrame:
    """Carrega cotas diárias dos fundos de interesse + benchmarks.

    Retorna DataFrame: cnpj_fundo | data | vl_quota | vl_patrim_liq | retorno_diario
    """
    # Cloud mode
    cotas_path = os.path.join(DATA_DIR, "cotas_consolidado.parquet")
    if CLOUD_MODE:
        if os.path.exists(cotas_path):
            df = pd.read_parquet(cotas_path)
            df["data"] = pd.to_datetime(df["data"])
            # Filtrar CNPJs de interesse + benchmarks
            cnpjs_set = set(cnpjs) | set(BENCHMARK_CNPJS.values())
            return df[df["cnpj_fundo"].isin(cnpjs_set)].copy()
        return pd.DataFrame(columns=["cnpj_fundo", "data", "vl_quota", "vl_patrim_liq", "retorno_diario"])

    # Modo local: baixar da CVM
    cnpjs_set = set(cnpjs) | set(BENCHMARK_CNPJS.values())

    today = datetime.now()
    meses_list = []
    for i in range(meses + 1):
        d = today - timedelta(days=30 * i)
        ym = d.strftime("%Y%m")
        if ym not in meses_list:
            meses_list.append(ym)
    meses_list = sorted(set(meses_list))

    all_dfs = []
    progress = st.progress(0, text="Baixando cotas CVM...")

    for idx, ym in enumerate(meses_list):
        progress.progress((idx + 1) / len(meses_list), text=f"Cotas {ym[:4]}/{ym[4:]}...")
        df = _download_cvm_inf_diario(ym, cnpjs_filtro=cnpjs_set)
        if df is not None and not df.empty:
            all_dfs.append(df)

    progress.empty()

    if not all_dfs:
        return pd.DataFrame(columns=["cnpj_fundo", "data", "vl_quota", "vl_patrim_liq", "retorno_diario"])

    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all = df_all.rename(columns={
        "cnpj_norm": "cnpj_fundo",
        "DT_COMPTC": "data",
        "VL_QUOTA": "vl_quota",
        "VL_PATRIM_LIQ": "vl_patrim_liq",
    })
    df_all["data"] = pd.to_datetime(df_all["data"])
    df_all = df_all.sort_values(["cnpj_fundo", "data"]).drop_duplicates(
        subset=["cnpj_fundo", "data"], keep="last"
    )

    # Calcular retorno diário vetorizado
    df_all["retorno_diario"] = df_all.groupby("cnpj_fundo")["vl_quota"].transform(
        lambda s: s.pct_change()
    )

    return df_all.reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner="Calculando estatisticas do universo de fundos...")
def carregar_universo_stats(meses: int = 36) -> pd.DataFrame:
    """Carrega estatísticas agregadas do universo de fundos RV.

    Em vez de carregar TODOS os fundos em memória, baixa mês a mês e
    calcula apenas as estatísticas agregadas (média, std, percentis).

    Retorna DataFrame: data | media_ret | std_ret | p10 | p25 | p50 | p75 | p90 | n_fundos
    """
    # Cloud mode
    stats_path = os.path.join(DATA_DIR, "universo_stats.parquet")
    if CLOUD_MODE:
        if os.path.exists(stats_path):
            df = pd.read_parquet(stats_path)
            df["data"] = pd.to_datetime(df["data"])
            return df
        return pd.DataFrame()

    today = datetime.now()
    meses_list = []
    for i in range(meses + 1):
        d = today - timedelta(days=30 * i)
        ym = d.strftime("%Y%m")
        if ym not in meses_list:
            meses_list.append(ym)
    meses_list = sorted(set(meses_list))

    all_dfs = []
    progress = st.progress(0, text="Baixando universo CVM...")

    for idx, ym in enumerate(meses_list):
        progress.progress((idx + 1) / len(meses_list), text=f"Universo {ym[:4]}/{ym[4:]}...")
        df = _download_cvm_inf_diario(ym, cnpjs_filtro=None)
        if df is None or df.empty:
            continue
        # Calcular retorno diário para todos os fundos deste mês
        df = df.rename(columns={"DT_COMPTC": "data", "VL_QUOTA": "vl_quota", "cnpj_norm": "cnpj"})
        df["data"] = pd.to_datetime(df["data"])
        df = df.sort_values(["cnpj", "data"])
        df["ret"] = df.groupby("cnpj")["vl_quota"].transform(lambda s: s.pct_change())
        # Agregar: por data, calcular stats
        daily_stats = df.groupby("data")["ret"].agg(
            media_ret="mean",
            std_ret="std",
            p10=lambda x: np.nanpercentile(x, 10),
            p25=lambda x: np.nanpercentile(x, 25),
            p50=lambda x: np.nanpercentile(x, 50),
            p75=lambda x: np.nanpercentile(x, 75),
            p90=lambda x: np.nanpercentile(x, 90),
            n_fundos="count",
        ).reset_index()
        all_dfs.append(daily_stats)

    progress.empty()

    if not all_dfs:
        return pd.DataFrame()

    df_stats = pd.concat(all_dfs, ignore_index=True)
    df_stats = df_stats.sort_values("data").drop_duplicates(subset=["data"], keep="last")
    return df_stats.reset_index(drop=True)


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

        # PL real: tentar obter do arquivo CDA PL (VL_PATRIM_LIQ)
        df_pl = _download_cvm_pl(ym)
        pl_real = {}
        if df_pl is not None and not df_pl.empty:
            pl_cnpj_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in df_pl.columns else "CNPJ_FUNDO"
            if pl_cnpj_col in df_pl.columns and "VL_PATRIM_LIQ" in df_pl.columns:
                df_pl["cnpj_norm"] = df_pl[pl_cnpj_col].apply(_normalizar_cnpj)
                df_pl_filtered = df_pl[df_pl["cnpj_norm"].isin(cnpjs_alvo)]
                pl_real = dict(zip(df_pl_filtered["cnpj_norm"], df_pl_filtered["VL_PATRIM_LIQ"]))

        # Fallback: PL aproximado pela soma de TODAS as posições no BLC_4
        pl_approx = df_filtered.groupby("cnpj_norm")["VL_MERC_POS_FINAL"].sum()

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

        # Usar PL real (do arquivo PL) quando disponível, senão fallback
        df_stocks["pl"] = df_stocks["cnpj_norm"].map(
            lambda x: pl_real.get(x, pl_approx.get(x, 0))
        )
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
@st.cache_data(ttl=3600)
def carregar_fundamentals_explosao() -> pd.DataFrame:
    """Carrega dados fundamentalistas para explosão (parquet cloud ou SQLite local).

    Retorna DataFrame com colunas: ticker, indicador, valor
    Tickers no formato 'VALE3.SA' (Yahoo Finance).
    """
    parquet_path = os.path.join(DATA_DIR, "fundamentals_explosao.parquet")

    # Cloud mode ou parquet pré-exportado existe
    if os.path.exists(parquet_path):
        return pd.read_parquet(parquet_path)

    # Local: ler direto do SQLite yahoo_finance.db
    db_path = os.path.join(os.path.dirname(_SCRIPT_DIR), "yahoo_finance", "yahoo_finance.db")
    if os.path.exists(db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(
            "SELECT ticker, indicador, valor FROM fundamentalistas WHERE ticker LIKE '%.SA'",
            conn,
        )
        conn.close()
        return df

    return pd.DataFrame(columns=["ticker", "indicador", "valor"])


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
    # Só excluir da CVM os fundos cujo XML é recente (últimos 6 meses)
    if not df_xml.empty:
        _xml_d = pd.to_datetime(df_xml["data"])
        _xml_max = _xml_d.groupby(df_xml["cnpj_fundo"]).max()
        _cutoff = pd.Timestamp.now() - pd.DateOffset(months=6)
        cnpjs_com_xml_recente = tuple(_xml_max[_xml_max >= _cutoff].index)
    else:
        cnpjs_com_xml_recente = ()

    # 2. Dados CVM (fallback para quem não tem XML recente)
    df_cvm = carregar_dados_cvm(todos_cnpjs, cnpjs_com_xml_recente, meses=36)

    # 3. Unificar
    df_posicoes = pd.concat([df_xml, df_cvm], ignore_index=True)
    if not df_posicoes.empty:
        df_posicoes = df_posicoes.sort_values(["cnpj_fundo", "data", "ativo"])

    # Mapear CNPJ-foco de volta para o fundo original
    # Criar mapa: cnpj_foco -> lista de cnpj_direto (pode haver vários feeders)
    from collections import defaultdict
    foco_to_diretos = defaultdict(list)
    for _, row in df_fundos.iterrows():
        foco = row["cnpj_foco_norm"]
        direto = row["cnpj_norm"]
        if foco and foco != direto and foco != "":
            foco_to_diretos[foco].append(direto)

    # Duplicar dados do foco para CADA feeder que aponta para ele
    if not df_posicoes.empty and foco_to_diretos:
        foco_cnpjs_set = set(foco_to_diretos.keys())
        df_foco = df_posicoes[df_posicoes["cnpj_fundo"].isin(foco_cnpjs_set)].copy()
        df_direto = df_posicoes[~df_posicoes["cnpj_fundo"].isin(foco_cnpjs_set)].copy()

        foco_dups = []
        for foco_cnpj, diretos in foco_to_diretos.items():
            df_this = df_foco[df_foco["cnpj_fundo"] == foco_cnpj]
            if df_this.empty:
                continue
            for direto_cnpj in diretos:
                df_dup = df_this.copy()
                df_dup["cnpj_fundo"] = direto_cnpj
                df_dup["_is_foco"] = True
                foco_dups.append(df_dup)

        df_direto["_is_foco"] = False
        if foco_dups:
            df_posicoes = pd.concat([df_direto, pd.concat(foco_dups, ignore_index=True)], ignore_index=True)
        else:
            df_posicoes = df_direto

        # Quando há dados foco E direto para mesmo (cnpj, data), preferir foco
        df_posicoes = df_posicoes.sort_values(
            ["cnpj_fundo", "data", "_is_foco", "ativo"],
            ascending=[True, True, True, True]
        )
        keep_mask = []
        for (cnpj, dt), grp in df_posicoes.groupby(["cnpj_fundo", "data"]):
            if grp["_is_foco"].any() and not grp["_is_foco"].all():
                keep_mask.extend(grp[grp["_is_foco"]].index.tolist())
            else:
                keep_mask.extend(grp.index.tolist())

        df_posicoes = df_posicoes.loc[keep_mask]
        df_posicoes = df_posicoes.drop(columns=["_is_foco"])

        # Deduplicar por (cnpj_fundo, data, ativo) - manter último
        df_posicoes = df_posicoes.drop_duplicates(
            subset=["cnpj_fundo", "data", "ativo"], keep="last"
        )
        df_posicoes = df_posicoes.sort_values(["cnpj_fundo", "data", "ativo"])

    return df_fundos, df_posicoes
