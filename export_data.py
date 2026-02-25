"""
Script de exportação INCREMENTAL de dados para deploy cloud.

Na primeira vez, baixa tudo (36 meses CVM + todos XMLs).
Nas próximas execuções:
  - XMLs: só processa novos arquivos (compara com data mais recente no parquet)
  - CVM: só baixa meses que ainda não estão no parquet
  - Reconstrói consolidado com dedup

Modos de execução:
    python export_data.py          # incremental (padrão)
    python export_data.py --full   # força reprocessamento completo
    python export_data.py --ci     # modo CI/GitHub Actions (sem XMLs/Excel)

Os parquets ficam em data/ e devem ser commitados no repo.
"""

import os
import sys
import argparse
from datetime import datetime

# Garantir diretório correto
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

# Monkey-patch streamlit
import streamlit as st


def _mock_cache_data(*args, **kwargs):
    def decorator(func):
        return func
    if args and callable(args[0]):
        return args[0]
    return decorator


def _mock_progress(*args, **kwargs):
    class FakeProgress:
        def progress(self, *a, **kw):
            pass
        def empty(self):
            pass
    return FakeProgress()


st.cache_data = _mock_cache_data
st.progress = _mock_progress

import pandas as pd
import time

# Force CLOUD_MODE = False para carregar de fontes locais
os.environ["FORCE_LOCAL_MODE"] = "1"

from data_loader import (
    carregar_fundos_rv,
    carregar_dados_xml,
    carregar_dados_cvm,
    carregar_cotas_fundos,
    carregar_universo_stats,
    buscar_carteiras_cvm_sob_demanda,
    _download_cvm_blc4,
    _download_cvm_pl,
    _normalizar_cnpj,
    BENCHMARK_CNPJS,
)
from sector_map import classificar_setor

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _dedup_consolidado(df_posicoes, df_fundos):
    """Aplica dedup de CNPJ-FOCO e ativos duplicados.

    Quando múltiplos feeders apontam para o mesmo foco,
    duplica os dados do foco para cada feeder direto.
    """
    from collections import defaultdict

    # foco → lista de diretos (pode haver vários feeders para mesmo foco)
    foco_to_diretos = defaultdict(list)
    for _, row in df_fundos.iterrows():
        foco = row["cnpj_foco_norm"]
        direto = row["cnpj_norm"]
        if foco and foco != direto and foco != "":
            foco_to_diretos[foco].append(direto)

    if df_posicoes.empty:
        return df_posicoes

    foco_cnpjs_set = set(foco_to_diretos.keys())

    # Separar dados de foco e não-foco
    df_foco = df_posicoes[df_posicoes["cnpj_fundo"].isin(foco_cnpjs_set)].copy()
    df_direto = df_posicoes[~df_posicoes["cnpj_fundo"].isin(foco_cnpjs_set)].copy()

    # Para cada cnpj_foco, duplicar dados para TODOS os feeders diretos
    foco_dups = []
    for foco_cnpj, diretos in foco_to_diretos.items():
        df_this_foco = df_foco[df_foco["cnpj_fundo"] == foco_cnpj]
        if df_this_foco.empty:
            continue
        for direto_cnpj in diretos:
            df_dup = df_this_foco.copy()
            df_dup["cnpj_fundo"] = direto_cnpj
            df_dup["_is_foco"] = True
            foco_dups.append(df_dup)

    df_direto["_is_foco"] = False

    if foco_dups:
        df_all_foco = pd.concat(foco_dups, ignore_index=True)
        df_posicoes = pd.concat([df_direto, df_all_foco], ignore_index=True)
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

    df_posicoes = df_posicoes.drop_duplicates(
        subset=["cnpj_fundo", "data", "ativo"], keep="last"
    )
    return df_posicoes.sort_values(["cnpj_fundo", "data", "ativo"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Força reprocessamento completo")
    parser.add_argument("--ci", action="store_true", help="Modo CI/GitHub Actions (sem XMLs/Excel)")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    if args.ci:
        mode = "CI/GITHUB ACTIONS"
    elif args.full:
        mode = "COMPLETO"
    else:
        mode = "INCREMENTAL"
    print(f"EXPORTACAO DE DADOS ({mode})")
    print("=" * 60)

    # ── 1. Fundos RV ──
    fundos_path = os.path.join(DATA_DIR, "fundos_rv.parquet")
    if args.ci:
        # CI: usa parquet existente (Base Geral.xlsm não disponível)
        print("\n[1/8] Carregando fundos RV do parquet existente...")
        if not os.path.exists(fundos_path):
            print("  ERRO: fundos_rv.parquet não encontrado! Execute localmente primeiro.")
            sys.exit(1)
        df_fundos = pd.read_parquet(fundos_path)
        print(f"  -> {len(df_fundos)} fundos (cache)")
    else:
        print("\n[1/8] Carregando fundos RV...")
        t0 = time.time()
        df_fundos = carregar_fundos_rv()
        print(f"  -> {len(df_fundos)} fundos em {time.time()-t0:.1f}s")
        df_fundos.to_parquet(fundos_path, index=False)

    cnpjs_direto = set(df_fundos["cnpj_norm"].dropna().tolist())
    cnpjs_foco = set(df_fundos["cnpj_foco_norm"].dropna().tolist()) - {""}
    todos_cnpjs = tuple(cnpjs_direto | cnpjs_foco)

    # ── 2. XMLs ──
    xml_path = os.path.join(DATA_DIR, "posicoes_xml.parquet")
    if args.ci:
        # CI: usa parquet existente (XMLs no Google Drive não disponíveis)
        print("\n[2/8] XMLs: usando parquet existente (modo CI)...")
        if os.path.exists(xml_path):
            df_xml = pd.read_parquet(xml_path)
            df_xml["data"] = pd.to_datetime(df_xml["data"])
            print(f"  -> {len(df_xml)} registros XML (cache)")
        else:
            df_xml = pd.DataFrame()
            print("  -> Sem dados XML (parquet não encontrado)")
    elif not args.full and os.path.exists(xml_path):
        print("\n[2/8] XMLs: verificando incrementalmente...")
        df_xml_old = pd.read_parquet(xml_path)
        df_xml_old["data"] = pd.to_datetime(df_xml_old["data"])
        old_max_date = df_xml_old["data"].max()
        print(f"  Dados existentes ate: {old_max_date}")

        t0 = time.time()
        df_xml_new = carregar_dados_xml(todos_cnpjs)
        new_max_date = df_xml_new["data"].max() if not df_xml_new.empty else old_max_date

        if new_max_date > old_max_date or len(df_xml_new) != len(df_xml_old):
            df_xml = df_xml_new
            print(f"  -> Novos dados! {len(df_xml)} registros (era {len(df_xml_old)})")
            df_xml.to_parquet(xml_path, index=False)
        else:
            df_xml = df_xml_old
            print(f"  -> Sem mudancas ({len(df_xml)} registros)")
        print(f"  -> {time.time()-t0:.1f}s")
    else:
        print("\n[2/8] Processando todos os XMLs...")
        t0 = time.time()
        df_xml = carregar_dados_xml(todos_cnpjs)
        print(f"  -> {len(df_xml)} registros XML em {time.time()-t0:.1f}s")
        df_xml.to_parquet(xml_path, index=False)

    # ── 3. CVM (incremental: só meses novos) ──
    cvm_path = os.path.join(DATA_DIR, "posicoes_cvm.parquet")
    # Só excluir da CVM os fundos cujo XML é recente (últimos 6 meses).
    # Fundos com XML antigo/parado devem ter fallback para CVM.
    if not df_xml.empty:
        _xml_dates = pd.to_datetime(df_xml["data"])
        _xml_latest = _xml_dates.groupby(df_xml["cnpj_fundo"]).max()
        _cutoff = pd.Timestamp.now() - pd.DateOffset(months=6)
        cnpjs_com_xml_recente = tuple(_xml_latest[_xml_latest >= _cutoff].index)
        _n_stale = len(set(df_xml["cnpj_fundo"].unique())) - len(cnpjs_com_xml_recente)
        if _n_stale > 0:
            print(f"  AVISO: {_n_stale} fundos com XML antigo (>6 meses) -- incluindo na busca CVM")
    else:
        cnpjs_com_xml_recente = ()

    if not args.full and os.path.exists(cvm_path):
        print("\n[3/8] CVM: verificando meses novos...")
        df_cvm_old = pd.read_parquet(cvm_path)
        df_cvm_old["data"] = pd.to_datetime(df_cvm_old["data"])
        meses_existentes = set(df_cvm_old["data"].dt.strftime("%Y%m").unique())
        print(f"  Meses existentes: {len(meses_existentes)} ({min(meses_existentes)} a {max(meses_existentes)})")

        # Gerar todos os meses desejados (36 meses)
        from datetime import timedelta
        today = datetime.now()
        meses_desejados = set()
        for i in range(1, 37):
            d = today - timedelta(days=30 * i)
            meses_desejados.add(d.strftime("%Y%m"))

        meses_novos = sorted(meses_desejados - meses_existentes)

        # Também re-baixar os 2 meses mais recentes (podem ter sido atualizados)
        meses_recentes = sorted(meses_existentes)[-2:]
        meses_a_baixar = sorted(set(meses_novos) | set(meses_recentes))

        if meses_a_baixar:
            print(f"  Baixando {len(meses_a_baixar)} meses: {meses_a_baixar[:5]}{'...' if len(meses_a_baixar)>5 else ''}")
            cnpjs_alvo = set(todos_cnpjs) - set(cnpjs_com_xml_recente)
            new_records = []

            for ym in meses_a_baixar:
                df_cvm_month = _download_cvm_blc4(ym)
                if df_cvm_month is None or df_cvm_month.empty:
                    continue

                cnpj_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in df_cvm_month.columns else "CNPJ_FUNDO"
                df_cvm_month["cnpj_norm"] = df_cvm_month[cnpj_col].apply(_normalizar_cnpj)
                df_filtered = df_cvm_month[df_cvm_month["cnpj_norm"].isin(cnpjs_alvo)].copy()
                if df_filtered.empty:
                    continue

                needed = ["DT_COMPTC", "CD_ATIVO", "VL_MERC_POS_FINAL"]
                if not all(c in df_filtered.columns for c in needed):
                    continue

                # PL real do arquivo CDA PL
                df_pl = _download_cvm_pl(ym)
                pl_real = {}
                if df_pl is not None and not df_pl.empty:
                    pl_cnpj_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in df_pl.columns else "CNPJ_FUNDO"
                    if pl_cnpj_col in df_pl.columns and "VL_PATRIM_LIQ" in df_pl.columns:
                        df_pl["cnpj_norm"] = df_pl[pl_cnpj_col].apply(_normalizar_cnpj)
                        df_pl_f = df_pl[df_pl["cnpj_norm"].isin(cnpjs_alvo)]
                        pl_real = dict(zip(df_pl_f["cnpj_norm"], df_pl_f["VL_PATRIM_LIQ"]))

                # Fallback: PL aproximado
                pl_approx = df_filtered.groupby("cnpj_norm")["VL_MERC_POS_FINAL"].sum()

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
                new_records.append(month_records)

            if new_records:
                df_new = pd.concat(new_records, ignore_index=True)
                # Remover meses que foram re-baixados do dataframe antigo
                meses_re = set(meses_a_baixar)
                df_cvm_keep = df_cvm_old[~df_cvm_old["data"].dt.strftime("%Y%m").isin(meses_re)]
                df_cvm = pd.concat([df_cvm_keep, df_new], ignore_index=True)
                print(f"  -> Adicionados {len(df_new)} registros novos")
            else:
                df_cvm = df_cvm_old
                print(f"  -> Nenhum dado novo de CVM")
        else:
            df_cvm = df_cvm_old
            print(f"  -> Todos os meses ja existem")

        df_cvm.to_parquet(cvm_path, index=False)
        print(f"  -> Total CVM: {len(df_cvm)} registros")
    else:
        print("\n[3/8] Baixando todos os dados CVM (36 meses)...")
        t0 = time.time()
        df_cvm = carregar_dados_cvm(todos_cnpjs, cnpjs_com_xml_recente, meses=36)
        print(f"  -> {len(df_cvm)} registros CVM em {time.time()-t0:.1f}s")
        df_cvm.to_parquet(cvm_path, index=False)

    # ── 4. Consolidar com dedup ──
    print("\n[4/8] Consolidando com deduplicacao...")
    df_posicoes = pd.concat([df_xml, df_cvm], ignore_index=True)
    df_posicoes = _dedup_consolidado(df_posicoes, df_fundos)

    print(f"  -> {len(df_posicoes)} registros consolidados")
    print(f"  -> CNPJs com dados: {df_posicoes['cnpj_fundo'].nunique()}")

    # ── 4b. CVM sob demanda para fundos investidos (Mellon cotas) ──
    # Identificar CNPJs de fundos investidos (cotas) que não estão no universo
    cnpjs_no_consolidado = set(df_posicoes["cnpj_fundo"].unique())
    _cotas_entries = df_posicoes[df_posicoes["ativo"].str.startswith("FUNDO ", na=False)]
    if not _cotas_entries.empty:
        _cnpjs_investidos = set(
            _cotas_entries["ativo"].str.replace("FUNDO ", "", regex=False).unique()
        )
        _cnpjs_sem_dados = {c for c in _cnpjs_investidos
                           if c and len(c) == 14 and c not in cnpjs_no_consolidado}
        if _cnpjs_sem_dados:
            print(f"\n[4b] Buscando CVM sob demanda para {len(_cnpjs_sem_dados)} fundos investidos...")
            t0 = time.time()
            df_cvm_extra = buscar_carteiras_cvm_sob_demanda(
                tuple(_cnpjs_sem_dados), meses_max=6)
            if not df_cvm_extra.empty:
                df_posicoes = pd.concat([df_posicoes, df_cvm_extra], ignore_index=True)
                print(f"  -> {len(df_cvm_extra)} registros adicionais de "
                      f"{df_cvm_extra['cnpj_fundo'].nunique()} fundos em {time.time()-t0:.1f}s")
            else:
                print(f"  -> Nenhum dado CVM encontrado para os fundos investidos ({time.time()-t0:.1f}s)")

    df_posicoes.to_parquet(os.path.join(DATA_DIR, "posicoes_consolidado.parquet"), index=False)
    print(f"  -> Total final: {len(df_posicoes)} registros, {df_posicoes['cnpj_fundo'].nunique()} CNPJs")

    # ── 5. Cotas dos fundos (inf_diario) ──
    print("\n[5/8] Exportando cotas dos fundos (10 anos)...")
    t0 = time.time()
    all_cnpjs_cotas = tuple(set(
        df_fundos["cnpj_norm"].dropna().tolist()
    ))
    df_cotas = carregar_cotas_fundos(all_cnpjs_cotas, meses=120)
    cotas_path = os.path.join(DATA_DIR, "cotas_consolidado.parquet")
    df_cotas.to_parquet(cotas_path, index=False)
    print(f"  -> {len(df_cotas)} registros de cotas em {time.time()-t0:.1f}s")

    # ── 6. Estatísticas do universo ──
    print("\n[6/8] Calculando estatisticas do universo (10 anos)...")
    t0 = time.time()
    df_stats = carregar_universo_stats(meses=120)
    stats_path = os.path.join(DATA_DIR, "universo_stats.parquet")
    if not df_stats.empty:
        df_stats.to_parquet(stats_path, index=False)
        print(f"  -> {len(df_stats)} datas com stats em {time.time()-t0:.1f}s")
    else:
        print(f"  -> Sem dados de universo (cache pode estar indisponivel)")

    # ── 7. Explosão: dados dos PDFs BTG para modo cloud ──
    print("\n[7/8] Exportando dados de Explosao (PDFs BTG)...")
    t0 = time.time()
    import pdf_parser

    FUNDOS_RV_TAG = [
        "VIT LB FIA", "VIT ACOES FIA", "TRANCOSO IBOV FIA",
        "DUNAJUKO FIA", "JUBA II FIA", "PROFITABLE G FIA",
        "SOLIS FIA", "TB ATMOS FC FIA",
    ]

    if pdf_parser._pdf_dir_exists():
        datas_pdf = pdf_parser.listar_datas_disponiveis()
        all_portfolios = []
        all_resumos = []
        all_acoes_diretas = []

        # Exportar as 20 datas mais recentes (para histórico de explosão)
        for data_pdf in datas_pdf[:20]:
            fundos_pdf = pdf_parser.listar_fundos_pdf(data_pdf)
            fundos_rv = [f for f in fundos_pdf if f in FUNDOS_RV_TAG]
            if not fundos_rv:
                fundos_rv = [f for f in fundos_pdf if "FIA" in f.upper()]

            for fundo in fundos_rv:
                # Portfolio investido (fundos)
                df_port = pdf_parser.extrair_portfolio_investido(data_pdf, fundo)
                if not df_port.empty:
                    df_port["data_pdf"] = data_pdf
                    df_port["fundo_tag"] = fundo
                    all_portfolios.append(df_port)

                # Ações diretas (seção "Ações" do PDF)
                df_acoes = pdf_parser.extrair_acoes_diretas(data_pdf, fundo)
                if not df_acoes.empty:
                    df_acoes["data_pdf"] = data_pdf
                    df_acoes["fundo_tag"] = fundo
                    all_acoes_diretas.append(df_acoes)

                # Resumo
                resumo = pdf_parser.extrair_resumo(data_pdf, fundo)
                if resumo:
                    resumo["data_pdf"] = data_pdf
                    resumo["fundo_tag"] = fundo
                    all_resumos.append(resumo)

        if all_portfolios:
            df_explosao = pd.concat(all_portfolios, ignore_index=True)
            df_explosao.to_parquet(os.path.join(DATA_DIR, "explosao_portfolios.parquet"), index=False)
            print(f"  -> {len(df_explosao)} holdings de {len(all_portfolios)} portfolios")
        else:
            print(f"  -> Nenhum portfolio extraido")

        if all_acoes_diretas:
            df_acoes_dir_all = pd.concat(all_acoes_diretas, ignore_index=True)
            df_acoes_dir_all.to_parquet(os.path.join(DATA_DIR, "explosao_acoes_diretas.parquet"), index=False)
            n_fundos_dir = df_acoes_dir_all["fundo_tag"].nunique()
            print(f"  -> {len(df_acoes_dir_all)} acoes diretas de {n_fundos_dir} fundos")
        else:
            print(f"  -> Nenhuma acao direta encontrada")

        if all_resumos:
            df_resumos = pd.DataFrame(all_resumos)
            df_resumos.to_parquet(os.path.join(DATA_DIR, "explosao_resumos.parquet"), index=False)
            print(f"  -> {len(df_resumos)} resumos exportados")

        print(f"  -> {time.time()-t0:.1f}s")
    else:
        print(f"  -> Diretorio de PDFs nao encontrado (pulando)")

    # ── 8. Fundamentals para Explosão (yahoo_finance.db) ──
    print("\n[8/8] Exportando dados fundamentalistas para Explosao...")
    t0 = time.time()
    YAHOO_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "yahoo_finance", "yahoo_finance.db")
    if os.path.exists(YAHOO_DB):
        import sqlite3
        conn = sqlite3.connect(YAHOO_DB)
        df_fund = pd.read_sql_query(
            "SELECT ticker, indicador, valor FROM fundamentalistas WHERE ticker LIKE '%.SA'",
            conn
        )
        conn.close()
        if not df_fund.empty:
            fund_path = os.path.join(DATA_DIR, "fundamentals_explosao.parquet")
            df_fund.to_parquet(fund_path, index=False)
            n_tickers = df_fund["ticker"].nunique()
            n_indicadores = df_fund["indicador"].nunique()
            print(f"  -> {len(df_fund)} registros ({n_tickers} tickers, {n_indicadores} indicadores)")
        else:
            print(f"  -> Nenhum dado fundamentalista encontrado")
    else:
        print(f"  -> yahoo_finance.db nao encontrado em {YAHOO_DB} (pulando)")
    print(f"  -> {time.time()-t0:.1f}s")

    # Resumo
    total_size = sum(
        os.path.getsize(os.path.join(DATA_DIR, f))
        for f in os.listdir(DATA_DIR) if f.endswith(".parquet")
    )
    print(f"\n{'=' * 60}")
    print(f"CONCLUIDO! Total: {total_size / 1e6:.1f} MB em data/")
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith(".parquet"):
            size = os.path.getsize(os.path.join(DATA_DIR, f))
            print(f"  {f}: {size / 1e6:.2f} MB")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
