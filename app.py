import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import base64
from collections import Counter

from data_loader import carregar_todos_dados, carregar_fundos_rv

# ──────────────────────────────────────────────────────────────────────────────
# Paleta TAG Investimentos
# ──────────────────────────────────────────────────────────────────────────────
TAG_VERMELHO = "#630D24"
TAG_OFFWHITE = "#E6E4DB"
TAG_LARANJA = "#FF8853"
TAG_BRANCO = "#FFFFFF"
TAG_CINZA_ESCURO = "#2C1A1A"
TAG_CHART_COLORS = [
    "#630D24", "#FF8853", "#002A6E", "#5C85F7", "#58C6F5",
    "#A485F2", "#6BDE97", "#FFBB00", "#ED5A6E", "#477C88",
    "#8B5CF6", "#F97316", "#10B981", "#EF4444", "#3B82F6",
    "#D946EF", "#14B8A6", "#F59E0B", "#EC4899", "#6366F1",
]

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Carteira RV - TAG Investimentos",
    page_icon="\U0001F4C8",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(_APP_DIR, "..", "luz_amarela", "tag_logo_rodape.png")
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = os.path.join(_APP_DIR, "assets", "tag_logo_rodape.png")


def get_logo_base64():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
        .stApp {{
            font-family: 'Tahoma', 'Inter', 'Segoe UI', sans-serif;
        }}
        .stMarkdown p, .stMarkdown li {{
            font-size: 1.05rem !important;
            line-height: 1.7 !important;
        }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 0px; }}
        .stTabs [data-baseweb="tab"] {{
            font-size: 16px !important; font-weight: 500 !important;
            padding: 14px 28px !important; color: #666 !important;
        }}
        .stTabs [aria-selected="true"] {{
            font-weight: 700 !important; color: {TAG_VERMELHO} !important;
            border-bottom: 3px solid {TAG_VERMELHO} !important;
        }}
        .stDataFrame th {{
            font-size: 13px !important; font-weight: 700 !important;
            padding: 10px 14px !important;
            background: {TAG_VERMELHO} !important; color: {TAG_BRANCO} !important;
        }}
        .stDataFrame td {{ padding: 8px 14px !important; font-size: 13px !important; }}
        .stMarkdown table {{
            width: 100% !important; border-collapse: collapse !important;
            margin: 12px 0 !important;
        }}
        .stMarkdown table th {{
            background: {TAG_VERMELHO} !important; color: {TAG_BRANCO} !important;
            padding: 12px 18px !important; text-align: left !important;
            font-weight: 600 !important;
        }}
        .stMarkdown table td {{
            padding: 10px 18px !important; border-bottom: 1px solid #eee !important;
        }}
        .stMarkdown table tr:nth-child(even) td {{
            background: #f9f8f5 !important;
        }}
        .tag-header {{
            display: flex; align-items: center; gap: 24px;
            padding: 24px 0 18px 0; margin-bottom: 8px;
        }}
        .tag-logo-box {{
            background: {TAG_VERMELHO}; border-radius: 14px;
            padding: 14px 22px; display: flex; align-items: center;
            justify-content: center; min-height: 56px;
        }}
        .tag-logo-box img {{ height: 56px; filter: brightness(0) invert(1); }}
        .tag-header-text h1 {{
            margin: 0; font-size: 2.5rem; font-weight: 700;
            color: {TAG_VERMELHO}; letter-spacing: -0.5px;
        }}
        .tag-header-text p {{
            margin: 4px 0 0 0; font-size: 1.1rem; color: #777;
        }}
        .tag-divider {{
            height: 3px;
            background: linear-gradient(90deg, {TAG_VERMELHO}, {TAG_LARANJA}, transparent);
            margin: 22px 0; border: none;
        }}
        .tag-section-divider {{
            height: 1px;
            background: linear-gradient(90deg, {TAG_VERMELHO}33, transparent);
            margin: 32px 0 24px 0; border: none;
        }}
        .tag-metric-card {{
            background: {TAG_BRANCO}; border-radius: 12px;
            padding: 20px 16px; text-align: center;
            border-left: 5px solid {TAG_VERMELHO};
            box-shadow: 0 2px 12px rgba(0,0,0,0.07);
        }}
        .tag-metric-card .value {{
            font-size: 2rem; font-weight: 700;
            color: {TAG_VERMELHO}; line-height: 1.1;
        }}
        .tag-metric-card .label {{
            font-size: 0.85rem; color: #777; margin-top: 6px; font-weight: 500;
        }}
        .tag-section-title {{
            font-size: 1.15rem; font-weight: 600; color: {TAG_VERMELHO};
            margin: 24px 0 12px 0; padding-bottom: 8px;
            border-bottom: 2px solid {TAG_VERMELHO}22;
        }}
        div[data-testid="stSidebar"] {{ display: none !important; }}
    </style>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────
def render_header():
    logo_b64 = get_logo_base64()
    logo_html = f'<div class="tag-logo-box"><img src="data:image/png;base64,{logo_b64}"></div>' if logo_b64 else ""
    st.markdown(f"""
    <div class="tag-header">
        {logo_html}
        <div class="tag-header-text">
            <h1>Carteira RV</h1>
            <p>Evolucao de Carteiras dos Fundos de Renda Variavel</p>
        </div>
    </div>
    <div class="tag-divider"></div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Metric card
# ──────────────────────────────────────────────────────────────────────────────
def metric_card(label, value):
    return f"""
    <div class="tag-metric-card">
        <div class="value">{value}</div>
        <div class="label">{label}</div>
    </div>
    """


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _hex_to_rgba(hex_color, alpha=0.8):
    h = hex_color.lstrip("#")
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _chart_layout(fig, title, height=500, y_title="% do PL", y_suffix="%",
                  legend_h=True, margin_b=40):
    """Aplica layout padrão TAG a um gráfico Plotly."""
    legend = dict(
        orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)
    ) if legend_h else dict(font=dict(size=11))

    fig.update_layout(
        title=dict(text=title, font=dict(size=17, color=TAG_VERMELHO)),
        height=height, template="plotly_white",
        yaxis=dict(title=y_title, ticksuffix=y_suffix) if y_title else {},
        legend=legend,
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=60, b=margin_b),
        font=dict(family="Tahoma, sans-serif"),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Gráficos
# ──────────────────────────────────────────────────────────────────────────────
def grafico_stacked_area(df_pivot, titulo, top_n=15):
    media = df_pivot.mean().sort_values(ascending=False)
    top_cols = media.head(top_n).index.tolist()
    outros = [c for c in df_pivot.columns if c not in top_cols]

    fig = go.Figure()
    for i, col in enumerate(top_cols):
        fig.add_trace(go.Scatter(
            x=df_pivot.index, y=df_pivot[col],
            name=col, stackgroup="one",
            line=dict(width=0.5),
            fillcolor=_hex_to_rgba(TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)], 0.8),
            hovertemplate=f"<b>{col}</b><br>%{{x|%b/%Y}}: %{{y:.1f}}%<extra></extra>",
        ))

    if outros:
        df_outros = df_pivot[outros].sum(axis=1)
        fig.add_trace(go.Scatter(
            x=df_pivot.index, y=df_outros,
            name="Outros", stackgroup="one",
            line=dict(width=0.5, color="#CCCCCC"),
            fillcolor="rgba(204,204,204,0.5)",
        ))

    return _chart_layout(fig, titulo)


def grafico_linhas(df_pivot, titulo, top_n=15):
    media = df_pivot.mean().sort_values(ascending=False)
    top_cols = media.head(top_n).index.tolist()

    fig = go.Figure()
    for i, col in enumerate(top_cols):
        fig.add_trace(go.Scatter(
            x=df_pivot.index, y=df_pivot[col],
            name=col, mode="lines+markers",
            line=dict(width=2, color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
            marker=dict(size=4),
            hovertemplate=f"<b>{col}</b><br>%{{x|%b/%Y}}: %{{y:.1f}}%<extra></extra>",
        ))

    return _chart_layout(fig, titulo)


def grafico_pl(df_pl, titulo):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_pl["data"], y=df_pl["pl"] / 1e6,
        mode="lines+markers",
        line=dict(width=2.5, color=TAG_VERMELHO),
        marker=dict(size=5),
        fill="tozeroy", fillcolor=_hex_to_rgba(TAG_VERMELHO, 0.08),
        hovertemplate="<b>%{x|%b/%Y}</b><br>R$ %{y:,.1f}M<extra></extra>",
    ))
    return _chart_layout(fig, titulo, height=400, y_title="PL (R$ milhoes)", y_suffix="",
                         legend_h=False)


def grafico_n_ativos(df_n, titulo):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_n["data"], y=df_n["n_ativos"],
        marker_color=TAG_LARANJA,
        marker=dict(line=dict(width=0)),
        hovertemplate="<b>%{x|%b/%Y}</b><br>%{y} ativos<extra></extra>",
    ))
    return _chart_layout(fig, titulo, height=350, y_title="Qtd. Ativos", y_suffix="",
                         legend_h=False)


def grafico_concentracao(df, cnpj, titulo_prefix):
    """Gera gráfico de evolução da concentração: maior posição e soma das top 5."""
    d = df[df["cnpj_fundo"] == cnpj].copy()
    if d.empty:
        return None

    datas = sorted(d["data"].unique())
    top1_pcts = []
    top5_pcts = []
    top1_nomes = []

    for dt in datas:
        snapshot = d[d["data"] == dt].sort_values("pct_pl", ascending=False)
        if snapshot.empty:
            top1_pcts.append(0)
            top5_pcts.append(0)
            top1_nomes.append("")
            continue
        top1_pcts.append(snapshot["pct_pl"].iloc[0])
        top1_nomes.append(snapshot["ativo"].iloc[0])
        top5_pcts.append(snapshot["pct_pl"].head(5).sum())

    fig = go.Figure()

    # Área do top 5 (fundo)
    fig.add_trace(go.Scatter(
        x=datas, y=top5_pcts,
        name="Top 5 (soma)",
        mode="lines",
        line=dict(width=1, color=TAG_LARANJA),
        fill="tozeroy",
        fillcolor=_hex_to_rgba(TAG_LARANJA, 0.15),
        hovertemplate="<b>%{x|%b/%Y}</b><br>Top 5: %{y:.1f}%<extra></extra>",
    ))

    # Linha do top 1
    fig.add_trace(go.Scatter(
        x=datas, y=top1_pcts,
        name="Maior posicao",
        mode="lines+markers",
        line=dict(width=2.5, color=TAG_VERMELHO),
        marker=dict(size=5),
        customdata=top1_nomes,
        hovertemplate="<b>%{x|%b/%Y}</b><br>%{customdata}: %{y:.1f}%<extra></extra>",
    ))

    return _chart_layout(fig, f"{titulo_prefix} — Concentracao (Top 1 e Top 5)",
                         height=400, y_title="% do PL")


# ──────────────────────────────────────────────────────────────────────────────
# Preparação de dados
# ──────────────────────────────────────────────────────────────────────────────
def preparar_pivot_ativo(df, cnpj):
    d = df[df["cnpj_fundo"] == cnpj].copy()
    return d.pivot_table(index="data", columns="ativo", values="pct_pl", aggfunc="sum").fillna(0)


def preparar_pivot_setor(df, cnpj):
    d = df[df["cnpj_fundo"] == cnpj].copy()
    return d.pivot_table(index="data", columns="setor", values="pct_pl", aggfunc="sum").fillna(0)


def tabela_carteira_atual(df, cnpj):
    d = df[df["cnpj_fundo"] == cnpj].copy()
    if d.empty:
        return pd.DataFrame()
    ultima_data = d["data"].max()
    d = d[d["data"] == ultima_data].copy()
    d = d.sort_values("pct_pl", ascending=False)
    d["pct_pl_fmt"] = d["pct_pl"].map(lambda x: f"{x:.2f}%")
    d["valor_fmt"] = d["valor"].map(lambda x: f"R$ {x:,.0f}".replace(",", "."))
    return d[["ativo", "setor", "valor_fmt", "pct_pl_fmt", "pct_pl"]].rename(columns={
        "ativo": "Ativo", "setor": "Setor", "valor_fmt": "Valor", "pct_pl_fmt": "% PL"
    }).reset_index(drop=True)


def render_tabela_carteira_html(tbl):
    """Gera HTML profissional para a tabela de carteira atual com barras de progresso."""
    if tbl.empty:
        return ""
    max_pct = tbl["pct_pl"].max() if tbl["pct_pl"].max() > 0 else 1

    rows_html = ""
    for i, row in tbl.iterrows():
        bar_width = min(100, (row["pct_pl"] / max_pct) * 100)
        # Cor da barra gradiente: vermelho TAG para maiores, laranja para menores
        if row["pct_pl"] >= max_pct * 0.5:
            bar_color = TAG_VERMELHO
        elif row["pct_pl"] >= max_pct * 0.25:
            bar_color = "#B44A5E"
        else:
            bar_color = TAG_LARANJA

        rank = i + 1
        zebra = "#f9f8f5" if i % 2 == 1 else "#ffffff"

        rows_html += f"""
        <tr style="background: {zebra};">
            <td style="padding: 10px 14px; text-align: center; font-weight: 600; color: #999; font-size: 12px; width: 40px;">{rank}</td>
            <td style="padding: 10px 14px; font-weight: 700; color: {TAG_CINZA_ESCURO}; font-size: 14px; white-space: nowrap;">
                {row['Ativo']}
            </td>
            <td style="padding: 10px 14px; color: #666; font-size: 13px;">{row['Setor']}</td>
            <td style="padding: 10px 14px; text-align: right; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; color: {TAG_CINZA_ESCURO};">
                {row['Valor']}
            </td>
            <td style="padding: 10px 14px; width: 200px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="flex: 1; background: #f0efea; border-radius: 4px; height: 18px; overflow: hidden;">
                        <div style="width: {bar_width}%; height: 100%; background: {bar_color}; border-radius: 4px; transition: width 0.3s;"></div>
                    </div>
                    <span style="font-weight: 700; font-size: 13px; color: {TAG_CINZA_ESCURO}; min-width: 52px; text-align: right;">
                        {row['% PL']}
                    </span>
                </div>
            </td>
        </tr>"""

    total_pct = tbl["pct_pl"].sum()
    n_ativos = len(tbl)

    nota_pct = ""
    if total_pct < 85:
        nota_pct = f"""
        <tr style="background: #fff9f0;">
            <td colspan="5" style="padding: 8px 14px; font-size: 11px; color: #999; text-align: center;">
                * O % PL e calculado sobre o patrimonio total do fundo. Fundos com posicoes em renda fixa, caixa ou derivativos terao alocacao em acoes inferior a 100%.
            </td>
        </tr>"""

    html = f"""
    <div style="border-radius: 12px; overflow: hidden; box-shadow: 0 2px 16px rgba(0,0,0,0.08); border: 1px solid #e8e6df; margin: 8px 0 16px 0;">
        <table style="width: 100%; border-collapse: collapse; font-family: 'Tahoma', 'Inter', sans-serif;">
            <thead>
                <tr style="background: {TAG_VERMELHO};">
                    <th style="padding: 12px 14px; color: white; font-size: 12px; font-weight: 600; text-align: center; width: 40px;">#</th>
                    <th style="padding: 12px 14px; color: white; font-size: 12px; font-weight: 600; text-align: left;">ATIVO</th>
                    <th style="padding: 12px 14px; color: white; font-size: 12px; font-weight: 600; text-align: left;">SETOR</th>
                    <th style="padding: 12px 14px; color: white; font-size: 12px; font-weight: 600; text-align: right;">VALOR</th>
                    <th style="padding: 12px 14px; color: white; font-size: 12px; font-weight: 600; text-align: left; width: 200px;">% PL</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
            <tfoot>
                <tr style="background: #f5f4ef; border-top: 2px solid {TAG_VERMELHO}33;">
                    <td colspan="4" style="padding: 10px 14px; font-weight: 600; color: #777; font-size: 12px; text-align: right;">
                        {n_ativos} ativos &nbsp;|&nbsp; Total alocado em acoes:
                    </td>
                    <td style="padding: 10px 14px; font-weight: 700; font-size: 14px; color: {TAG_VERMELHO};">
                        {total_pct:.1f}%
                    </td>
                </tr>
                {nota_pct}
            </tfoot>
        </table>
    </div>"""
    return html


# ──────────────────────────────────────────────────────────────────────────────
# Funções de sobreposição
# ──────────────────────────────────────────────────────────────────────────────
def _calcular_sobreposicao_ativos(cart_a: dict, cart_b: dict) -> float:
    """Calcula sobreposição entre dois dicts {ativo: pct_pl}.
    Sobreposição = soma de min(pct_a, pct_b) para cada ativo em comum.
    """
    common = set(cart_a.keys()) & set(cart_b.keys())
    return sum(min(cart_a[k], cart_b[k]) for k in common)


def _calcular_sobreposicao_setores(set_a: dict, set_b: dict) -> float:
    """Calcula sobreposição entre dois dicts {setor: pct_pl}.
    Exclui setores genéricos ('Outros') que inflam artificialmente o resultado.
    """
    excluir = {"Outros", "Outros/Não classificado", ""}
    common = (set(set_a.keys()) & set(set_b.keys())) - excluir
    return sum(min(set_a[k], set_b[k]) for k in common)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    inject_css()

    # Carregar dados
    df_fundos, df_posicoes = carregar_todos_dados()
    render_header()

    if df_posicoes.empty:
        st.warning("Nenhum dado de carteira encontrado.")
        return

    # ── Filtros ──
    col_cat, col_tier, col_fundo = st.columns([2, 1, 4])

    categorias = sorted(df_fundos["categoria"].dropna().unique().tolist())
    with col_cat:
        cat_sel = st.multiselect("Categoria", options=categorias, default=[])

    tiers = sorted(df_fundos["tier"].dropna().unique().tolist())
    with col_tier:
        tier_sel = st.multiselect("Tier", options=tiers, default=[])

    df_fundos_filtrado = df_fundos.copy()
    if cat_sel:
        df_fundos_filtrado = df_fundos_filtrado[df_fundos_filtrado["categoria"].isin(cat_sel)]
    if tier_sel:
        df_fundos_filtrado = df_fundos_filtrado[df_fundos_filtrado["tier"].isin(tier_sel)]

    cnpjs_com_dados = set(df_posicoes["cnpj_fundo"].unique())
    df_fundos_filtrado = df_fundos_filtrado[df_fundos_filtrado["cnpj_norm"].isin(cnpjs_com_dados)]

    nome_cnpj_map = dict(zip(df_fundos_filtrado["nome"], df_fundos_filtrado["cnpj_norm"]))
    nomes_disponiveis = sorted(nome_cnpj_map.keys())

    with col_fundo:
        fundos_sel = st.multiselect(
            "Fundo(s)",
            options=nomes_disponiveis,
            default=nomes_disponiveis[:1] if nomes_disponiveis else [],
            max_selections=15,
        )

    if not fundos_sel:
        st.info("Selecione pelo menos um fundo para visualizar a carteira.")
        return

    cnpjs_sel = [nome_cnpj_map[n] for n in fundos_sel]
    df_pos = df_posicoes[df_posicoes["cnpj_fundo"].isin(cnpjs_sel)].copy()

    # ── Tabs ──
    tab_ativo, tab_setor, tab_pl, tab_comparativo = st.tabs([
        "Por Ativo", "Por Setor", "Evolucao PL", "Comparativo"
    ])

    # ══════════════════════════════════════════════════════════════════════
    # TAB 1: POR ATIVO
    # ══════════════════════════════════════════════════════════════════════
    with tab_ativo:
        for idx, nome_fundo in enumerate(fundos_sel):
            cnpj = nome_cnpj_map[nome_fundo]
            df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]

            if df_f.empty:
                st.warning(f"Sem dados para {nome_fundo}")
                continue

            st.markdown(f"### {nome_fundo}")

            ultima = df_f[df_f["data"] == df_f["data"].max()]
            pl_atual = ultima["pl"].iloc[0] if not ultima.empty else 0
            n_ativos = ultima["ativo"].nunique() if not ultima.empty else 0
            top_ativo = ultima.sort_values("pct_pl", ascending=False).iloc[0] if not ultima.empty else None
            fonte = df_f["fonte"].iloc[0] if not df_f.empty else ""
            dt_ref = df_f["data"].max().strftime("%d/%m/%Y") if not df_f.empty else ""

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(metric_card("PL", f"R$ {pl_atual/1e6:.1f}M"), unsafe_allow_html=True)
            with c2:
                st.markdown(metric_card("Ativos", str(n_ativos)), unsafe_allow_html=True)
            with c3:
                if top_ativo is not None:
                    st.markdown(metric_card("Top Holding", f"{top_ativo['ativo']}<br><span style='font-size:1.1rem'>({top_ativo['pct_pl']:.1f}%)</span>"), unsafe_allow_html=True)
            with c4:
                st.markdown(metric_card("Fonte / Data", f"{fonte}<br><span style='font-size:1.1rem'>{dt_ref}</span>"), unsafe_allow_html=True)

            st.markdown("")

            tbl = tabela_carteira_atual(df_pos, cnpj)
            if not tbl.empty:
                with st.expander("Carteira Atual (detalhada)", expanded=False):
                    html_table = render_tabela_carteira_html(tbl)
                    st.markdown(html_table, unsafe_allow_html=True)

            pivot = preparar_pivot_ativo(df_pos, cnpj)
            if not pivot.empty:
                st.plotly_chart(
                    grafico_stacked_area(pivot, f"{nome_fundo} — Composicao por Ativo"),
                    width="stretch",
                )
                st.plotly_chart(
                    grafico_linhas(pivot, f"{nome_fundo} — Evolucao por Ativo"),
                    width="stretch",
                )

            # Gráfico de concentração (top 1 e top 5)
            fig_conc = grafico_concentracao(df_pos, cnpj, nome_fundo)
            if fig_conc is not None:
                st.plotly_chart(fig_conc, width="stretch")

            if idx < len(fundos_sel) - 1:
                st.markdown('<div class="tag-section-divider"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 2: POR SETOR
    # ══════════════════════════════════════════════════════════════════════
    with tab_setor:
        for idx, nome_fundo in enumerate(fundos_sel):
            cnpj = nome_cnpj_map[nome_fundo]
            df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]

            if df_f.empty:
                st.warning(f"Sem dados para {nome_fundo}")
                continue

            st.markdown(f"### {nome_fundo}")

            ultima_data = df_f["data"].max()
            setor_atual = df_f[df_f["data"] == ultima_data].groupby("setor")["pct_pl"].sum().sort_values(ascending=False)
            setor_df = setor_atual.reset_index()
            setor_df.columns = ["Setor", "% PL"]
            setor_df["% PL"] = setor_df["% PL"].map(lambda x: f"{x:.1f}%")
            with st.expander("Alocacao Setorial Atual", expanded=False):
                st.dataframe(setor_df, width="stretch", hide_index=True)

            pivot_s = preparar_pivot_setor(df_pos, cnpj)
            if not pivot_s.empty:
                st.plotly_chart(
                    grafico_stacked_area(pivot_s, f"{nome_fundo} — Composicao por Setor", top_n=20),
                    width="stretch",
                )
                st.plotly_chart(
                    grafico_linhas(pivot_s, f"{nome_fundo} — Evolucao por Setor", top_n=20),
                    width="stretch",
                )

            if idx < len(fundos_sel) - 1:
                st.markdown('<div class="tag-section-divider"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 3: EVOLUÇÃO PL
    # ══════════════════════════════════════════════════════════════════════
    with tab_pl:
        for idx, nome_fundo in enumerate(fundos_sel):
            cnpj = nome_cnpj_map[nome_fundo]
            df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]

            if df_f.empty:
                continue

            st.markdown(f"### {nome_fundo}")

            pl_mensal = df_f.groupby("data")["pl"].first().reset_index()
            st.plotly_chart(
                grafico_pl(pl_mensal, f"{nome_fundo} — Patrimonio Liquido"),
                width="stretch",
            )

            n_ativos = df_f.groupby("data")["ativo"].nunique().reset_index()
            n_ativos.columns = ["data", "n_ativos"]
            st.plotly_chart(
                grafico_n_ativos(n_ativos, f"{nome_fundo} — Numero de Ativos"),
                width="stretch",
            )

            if idx < len(fundos_sel) - 1:
                st.markdown('<div class="tag-section-divider"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 4: COMPARATIVO
    # ══════════════════════════════════════════════════════════════════════
    with tab_comparativo:
        if len(fundos_sel) < 2:
            st.info("Selecione 2 ou mais fundos para ver o comparativo.")
        else:
            # ── Preparar dados da carteira mais recente ──
            carteiras = {}     # nome -> {ativo: pct_pl}
            setores_map = {}   # nome -> {setor: pct_pl}
            nomes_comp = []
            for nome_fundo in fundos_sel:
                cnpj = nome_cnpj_map[nome_fundo]
                df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]
                if df_f.empty:
                    continue
                ultima = df_f["data"].max()
                df_ult = df_f[df_f["data"] == ultima]
                nomes_comp.append(nome_fundo)
                carteiras[nome_fundo] = dict(zip(df_ult["ativo"], df_ult["pct_pl"]))
                setores_map[nome_fundo] = df_ult.groupby("setor")["pct_pl"].sum().to_dict()

            if len(nomes_comp) < 2:
                st.warning("Dados insuficientes para comparacao.")
                return

            n = len(nomes_comp)
            # Nomes curtos para os eixos dos heatmaps
            labels = []
            for nm in nomes_comp:
                parts = nm.split()
                short = " ".join(parts[:3]) if len(parts) > 3 else nm
                if len(short) > 25:
                    short = short[:22] + "..."
                labels.append(short)

            # ─── 1. HEATMAP: Sobreposicao por Ativo ───
            st.markdown('<div class="tag-section-title">Sobreposicao por Ativo (% PL)</div>', unsafe_allow_html=True)
            st.caption("Cada celula mostra a soma dos min(% PL) dos ativos em comum entre dois fundos. Para cada ativo compartilhado, considera-se o menor peso entre os dois fundos.")

            # Calcular sobreposição (sem diagonal - usa NaN para não distorcer a escala de cor)
            overlap_ativos = np.full((n, n), np.nan)
            for i in range(n):
                for j in range(n):
                    if i != j:
                        overlap_ativos[i][j] = _calcular_sobreposicao_ativos(
                            carteiras[nomes_comp[i]], carteiras[nomes_comp[j]]
                        )

            # Texto: diagonal mostra qtd ativos, off-diagonal mostra %
            text_ativos = []
            for i in range(n):
                row = []
                for j in range(n):
                    if i == j:
                        n_at = len(carteiras[nomes_comp[i]])
                        row.append(f"{n_at} ativos")
                    else:
                        row.append(f"{overlap_ativos[i][j]:.1f}%")
                text_ativos.append(row)

            fig_heat_a = go.Figure(data=go.Heatmap(
                z=overlap_ativos,
                x=labels,
                y=labels,
                text=text_ativos,
                texttemplate="%{text}",
                textfont=dict(size=11, color="white"),
                colorscale=[
                    [0, "#e8eaf6"], [0.25, "#7986cb"],
                    [0.5, "#3f51b5"], [0.75, "#283593"],
                    [1, "#1a237e"]
                ],
                hovertemplate="<b>%{y}</b> x <b>%{x}</b><br>Sobreposicao: %{text}<extra></extra>",
                showscale=True,
                colorbar=dict(title="% PL", ticksuffix="%"),
            ))
            fig_heat_a.update_layout(
                height=max(420, 70 * n + 140),
                template="plotly_white",
                xaxis=dict(tickangle=45, side="bottom"),
                yaxis=dict(autorange="reversed"),
                font=dict(family="Tahoma, sans-serif", size=11),
                margin=dict(l=10, r=10, t=20, b=120),
            )
            st.plotly_chart(fig_heat_a, width="stretch")

            # ─── 2. HEATMAP: Sobreposicao por Setor ───
            st.markdown('<div class="tag-section-title">Sobreposicao por Setor (% PL)</div>', unsafe_allow_html=True)
            st.caption("Mesma logica aplicada por setor (excluindo setor 'Outros' para evitar inflacao artificial).")

            overlap_setores = np.full((n, n), np.nan)
            for i in range(n):
                for j in range(n):
                    if i != j:
                        overlap_setores[i][j] = _calcular_sobreposicao_setores(
                            setores_map[nomes_comp[i]], setores_map[nomes_comp[j]]
                        )

            text_setores = []
            for i in range(n):
                row = []
                for j in range(n):
                    if i == j:
                        n_set = len([s for s in setores_map[nomes_comp[i]] if s not in {"Outros", ""}])
                        row.append(f"{n_set} setores")
                    else:
                        row.append(f"{overlap_setores[i][j]:.1f}%")
                text_setores.append(row)

            fig_heat_s = go.Figure(data=go.Heatmap(
                z=overlap_setores,
                x=labels,
                y=labels,
                text=text_setores,
                texttemplate="%{text}",
                textfont=dict(size=11, color="white"),
                colorscale=[
                    [0, "#fce4ec"], [0.25, "#ef9a9a"],
                    [0.5, "#e53935"], [0.75, "#c62828"],
                    [1, "#630D24"]
                ],
                hovertemplate="<b>%{y}</b> x <b>%{x}</b><br>Sobreposicao: %{text}<extra></extra>",
                showscale=True,
                colorbar=dict(title="% PL", ticksuffix="%"),
            ))
            fig_heat_s.update_layout(
                height=max(420, 70 * n + 140),
                template="plotly_white",
                xaxis=dict(tickangle=45, side="bottom"),
                yaxis=dict(autorange="reversed"),
                font=dict(family="Tahoma, sans-serif", size=11),
                margin=dict(l=10, r=10, t=20, b=120),
            )
            st.plotly_chart(fig_heat_s, width="stretch")

            # ─── 3. Alocacao Setorial Comparada ───
            st.markdown('<div class="tag-section-title">Alocacao Setorial Comparada</div>', unsafe_allow_html=True)

            setores_comp = []
            for nome_fundo in nomes_comp:
                cnpj = nome_cnpj_map[nome_fundo]
                df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]
                if df_f.empty:
                    continue
                ultima = df_f["data"].max()
                setor_pct = df_f[df_f["data"] == ultima].groupby("setor")["pct_pl"].sum()
                setor_pct.name = nome_fundo
                setores_comp.append(setor_pct)

            if setores_comp:
                df_comp = pd.concat(setores_comp, axis=1).fillna(0)
                # Ordenar por soma total decrescente
                df_comp = df_comp.loc[df_comp.sum(axis=1).sort_values(ascending=False).index]

                fig_bar = go.Figure()
                for i, col in enumerate(df_comp.columns):
                    fig_bar.add_trace(go.Bar(
                        name=labels[i] if i < len(labels) else col,
                        x=df_comp.index,
                        y=df_comp[col],
                        marker_color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)],
                        hovertemplate=f"<b>{col}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
                    ))

                fig_bar.update_layout(
                    barmode="group",
                    height=480, template="plotly_white",
                    yaxis=dict(title="% do PL", ticksuffix="%"),
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Tahoma, sans-serif"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
                    margin=dict(l=40, r=20, t=20, b=40),
                )
                st.plotly_chart(fig_bar, width="stretch")

            # ─── 4. Sobreposicao Historica por Ativos ───
            st.markdown('<div class="tag-section-title">Sobreposicao Historica — Ativos</div>', unsafe_allow_html=True)
            st.caption("Evolucao da sobreposicao (soma min % PL dos ativos em comum) ao longo do tempo para cada par de fundos.")

            pares = []
            for i in range(len(nomes_comp)):
                for j in range(i + 1, len(nomes_comp)):
                    pares.append((nomes_comp[i], nomes_comp[j]))

            if pares:
                fig_hist = go.Figure()
                color_idx = 0

                for nome_a, nome_b in pares:
                    cnpj_a = nome_cnpj_map[nome_a]
                    cnpj_b = nome_cnpj_map[nome_b]
                    df_a = df_pos[df_pos["cnpj_fundo"] == cnpj_a]
                    df_b = df_pos[df_pos["cnpj_fundo"] == cnpj_b]

                    common_dates = sorted(set(df_a["data"].unique()) & set(df_b["data"].unique()))
                    if not common_dates:
                        continue

                    overlap_series = []
                    for dt in common_dates:
                        cart_a = dict(zip(df_a[df_a["data"] == dt]["ativo"], df_a[df_a["data"] == dt]["pct_pl"]))
                        cart_b = dict(zip(df_b[df_b["data"] == dt]["ativo"], df_b[df_b["data"] == dt]["pct_pl"]))
                        overlap_series.append(_calcular_sobreposicao_ativos(cart_a, cart_b))

                    la = labels[nomes_comp.index(nome_a)]
                    lb = labels[nomes_comp.index(nome_b)]
                    pair_label = f"{la} x {lb}"

                    fig_hist.add_trace(go.Scatter(
                        x=common_dates, y=overlap_series,
                        mode="lines+markers", name=pair_label,
                        line=dict(width=2.5, color=TAG_CHART_COLORS[color_idx % len(TAG_CHART_COLORS)]),
                        marker=dict(size=5),
                        hovertemplate=f"<b>{pair_label}</b><br>%{{x|%b/%Y}}: %{{y:.1f}}%<extra></extra>",
                    ))
                    color_idx += 1

                _chart_layout(fig_hist, "", y_title="% PL Sobreposto")
                st.plotly_chart(fig_hist, width="stretch")

            # ─── 5. Sobreposicao Historica por Setor ───
            st.markdown('<div class="tag-section-title">Sobreposicao Historica — Setores</div>', unsafe_allow_html=True)

            if pares:
                fig_hist_s = go.Figure()
                color_idx = 0

                for nome_a, nome_b in pares:
                    cnpj_a = nome_cnpj_map[nome_a]
                    cnpj_b = nome_cnpj_map[nome_b]
                    df_a = df_pos[df_pos["cnpj_fundo"] == cnpj_a]
                    df_b = df_pos[df_pos["cnpj_fundo"] == cnpj_b]

                    common_dates = sorted(set(df_a["data"].unique()) & set(df_b["data"].unique()))
                    if not common_dates:
                        continue

                    overlap_series = []
                    for dt in common_dates:
                        setor_a = df_a[df_a["data"] == dt].groupby("setor")["pct_pl"].sum().to_dict()
                        setor_b = df_b[df_b["data"] == dt].groupby("setor")["pct_pl"].sum().to_dict()
                        overlap_series.append(_calcular_sobreposicao_setores(setor_a, setor_b))

                    la = labels[nomes_comp.index(nome_a)]
                    lb = labels[nomes_comp.index(nome_b)]
                    pair_label = f"{la} x {lb}"

                    fig_hist_s.add_trace(go.Scatter(
                        x=common_dates, y=overlap_series,
                        mode="lines+markers", name=pair_label,
                        line=dict(width=2.5, color=TAG_CHART_COLORS[color_idx % len(TAG_CHART_COLORS)]),
                        marker=dict(size=5),
                        hovertemplate=f"<b>{pair_label}</b><br>%{{x|%b/%Y}}: %{{y:.1f}}%<extra></extra>",
                    ))
                    color_idx += 1

                _chart_layout(fig_hist_s, "", y_title="% PL Sobreposto")
                st.plotly_chart(fig_hist_s, width="stretch")

            # ─── 6. Ativos em Comum ───
            st.markdown('<div class="tag-section-title">Ativos em Comum</div>', unsafe_allow_html=True)

            # Pegar todos ativos de cada fundo
            all_holdings = {}
            for nome_fundo in nomes_comp:
                all_holdings[nome_fundo] = carteiras[nome_fundo]

            if len(all_holdings) >= 2:
                # Encontrar todos ativos que aparecem em pelo menos 2 fundos
                ativo_count = Counter()
                for holdings in all_holdings.values():
                    for ativo in holdings:
                        ativo_count[ativo] += 1

                ativos_compartilhados = {a for a, c in ativo_count.items() if c >= 2}

                if ativos_compartilhados:
                    st.caption(f"Ativos presentes em 2 ou mais fundos selecionados, com o respectivo % PL em cada fundo. Celulas vazias indicam que o fundo nao possui o ativo.")

                    rows = []
                    for ativo in sorted(ativos_compartilhados):
                        row_data = {"Ativo": ativo, "Fundos": ativo_count[ativo]}
                        pcts = []
                        for nome_fundo in nomes_comp:
                            pct = all_holdings.get(nome_fundo, {}).get(ativo, 0)
                            row_data[nome_fundo] = pct
                            if pct > 0:
                                pcts.append(pct)
                        row_data["_media"] = np.mean(pcts) if pcts else 0
                        rows.append(row_data)

                    df_common = pd.DataFrame(rows).sort_values(["Fundos", "_media"], ascending=[False, False])
                    df_common = df_common.drop(columns=["_media"])

                    # Formatar % PL (mostrar "-" para quem não tem)
                    for col in nomes_comp:
                        df_common[col] = df_common[col].map(lambda x: f"{x:.1f}%" if x > 0 else "—")

                    st.dataframe(df_common, width="stretch", hide_index=True,
                                 height=min(500, 35 * len(df_common) + 38))

                    st.caption(f"{len(ativos_compartilhados)} ativos compartilhados entre os {len(nomes_comp)} fundos.")
                else:
                    st.info("Nenhum ativo em comum entre os fundos selecionados.")

                # Tabela pairwise: qtd de ativos em comum por par
                st.markdown('<div class="tag-section-title">Numero de Ativos em Comum (por par)</div>', unsafe_allow_html=True)

                pair_data = []
                for i in range(len(nomes_comp)):
                    for j in range(i + 1, len(nomes_comp)):
                        na = nomes_comp[i]
                        nb = nomes_comp[j]
                        common_pair = set(all_holdings.get(na, {}).keys()) & set(all_holdings.get(nb, {}).keys())
                        total_a = len(all_holdings.get(na, {}))
                        total_b = len(all_holdings.get(nb, {}))
                        overlap_pct = _calcular_sobreposicao_ativos(
                            all_holdings.get(na, {}), all_holdings.get(nb, {})
                        )
                        pair_data.append({
                            "Fundo A": labels[i],
                            "Fundo B": labels[j],
                            "Ativos A": total_a,
                            "Ativos B": total_b,
                            "Em Comum": len(common_pair),
                            "Sobreposicao": f"{overlap_pct:.1f}%",
                        })

                if pair_data:
                    st.dataframe(pd.DataFrame(pair_data), width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
