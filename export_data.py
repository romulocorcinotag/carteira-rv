"""
Script de exportação INCREMENTAL de dados para deploy cloud.

Na primeira vez, baixa tudo (36 meses CVM + todos XMLs).
Nas próximas execuções:
  - XMLs: só processa novos arquivos (compara com data mais recente no parquet)
  - CVM: só baixa meses que ainda não estão no parquet
  - Reconstrói consolidado com dedup

Executar localmente quando quiser atualizar os dados:
    python export_data.py          # incremental (padrão)
    python export_data.py --full   # força reprocessamento completo

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
    _download_cvm_blc4,
    _download_cvm_pl,
    _normalizar_cnpj,
    BENCHMARK_CNPJS,
)
from sector_map import classificar_setor

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _dedup_consolidado(df_posicoes, df_fundos):
    """Aplica dedup de CNPJ-FOCO e ativos duplicados."""
    foco_map = {}
    for _, row in df_fundos.iterrows():
        foco = row["cnpj_foco_norm"]
        direto = row["cnpj_norm"]
        if foco and foco != direto and foco != "":
            foco_map[foco] = direto

    if df_posicoes.empty:
        return df_posicoes

    foco_cnpjs_set = set(foco_map.keys())
    df_posicoes["_is_foco"] = df_posicoes["cnpj_fundo"].isin(foco_cnpjs_set)
    df_posicoes["cnpj_fundo"] = df_posicoes["cnpj_fundo"].map(lambda x: foco_map.get(x, x))

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
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    mode = "COMPLETO" if args.full else "INCREMENTAL"
    print(f"EXPORTACAO DE DADOS ({mode})")
    print("=" * 60)

    # ── 1. Fundos RV (sempre atualiza) ──
    print("\n[1/6] Carregando fundos RV...")
    t0 = time.time()
    df_fundos = carregar_fundos_rv()
    print(f"  -> {len(df_fundos)} fundos em {time.time()-t0:.1f}s")
    df_fundos.to_parquet(os.path.join(DATA_DIR, "fundos_rv.parquet"), index=False)

    cnpjs_direto = set(df_fundos["cnpj_norm"].dropna().tolist())
    cnpjs_foco = set(df_fundos["cnpj_foco_norm"].dropna().tolist()) - {""}
    todos_cnpjs = tuple(cnpjs_direto | cnpjs_foco)

    # ── 2. XMLs (incremental: só novos) ──
    xml_path = os.path.join(DATA_DIR, "posicoes_xml.parquet")
    if not args.full and os.path.exists(xml_path):
        print("\n[2/6] XMLs: verificando incrementalmente...")
        df_xml_old = pd.read_parquet(xml_path)
        df_xml_old["data"] = pd.to_datetime(df_xml_old["data"])
        old_max_date = df_xml_old["data"].max()
        print(f"  Dados existentes ate: {old_max_date}")

        # Reprocessar tudo (XMLs são rápidos ~14s, e garantem consistência)
        # mas só re-exportar se houver dados novos
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
        print("\n[2/6] Processando todos os XMLs...")
        t0 = time.time()
        df_xml = carregar_dados_xml(todos_cnpjs)
        print(f"  -> {len(df_xml)} registros XML em {time.time()-t0:.1f}s")
        df_xml.to_parquet(xml_path, index=False)

    # ── 3. CVM (incremental: só meses novos) ──
    cvm_path = os.path.join(DATA_DIR, "posicoes_cvm.parquet")
    cnpjs_com_xml = tuple(set(df_xml["cnpj_fundo"].unique())) if not df_xml.empty else ()

    if not args.full and os.path.exists(cvm_path):
        print("\n[3/6] CVM: verificando meses novos...")
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
            cnpjs_alvo = set(todos_cnpjs) - set(cnpjs_com_xml)
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
        print("\n[3/6] Baixando todos os dados CVM (36 meses)...")
        t0 = time.time()
        df_cvm = carregar_dados_cvm(todos_cnpjs, cnpjs_com_xml, meses=36)
        print(f"  -> {len(df_cvm)} registros CVM em {time.time()-t0:.1f}s")
        df_cvm.to_parquet(cvm_path, index=False)

    # ── 4. Consolidar com dedup ──
    print("\n[4/6] Consolidando com deduplicacao...")
    df_posicoes = pd.concat([df_xml, df_cvm], ignore_index=True)
    df_posicoes = _dedup_consolidado(df_posicoes, df_fundos)

    df_posicoes.to_parquet(os.path.join(DATA_DIR, "posicoes_consolidado.parquet"), index=False)
    print(f"  -> {len(df_posicoes)} registros consolidados")
    print(f"  -> CNPJs com dados: {df_posicoes['cnpj_fundo'].nunique()}")

    # ── 5. Cotas dos fundos (inf_diario) ──
    print("\n[5/6] Exportando cotas dos fundos...")
    t0 = time.time()
    all_cnpjs_cotas = tuple(set(
        df_fundos["cnpj_norm"].dropna().tolist()
    ))
    df_cotas = carregar_cotas_fundos(all_cnpjs_cotas, meses=36)
    cotas_path = os.path.join(DATA_DIR, "cotas_consolidado.parquet")
    df_cotas.to_parquet(cotas_path, index=False)
    print(f"  -> {len(df_cotas)} registros de cotas em {time.time()-t0:.1f}s")

    # ── 6. Estatísticas do universo ──
    print("\n[6/6] Calculando estatisticas do universo...")
    t0 = time.time()
    df_stats = carregar_universo_stats(meses=36)
    stats_path = os.path.join(DATA_DIR, "universo_stats.parquet")
    if not df_stats.empty:
        df_stats.to_parquet(stats_path, index=False)
        print(f"  -> {len(df_stats)} datas com stats em {time.time()-t0:.1f}s")
    else:
        print(f"  -> Sem dados de universo (cache pode estar indisponivel)")

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
