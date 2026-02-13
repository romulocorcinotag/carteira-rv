import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import base64
from collections import Counter

from data_loader import (
    carregar_todos_dados, carregar_fundos_rv,
    carregar_cotas_fundos, carregar_universo_stats, BENCHMARK_CNPJS,
)

# ──────────────────────────────────────────────────────────────────────────────
# Paleta TAG Investimentos (conforme Guia de Marca 2021)
# ──────────────────────────────────────────────────────────────────────────────
TAG_VERMELHO = "#630D24"
TAG_OFFWHITE = "#E6E4DB"
TAG_LARANJA = "#FF8853"
TAG_BRANCO = "#FFFFFF"
TAG_CINZA_ESCURO = "#2C1A1A"
TAG_CINZA_MEDIO = "#6A6864"
TAG_AZUL_ESCURO = "#002A6E"
# Paleta de apoio para gráficos e tabelas (9 cores do guia de marca)
TAG_CHART_COLORS = [
    "#630D24",  # Vermelho vinho (principal)
    "#FF8853",  # Laranja
    "#002A6E",  # Azul escuro
    "#5C85F7",  # Azul
    "#58C6F5",  # Azul claro
    "#A485F2",  # Lilás
    "#6BDE97",  # Verde
    "#FFBB00",  # Amarelo
    "#ED5A6E",  # Rosa
    "#477C88",  # Teal
    "#6A6864",  # Cinza
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
# CSS (alinhado ao Guia de Marca TAG Investimentos)
# ──────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
        /* ── Base & Tipografia ── */
        .stApp {{
            font-family: 'Tahoma', 'Inter', 'Segoe UI', sans-serif;
            background-color: {TAG_OFFWHITE} !important;
        }}
        .stMainBlockContainer {{
            max-width: 1280px;
            padding-top: 1rem !important;
        }}
        .stMarkdown p, .stMarkdown li {{
            font-size: 0.95rem !important;
            line-height: 1.65 !important;
            color: {TAG_CINZA_ESCURO} !important;
        }}
        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0; background: transparent;
            border-bottom: 2px solid {TAG_VERMELHO}18;
        }}
        .stTabs [data-baseweb="tab"] {{
            font-size: 13px !important; font-weight: 500 !important;
            padding: 12px 24px !important; color: {TAG_CINZA_MEDIO} !important;
            text-transform: uppercase !important; letter-spacing: 0.5px !important;
            border-bottom: 3px solid transparent !important;
            transition: all 0.2s ease !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            color: {TAG_VERMELHO} !important;
        }}
        .stTabs [aria-selected="true"] {{
            font-weight: 700 !important; color: {TAG_VERMELHO} !important;
            border-bottom: 3px solid {TAG_VERMELHO} !important;
        }}
        /* ── DataFrames & Tabelas ── */
        .stDataFrame th {{
            font-size: 11px !important; font-weight: 600 !important;
            padding: 10px 14px !important; text-transform: uppercase !important;
            letter-spacing: 0.3px !important;
            background: {TAG_VERMELHO} !important; color: {TAG_BRANCO} !important;
        }}
        .stDataFrame td {{
            padding: 8px 14px !important; font-size: 13px !important;
            color: {TAG_CINZA_ESCURO} !important;
        }}
        .stMarkdown table {{
            width: 100% !important; border-collapse: collapse !important;
            margin: 12px 0 !important; border-radius: 6px !important;
            overflow: hidden !important;
        }}
        .stMarkdown table th {{
            background: {TAG_VERMELHO} !important; color: {TAG_BRANCO} !important;
            padding: 11px 16px !important; text-align: left !important;
            font-weight: 600 !important; font-size: 11px !important;
            text-transform: uppercase !important; letter-spacing: 0.4px !important;
        }}
        .stMarkdown table td {{
            padding: 10px 16px !important; border-bottom: 1px solid {TAG_OFFWHITE} !important;
            font-size: 13px !important; color: {TAG_CINZA_ESCURO} !important;
        }}
        .stMarkdown table tr:nth-child(even) td {{
            background: #f8f7f3 !important;
        }}
        .stMarkdown table tr:hover td {{
            background: {TAG_VERMELHO}08 !important;
        }}
        /* ── Inputs & Selectboxes ── */
        .stSelectbox > div > div,
        .stMultiSelect > div > div,
        .stDateInput > div > div {{
            border-color: {TAG_VERMELHO}30 !important;
            border-radius: 6px !important;
        }}
        .stSelectbox > div > div:focus-within,
        .stMultiSelect > div > div:focus-within {{
            border-color: {TAG_VERMELHO} !important;
            box-shadow: 0 0 0 1px {TAG_VERMELHO}40 !important;
        }}
        /* ── Multiselect pills ── */
        span[data-baseweb="tag"] {{
            background: {TAG_VERMELHO} !important; color: {TAG_BRANCO} !important;
            border-radius: 4px !important; font-size: 12px !important;
        }}
        /* ── Header ── */
        .tag-header {{
            display: flex; align-items: center; gap: 20px;
            padding: 16px 0 12px 0;
        }}
        .tag-logo-box {{
            background: {TAG_VERMELHO}; border-radius: 10px;
            padding: 12px 18px; display: flex; align-items: center;
            justify-content: center; min-height: 52px;
        }}
        .tag-logo-box img {{ height: 52px; filter: brightness(0) invert(1); }}
        .tag-header-text h1 {{
            margin: 0; font-size: 2.1rem; font-weight: 700;
            color: {TAG_VERMELHO}; letter-spacing: -0.3px;
        }}
        .tag-header-text p {{
            margin: 2px 0 0 0; font-size: 0.9rem; color: {TAG_CINZA_MEDIO};
            letter-spacing: 0.2px;
        }}
        /* ── Grafismo TAG (linha diagonal ascendente) ── */
        .tag-divider {{
            height: 3px; border: none;
            background: linear-gradient(135deg, {TAG_VERMELHO} 0%, {TAG_LARANJA} 40%, transparent 100%);
            margin: 12px 0 20px 0;
        }}
        .tag-section-divider {{
            height: 1px; border: none;
            background: linear-gradient(90deg, {TAG_VERMELHO}20, transparent);
            margin: 28px 0 20px 0;
        }}
        /* ── Cards de metricas ── */
        .tag-metric-card {{
            background: {TAG_BRANCO}; border-radius: 8px;
            padding: 18px 14px; text-align: center;
            border-top: 3px solid {TAG_VERMELHO};
            box-shadow: 0 1px 8px rgba(0,0,0,0.05);
            transition: box-shadow 0.2s ease;
        }}
        .tag-metric-card:hover {{
            box-shadow: 0 3px 16px rgba(99,13,36,0.1);
        }}
        .tag-metric-card .value {{
            font-size: 1.65rem; font-weight: 700;
            color: {TAG_VERMELHO}; line-height: 1.15;
        }}
        .tag-metric-card .label {{
            font-size: 0.78rem; color: {TAG_CINZA_MEDIO};
            margin-top: 6px; font-weight: 500;
            text-transform: uppercase; letter-spacing: 0.3px;
        }}
        /* ── Section titles ── */
        .tag-section-title {{
            font-size: 1.05rem; font-weight: 700; color: {TAG_VERMELHO};
            margin: 28px 0 10px 0; padding-bottom: 8px;
            border-bottom: 2px solid {TAG_VERMELHO}15;
            text-transform: uppercase; letter-spacing: 0.4px;
        }}
        /* ── Captions e info ── */
        .stCaption, .stAlert {{
            font-size: 0.82rem !important;
        }}
        /* ── Esconde sidebar ── */
        div[data-testid="stSidebar"] {{ display: none !important; }}
        /* ── Expander ── */
        details summary {{
            font-weight: 600 !important; color: {TAG_VERMELHO} !important;
            font-size: 0.9rem !important;
        }}
        /* ── Scrollbar sutil ── */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: {TAG_VERMELHO}30; border-radius: 3px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: {TAG_VERMELHO}60; }}
    </style>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────
def render_header():
    from datetime import datetime
    logo_b64 = get_logo_base64()
    logo_html = f'<div class="tag-logo-box"><img src="data:image/png;base64,{logo_b64}"></div>' if logo_b64 else ""

    # Data da última atualização dos dados
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    cotas_path = os.path.join(data_dir, "cotas_consolidado.parquet")
    if os.path.exists(cotas_path):
        mod_time = datetime.fromtimestamp(os.path.getmtime(cotas_path))
        data_atualizacao = mod_time.strftime("%d/%m/%Y %H:%M")
    else:
        data_atualizacao = "—"

    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between;">
        <div class="tag-header">
            {logo_html}
            <div class="tag-header-text">
                <h1>Carteira RV</h1>
                <p>Evolucao de Carteiras dos Fundos de Renda Variavel</p>
            </div>
        </div>
        <div style="text-align: right; padding-right: 4px;">
            <div style="font-size: 0.7rem; color: {TAG_CINZA_MEDIO}; text-transform: uppercase;
                        letter-spacing: 0.5px; font-weight: 600;">Atualizado em</div>
            <div style="font-size: 0.85rem; color: {TAG_VERMELHO}; font-weight: 700;
                        margin-top: 2px;">{data_atualizacao}</div>
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
        <div class="label">{label}</div>
        <div class="value">{value}</div>
    </div>
    """


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _hex_to_rgba(hex_color, alpha=0.8):
    h = hex_color.lstrip("#")
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _chart_layout(fig, title, height=480, y_title="% do PL", y_suffix="%",
                  legend_h=True, margin_b=40):
    """Aplica layout padrão TAG a um gráfico Plotly."""
    legend = dict(
        orientation="h", yanchor="bottom", y=1.02,
        font=dict(size=11, color=TAG_CINZA_MEDIO, family="Tahoma, sans-serif"),
        bgcolor="rgba(0,0,0,0)",
    ) if legend_h else dict(
        font=dict(size=11, color=TAG_CINZA_MEDIO, family="Tahoma, sans-serif")
    )

    layout_kwargs = dict(
        height=height, template="plotly_white",
        xaxis=dict(
            tickfont=dict(size=10, color=TAG_CINZA_MEDIO),
            gridcolor="#e8e6e0", gridwidth=1,
        ),
        legend=legend,
        plot_bgcolor=TAG_BRANCO,
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=50, r=16, t=50 if title else 30, b=margin_b),
        font=dict(family="Tahoma, sans-serif", color=TAG_CINZA_ESCURO),
        hoverlabel=dict(
            bgcolor=TAG_BRANCO, font_size=12,
            font_color=TAG_CINZA_ESCURO,
            bordercolor=TAG_VERMELHO + "40",
        ),
        hovermode="x unified",
    )
    if title:
        layout_kwargs["title"] = dict(text=title, font=dict(size=14, color=TAG_VERMELHO, family="Tahoma, sans-serif"))
    if y_title:
        layout_kwargs["yaxis"] = dict(
            title=dict(text=y_title, font=dict(size=11, color=TAG_CINZA_MEDIO)),
            ticksuffix=y_suffix,
            tickfont=dict(size=10, color=TAG_CINZA_MEDIO),
            gridcolor="#e8e6e0", gridwidth=1,
            zeroline=True, zerolinecolor="#d0cec6", zerolinewidth=1,
        )
    fig.update_layout(**layout_kwargs)
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
    <div style="border-radius: 8px; overflow: hidden; box-shadow: 0 1px 10px rgba(0,0,0,0.06); border: 1px solid {TAG_OFFWHITE}; margin: 8px 0 16px 0;">
        <table style="width: 100%; border-collapse: collapse; font-family: 'Tahoma', 'Inter', sans-serif;">
            <thead>
                <tr style="background: {TAG_VERMELHO};">
                    <th style="padding: 10px 14px; color: white; font-size: 11px; font-weight: 600; text-align: center; width: 36px; text-transform: uppercase; letter-spacing: 0.3px;">#</th>
                    <th style="padding: 10px 14px; color: white; font-size: 11px; font-weight: 600; text-align: left; text-transform: uppercase; letter-spacing: 0.3px;">Ativo</th>
                    <th style="padding: 10px 14px; color: white; font-size: 11px; font-weight: 600; text-align: left; text-transform: uppercase; letter-spacing: 0.3px;">Setor</th>
                    <th style="padding: 10px 14px; color: white; font-size: 11px; font-weight: 600; text-align: right; text-transform: uppercase; letter-spacing: 0.3px;">Valor</th>
                    <th style="padding: 10px 14px; color: white; font-size: 11px; font-weight: 600; text-align: left; width: 200px; text-transform: uppercase; letter-spacing: 0.3px;">% PL</th>
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
    tab_ativo, tab_setor, tab_pl, tab_comparativo, tab_perf = st.tabs([
        "Por Ativo", "Por Setor", "Evolucao PL", "Comparativo", "Performance"
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


    # ══════════════════════════════════════════════════════════════════════
    # TAB 5: PERFORMANCE
    # ══════════════════════════════════════════════════════════════════════
    with tab_perf:
        bench_cnpj_to_name = {v: k for k, v in BENCHMARK_CNPJS.items()}
        ibov_cnpj = list(BENCHMARK_CNPJS.values())[0]  # IBOVESPA proxy
        all_cnpjs_for_cotas = tuple(set(cnpjs_sel) | set(BENCHMARK_CNPJS.values()))

        df_cotas = carregar_cotas_fundos(all_cnpjs_for_cotas, meses=120)

        if df_cotas.empty:
            st.warning("Sem dados de cotas disponíveis. Verifique a conexão com a CVM.")
        else:
            # Filtros — usar máximo histórico como padrão
            col_dt1, col_dt2, col_janela = st.columns([2, 2, 2])
            min_data = df_cotas["data"].min().date()
            max_data = df_cotas["data"].max().date()

            with col_dt1:
                dt_inicio = st.date_input(
                    "Data inicio", value=min_data,
                    min_value=min_data, max_value=max_data, format="DD/MM/YYYY",
                    key="perf_dt_ini"
                )
            with col_dt2:
                dt_fim = st.date_input(
                    "Data fim", value=max_data,
                    min_value=min_data, max_value=max_data, format="DD/MM/YYYY",
                    key="perf_dt_fim"
                )
            with col_janela:
                janela_opcoes = {"1 ano": 252, "2 anos": 504, "3 anos": 756, "5 anos": 1260, "7 anos": 1764}
                janela_label = st.selectbox("Janela movel", list(janela_opcoes.keys()), index=0)
                janela_du = janela_opcoes[janela_label]

            mask_periodo = (df_cotas["data"].dt.date >= dt_inicio) & (df_cotas["data"].dt.date <= dt_fim)
            df_c = df_cotas[mask_periodo].copy()

            if df_c.empty:
                st.warning("Sem dados de cotas no período selecionado.")
            else:
                cnpj_to_label = {}
                for nome in fundos_sel:
                    cnpj = nome_cnpj_map[nome]
                    short = " ".join(nome.split()[:3])
                    if len(short) > 25:
                        short = short[:22] + "..."
                    cnpj_to_label[cnpj] = short
                for cnpj, name in bench_cnpj_to_name.items():
                    cnpj_to_label[cnpj] = name

                pivot_quota = df_c.pivot_table(index="data", columns="cnpj_fundo", values="vl_quota")
                pivot_quota = pivot_quota.sort_index().ffill()
                pivot_ret = pivot_quota.pct_change()

                fund_cols = [c for c in cnpjs_sel if c in pivot_quota.columns]
                bench_cols = [c for c in BENCHMARK_CNPJS.values() if c in pivot_quota.columns]
                all_cols = fund_cols + bench_cols

                bench_styles = {
                    list(BENCHMARK_CNPJS.values())[0]: dict(color=TAG_LARANJA, dash="dash"),
                    list(BENCHMARK_CNPJS.values())[1]: dict(color="#333333", dash="dash"),
                }

                CDI_ANUAL = 0.1315
                cdi_diario = (1 + CDI_ANUAL) ** (1 / 252) - 1

                if not fund_cols:
                    st.warning("Sem dados de cotas para os fundos selecionados no período.")
                else:
                    # ─── G1: Retorno Acumulado (%) ───
                    st.markdown('<div class="tag-section-title">Retorno Acumulado (%)</div>', unsafe_allow_html=True)

                    ret_acum_pct = ((1 + pivot_ret[all_cols]).cumprod() - 1) * 100
                    ret_acum_pct.iloc[0] = 0

                    fig_ret = go.Figure()
                    for i, cnpj in enumerate(fund_cols):
                        label = cnpj_to_label.get(cnpj, cnpj[:10])
                        fig_ret.add_trace(go.Scatter(
                            x=ret_acum_pct.index, y=ret_acum_pct[cnpj],
                            name=label, mode="lines",
                            line=dict(width=2.5, color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
                            hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}: %{{y:+.1f}}%<extra></extra>",
                        ))
                    for cnpj in bench_cols:
                        label = cnpj_to_label.get(cnpj, cnpj[:10])
                        style = bench_styles.get(cnpj, dict(color="#999", dash="dash"))
                        fig_ret.add_trace(go.Scatter(
                            x=ret_acum_pct.index, y=ret_acum_pct[cnpj],
                            name=label, mode="lines",
                            line=dict(width=2, **style),
                            hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}: %{{y:+.1f}}%<extra></extra>",
                        ))
                    fig_ret.add_hline(y=0, line_dash="dot", line_color="#ccc", line_width=1)
                    _chart_layout(fig_ret, "", height=480, y_title="Retorno Acumulado (%)")
                    st.plotly_chart(fig_ret, use_container_width=True)

                    # ─── G2: Drawdown ───
                    st.markdown('<div class="tag-section-title">Drawdown</div>', unsafe_allow_html=True)

                    cum_quota = (1 + pivot_ret[all_cols]).cumprod()
                    running_max = cum_quota.cummax()
                    drawdown = (cum_quota / running_max - 1) * 100

                    fig_dd = go.Figure()
                    for i, cnpj in enumerate(fund_cols):
                        label = cnpj_to_label.get(cnpj, cnpj[:10])
                        fig_dd.add_trace(go.Scatter(
                            x=drawdown.index, y=drawdown[cnpj],
                            name=label, mode="lines",
                            line=dict(width=1.5, color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
                            fill="tozeroy" if i == 0 else None,
                            fillcolor=_hex_to_rgba(TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)], 0.12) if i == 0 else None,
                            hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}: %{{y:.1f}}%<extra></extra>",
                        ))
                    for cnpj in bench_cols:
                        label = cnpj_to_label.get(cnpj, cnpj[:10])
                        style = bench_styles.get(cnpj, dict(color="#999", dash="dash"))
                        fig_dd.add_trace(go.Scatter(
                            x=drawdown.index, y=drawdown[cnpj],
                            name=label, mode="lines",
                            line=dict(width=1.5, **style),
                            hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}: %{{y:.1f}}%<extra></extra>",
                        ))
                    _chart_layout(fig_dd, "", height=400, y_title="Drawdown (%)")
                    st.plotly_chart(fig_dd, use_container_width=True)

                    # ─── G3: Percentil (janela móvel) ───
                    st.markdown(f'<div class="tag-section-title">Percentil — Janela {janela_label}</div>', unsafe_allow_html=True)
                    st.caption("Posicao relativa do fundo no universo de fundos RV (0%=pior, 100%=melhor) com base no retorno acumulado na janela movel.")

                    rolling_ret = pivot_ret[all_cols].rolling(janela_du).apply(
                        lambda x: (1 + x).prod() - 1, raw=False
                    )

                    df_stats = carregar_universo_stats(meses=120)

                    if not df_stats.empty and not rolling_ret.dropna(how="all").empty:
                        df_st = df_stats.set_index("data").reindex(pivot_ret.index)

                        # Calcular retorno rolling para cada percentil do universo
                        pct_cols = ["p10", "p25", "p50", "p75", "p90"]
                        univ_roll = {}
                        for pc in pct_cols:
                            if pc in df_st.columns:
                                univ_roll[pc] = df_st[pc].rolling(janela_du, min_periods=max(1, janela_du // 2)).apply(
                                    lambda x: (1 + x).prod() - 1, raw=False
                                )

                        def _percentil_interpolado(val, dt):
                            """Interpola percentil real usando p10-p90 do universo."""
                            pts = []
                            for pc_name, pc_val in [("p10", 10), ("p25", 25), ("p50", 50), ("p75", 75), ("p90", 90)]:
                                if pc_name in univ_roll and dt in univ_roll[pc_name].index:
                                    v = univ_roll[pc_name].loc[dt]
                                    if pd.notna(v):
                                        pts.append((v, pc_val))
                            if len(pts) < 2:
                                return 50.0
                            pts.sort(key=lambda x: x[0])
                            # Interpolação linear entre os pontos conhecidos
                            if val <= pts[0][0]:
                                return max(0, pts[0][1] * val / pts[0][0]) if pts[0][0] != 0 else 5.0
                            if val >= pts[-1][0]:
                                return min(100, pts[-1][1] + (100 - pts[-1][1]) * (val - pts[-1][0]) / (abs(pts[-1][0]) + 0.0001))
                            for k in range(len(pts) - 1):
                                v0, p0 = pts[k]
                                v1, p1 = pts[k + 1]
                                if v0 <= val <= v1:
                                    frac = (val - v0) / (v1 - v0) if v1 != v0 else 0.5
                                    return p0 + frac * (p1 - p0)
                            return 50.0

                        fig_rank = go.Figure()
                        # Quintil bands
                        quintil_colors = [
                            ("#e8f5e9", "Q1 (top)"), ("#fff9c4", "Q2"),
                            ("#fff3e0", "Q3"), ("#fce4ec", "Q4"),
                            ("#ffebee", "Q5 (bottom)")
                        ]
                        for qi, (qcolor, qlabel) in enumerate(quintil_colors):
                            y0 = 100 - qi * 20
                            y1 = y0 - 20
                            fig_rank.add_hrect(
                                y0=y1, y1=y0, fillcolor=qcolor,
                                line_width=0, layer="below",
                                annotation_text=qlabel if qi in [0, 4] else "",
                                annotation_position="right",
                            )

                        for i, cnpj in enumerate(fund_cols + bench_cols):
                            label = cnpj_to_label.get(cnpj, cnpj[:10])
                            is_bench = cnpj in bench_cols
                            fund_roll = rolling_ret[cnpj].dropna()
                            if fund_roll.empty:
                                continue
                            pctls = pd.Series(
                                [_percentil_interpolado(val, dt) if pd.notna(val) else np.nan for dt, val in fund_roll.items()],
                                index=fund_roll.index,
                            )
                            pctls = pctls.dropna()
                            if pctls.empty:
                                continue
                            style = bench_styles.get(cnpj, {}) if is_bench else {}
                            fig_rank.add_trace(go.Scatter(
                                x=pctls.index, y=pctls.values,
                                name=label, mode="lines",
                                line=dict(
                                    width=2 if is_bench else 2.5,
                                    color=style.get("color", TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
                                    dash=style.get("dash", "solid"),
                                ),
                                hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>Percentil: %{{y:.0f}}%<extra></extra>",
                            ))

                        fig_rank.add_hline(y=50, line_dash="dot", line_color="#999", line_width=1)
                        _chart_layout(fig_rank, "", height=450, y_title="Percentil", y_suffix="%")
                        fig_rank.update_yaxes(range=[0, 100])
                        st.plotly_chart(fig_rank, use_container_width=True)
                    else:
                        st.info("Dados do universo insuficientes para calcular o percentil.")

                    # ─── G4: Capture Ratio (Upside vs Downside) ───
                    st.markdown('<div class="tag-section-title">Capture Ratio — Upside vs Downside</div>', unsafe_allow_html=True)
                    st.caption("Acima da diagonal = gestor ganha mais nas altas do que perde nas quedas (assimetria positiva). Quanto mais acima-esquerda, melhor.")

                    if ibov_cnpj in pivot_ret.columns:
                        bench_ret = pivot_ret[ibov_cnpj].dropna()
                        # Calcular com retornos mensais para robustez
                        monthly_ret = pivot_ret[all_cols].resample("ME").apply(lambda x: (1 + x).prod() - 1)
                        bench_monthly = monthly_ret[ibov_cnpj].dropna() if ibov_cnpj in monthly_ret.columns else pd.Series(dtype=float)

                        capture_data = []
                        for cnpj in all_cols:
                            if cnpj not in monthly_ret.columns or cnpj == ibov_cnpj:
                                continue
                            fund_m = monthly_ret[cnpj]
                            common = fund_m.dropna().index.intersection(bench_monthly.dropna().index)
                            if len(common) < 12:
                                continue
                            bm = bench_monthly.loc[common]
                            fm = fund_m.loc[common]
                            up_mask = bm > 0
                            down_mask = bm < 0
                            up_cap = (fm[up_mask].mean() / bm[up_mask].mean() * 100) if up_mask.sum() > 3 else np.nan
                            down_cap = (fm[down_mask].mean() / bm[down_mask].mean() * 100) if down_mask.sum() > 3 else np.nan
                            if pd.notna(up_cap) and pd.notna(down_cap):
                                capture_data.append({
                                    "cnpj": cnpj,
                                    "label": cnpj_to_label.get(cnpj, cnpj[:10]),
                                    "up": up_cap, "down": down_cap,
                                    "is_fund": cnpj in fund_cols,
                                    "is_bench": cnpj in bench_cols,
                                })

                        if capture_data:
                            df_cap = pd.DataFrame(capture_data)
                            fig_cap = go.Figure()
                            # Diagonal line (up = down)
                            cap_range = [min(df_cap["down"].min(), df_cap["up"].min()) - 10,
                                         max(df_cap["down"].max(), df_cap["up"].max()) + 10]
                            fig_cap.add_trace(go.Scatter(
                                x=cap_range, y=cap_range, mode="lines",
                                line=dict(color="#ddd", dash="dash", width=1),
                                showlegend=False, hoverinfo="skip",
                            ))

                            for idx_row, row in df_cap.iterrows():
                                if row["is_fund"]:
                                    color = TAG_CHART_COLORS[list(df_cap[df_cap["is_fund"]].index).index(idx_row) % len(TAG_CHART_COLORS)]
                                    size = 16
                                elif row["is_bench"]:
                                    color = bench_styles.get(row["cnpj"], {}).get("color", "#999")
                                    size = 14
                                else:
                                    continue
                                fig_cap.add_trace(go.Scatter(
                                    x=[row["down"]], y=[row["up"]],
                                    mode="markers+text", name=row["label"],
                                    marker=dict(symbol="star", size=size, color=color,
                                                line=dict(width=1, color="white")),
                                    text=[row["label"]], textposition="top center",
                                    textfont=dict(size=9),
                                    hovertemplate=f"<b>{row['label']}</b><br>Upside: {row['up']:.0f}%<br>Downside: {row['down']:.0f}%<extra></extra>",
                                ))

                            fig_cap.update_layout(
                                height=480, template="plotly_white",
                                xaxis=dict(title=dict(text="Downside Capture (%)", font=dict(size=11, color=TAG_CINZA_MEDIO)),
                                           ticksuffix="%", tickfont=dict(size=10, color=TAG_CINZA_MEDIO), gridcolor="#e8e6e0"),
                                yaxis=dict(title=dict(text="Upside Capture (%)", font=dict(size=11, color=TAG_CINZA_MEDIO)),
                                           ticksuffix="%", tickfont=dict(size=10, color=TAG_CINZA_MEDIO), gridcolor="#e8e6e0"),
                                font=dict(family="Tahoma, sans-serif", color=TAG_CINZA_ESCURO),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11, color=TAG_CINZA_MEDIO)),
                                margin=dict(l=50, r=16, t=40, b=50),
                                plot_bgcolor=TAG_BRANCO, paper_bgcolor="rgba(0,0,0,0)",
                                hoverlabel=dict(bgcolor=TAG_BRANCO, font_size=12, bordercolor=TAG_VERMELHO + "40"),
                                hovermode="closest",
                            )
                            st.plotly_chart(fig_cap, use_container_width=True)

                    # ─── G5: Rolling Alpha vs Benchmark ───
                    st.markdown(f'<div class="tag-section-title">Alpha Rolling vs IBOVESPA — Janela {janela_label}</div>', unsafe_allow_html=True)
                    st.caption("Alpha de Jensen (retorno excedente após ajustar pelo beta de mercado). Positivo = gestor gerando valor. Persistência indica habilidade real.")

                    if ibov_cnpj in pivot_ret.columns:
                        fig_alpha = go.Figure()
                        bench_r = pivot_ret[ibov_cnpj]
                        for i, cnpj in enumerate(fund_cols):
                            if cnpj not in pivot_ret.columns:
                                continue
                            label = cnpj_to_label.get(cnpj, cnpj[:10])
                            fund_r = pivot_ret[cnpj]
                            # Rolling alpha: regressão rolling
                            exc_fund = fund_r - cdi_diario
                            exc_bench = bench_r - cdi_diario
                            roll_cov = exc_fund.rolling(janela_du).cov(exc_bench)
                            roll_var = exc_bench.rolling(janela_du).var()
                            roll_beta = roll_cov / roll_var
                            roll_alpha = (exc_fund.rolling(janela_du).mean() - roll_beta * exc_bench.rolling(janela_du).mean()) * 252
                            roll_alpha = roll_alpha.dropna()
                            fig_alpha.add_trace(go.Scatter(
                                x=roll_alpha.index, y=roll_alpha.values * 100,
                                name=label, mode="lines",
                                line=dict(width=2, color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
                                hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>Alpha: %{{y:+.1f}}% a.a.<extra></extra>",
                            ))
                        for cnpj in bench_cols:
                            if cnpj == ibov_cnpj or cnpj not in pivot_ret.columns:
                                continue
                            label = cnpj_to_label.get(cnpj, cnpj[:10])
                            style = bench_styles.get(cnpj, dict(color="#999", dash="dash"))
                            fund_r = pivot_ret[cnpj]
                            exc_fund = fund_r - cdi_diario
                            exc_bench = bench_r - cdi_diario
                            roll_cov = exc_fund.rolling(janela_du).cov(exc_bench)
                            roll_var = exc_bench.rolling(janela_du).var()
                            roll_beta = roll_cov / roll_var
                            roll_alpha = (exc_fund.rolling(janela_du).mean() - roll_beta * exc_bench.rolling(janela_du).mean()) * 252
                            roll_alpha = roll_alpha.dropna()
                            fig_alpha.add_trace(go.Scatter(
                                x=roll_alpha.index, y=roll_alpha.values * 100,
                                name=label, mode="lines",
                                line=dict(width=1.5, **style),
                                hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>Alpha: %{{y:+.1f}}% a.a.<extra></extra>",
                            ))
                        fig_alpha.add_hline(y=0, line_dash="dot", line_color="#ccc", line_width=1)
                        _chart_layout(fig_alpha, "", height=400, y_title="Alpha (% a.a.)")
                        st.plotly_chart(fig_alpha, use_container_width=True)

                    # ─── G6: Rolling Tracking Error ───
                    st.markdown(f'<div class="tag-section-title">Tracking Error Rolling — Janela {janela_label}</div>', unsafe_allow_html=True)
                    st.caption("Desvio dos retornos em relação ao IBOVESPA. TE < 2% = closet indexer. TE 2-8% = gestão ativa moderada. TE > 8% = alta convicção.")

                    if ibov_cnpj in pivot_ret.columns:
                        fig_te = go.Figure()
                        # Faixas de referência
                        fig_te.add_hrect(y0=0, y1=2, fillcolor="rgba(200,200,200,0.15)", line_width=0, layer="below")
                        fig_te.add_hrect(y0=2, y1=8, fillcolor="rgba(200,230,255,0.10)", line_width=0, layer="below")
                        fig_te.add_hline(y=2, line_dash="dot", line_color="#bbb", line_width=1, annotation_text="Closet Indexer", annotation_position="top left")
                        fig_te.add_hline(y=8, line_dash="dot", line_color="#bbb", line_width=1, annotation_text="Alta Convicção", annotation_position="top left")

                        bench_r = pivot_ret[ibov_cnpj]
                        for i, cnpj in enumerate(fund_cols):
                            if cnpj not in pivot_ret.columns:
                                continue
                            label = cnpj_to_label.get(cnpj, cnpj[:10])
                            active_ret = pivot_ret[cnpj] - bench_r
                            roll_te = active_ret.rolling(janela_du).std() * np.sqrt(252) * 100
                            roll_te = roll_te.dropna()
                            fig_te.add_trace(go.Scatter(
                                x=roll_te.index, y=roll_te.values,
                                name=label, mode="lines",
                                line=dict(width=2, color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
                                hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>TE: %{{y:.1f}}%<extra></extra>",
                            ))
                        for cnpj in bench_cols:
                            if cnpj == ibov_cnpj or cnpj not in pivot_ret.columns:
                                continue
                            label = cnpj_to_label.get(cnpj, cnpj[:10])
                            style = bench_styles.get(cnpj, dict(color="#999", dash="dash"))
                            active_ret = pivot_ret[cnpj] - bench_r
                            roll_te = active_ret.rolling(janela_du).std() * np.sqrt(252) * 100
                            roll_te = roll_te.dropna()
                            fig_te.add_trace(go.Scatter(
                                x=roll_te.index, y=roll_te.values,
                                name=label, mode="lines",
                                line=dict(width=1.5, **style),
                                hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>TE: %{{y:.1f}}%<extra></extra>",
                            ))
                        _chart_layout(fig_te, "", height=380, y_title="Tracking Error (% a.a.)")
                        st.plotly_chart(fig_te, use_container_width=True)

                    # ─── G7: Risco × Retorno (scatter) ───
                    st.markdown(f'<div class="tag-section-title">Risco x Retorno</div>', unsafe_allow_html=True)
                    st.caption("X = Ulcer Index (risco de drawdown). Y = Retorno anualizado. Quanto mais acima e à esquerda, melhor.")

                    scatter_data = []
                    for cnpj in all_cols:
                        if cnpj not in pivot_ret.columns:
                            continue
                        ret_series = pivot_ret[cnpj].dropna()
                        if len(ret_series) < 60:
                            continue
                        ret_acum = (1 + ret_series).prod() - 1
                        n_dias = len(ret_series)
                        ret_anual = (1 + ret_acum) ** (252 / n_dias) - 1 if n_dias > 0 else 0
                        cum = (1 + ret_series).cumprod()
                        dd = (cum / cum.cummax() - 1) * 100
                        ulcer = np.sqrt((dd ** 2).mean())
                        scatter_data.append({
                            "cnpj": cnpj, "label": cnpj_to_label.get(cnpj, cnpj[:10]),
                            "ret_anual": ret_anual * 100, "ulcer": ulcer,
                            "is_fund": cnpj in fund_cols, "is_bench": cnpj in bench_cols,
                        })

                    if scatter_data:
                        df_scatter = pd.DataFrame(scatter_data)
                        fig_scatter = go.Figure()
                        for idx_row, row in df_scatter.iterrows():
                            if row["is_fund"]:
                                color = TAG_CHART_COLORS[list(df_scatter[df_scatter["is_fund"]].index).index(idx_row) % len(TAG_CHART_COLORS)]
                                size = 18
                            elif row["is_bench"]:
                                color = bench_styles.get(row["cnpj"], {}).get("color", "#999")
                                size = 16
                            else:
                                continue
                            fig_scatter.add_trace(go.Scatter(
                                x=[row["ulcer"]], y=[row["ret_anual"]],
                                mode="markers+text", name=row["label"],
                                marker=dict(symbol="star", size=size, color=color,
                                            line=dict(width=1, color="white")),
                                text=[row["label"]], textposition="top center",
                                textfont=dict(size=10),
                                hovertemplate=f"<b>{row['label']}</b><br>Retorno: {row['ret_anual']:.1f}% a.a.<br>Ulcer Index: {row['ulcer']:.1f}<extra></extra>",
                            ))
                        fig_scatter.add_hline(y=0, line_dash="dot", line_color="#ccc", line_width=1)
                        fig_scatter.update_layout(
                            height=480, template="plotly_white",
                            xaxis=dict(title=dict(text="Ulcer Index (risco)", font=dict(size=11, color=TAG_CINZA_MEDIO)),
                                       zeroline=True, tickfont=dict(size=10, color=TAG_CINZA_MEDIO), gridcolor="#e8e6e0"),
                            yaxis=dict(title=dict(text="Retorno Anualizado (%)", font=dict(size=11, color=TAG_CINZA_MEDIO)),
                                       ticksuffix="%", tickfont=dict(size=10, color=TAG_CINZA_MEDIO), gridcolor="#e8e6e0"),
                            font=dict(family="Tahoma, sans-serif", color=TAG_CINZA_ESCURO),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11, color=TAG_CINZA_MEDIO)),
                            margin=dict(l=50, r=16, t=40, b=50),
                            plot_bgcolor=TAG_BRANCO, paper_bgcolor="rgba(0,0,0,0)",
                            hoverlabel=dict(bgcolor=TAG_BRANCO, font_size=12, bordercolor=TAG_VERMELHO + "40"),
                            hovermode="closest",
                        )
                        st.plotly_chart(fig_scatter, use_container_width=True)

                    # ─── G8: Tabela de Métricas Completa ───
                    st.markdown('<div class="tag-section-title">Metricas de Performance e Gestao</div>', unsafe_allow_html=True)

                    metrics_rows = []
                    for cnpj in all_cols:
                        if cnpj not in pivot_ret.columns:
                            continue
                        ret = pivot_ret[cnpj].dropna()
                        if len(ret) < 20:
                            continue

                        ret_acum = (1 + ret).prod() - 1
                        n_dias = len(ret)
                        ret_anual = (1 + ret_acum) ** (252 / n_dias) - 1 if n_dias > 0 else 0
                        vol_anual = ret.std() * np.sqrt(252)
                        sharpe = (ret_anual - CDI_ANUAL) / vol_anual if vol_anual > 0 else 0

                        cum = (1 + ret).cumprod()
                        dd = (cum / cum.cummax() - 1) * 100
                        max_dd = dd.min()
                        ulcer = np.sqrt((dd ** 2).mean())
                        calmar = ret_anual / abs(max_dd / 100) if max_dd != 0 else 0
                        pain = dd[dd < 0].abs().mean() if (dd < 0).any() else 0

                        # Métricas vs benchmark (IBOV)
                        ir, hit_rate, up_cap, down_cap = np.nan, np.nan, np.nan, np.nan
                        if ibov_cnpj in pivot_ret.columns and cnpj != ibov_cnpj:
                            bench_r = pivot_ret[ibov_cnpj].reindex(ret.index).dropna()
                            common_idx = ret.index.intersection(bench_r.index)
                            if len(common_idx) > 20:
                                fr = ret.loc[common_idx]
                                br = bench_r.loc[common_idx]
                                active = fr - br
                                te = active.std() * np.sqrt(252)
                                ir = active.mean() * 252 / te if te > 0 else 0
                                # Monthly hit rate
                                monthly_f = fr.resample("ME").apply(lambda x: (1 + x).prod() - 1)
                                monthly_b = br.resample("ME").apply(lambda x: (1 + x).prod() - 1)
                                common_m = monthly_f.dropna().index.intersection(monthly_b.dropna().index)
                                if len(common_m) > 6:
                                    hit_rate = (monthly_f.loc[common_m] > monthly_b.loc[common_m]).sum() / len(common_m) * 100
                                    up_m = monthly_b.loc[common_m] > 0
                                    down_m = monthly_b.loc[common_m] < 0
                                    if up_m.sum() > 2:
                                        up_cap = monthly_f.loc[common_m][up_m].mean() / monthly_b.loc[common_m][up_m].mean() * 100
                                    if down_m.sum() > 2:
                                        down_cap = monthly_f.loc[common_m][down_m].mean() / monthly_b.loc[common_m][down_m].mean() * 100

                        label = cnpj_to_label.get(cnpj, cnpj[:10])
                        row_data = {
                            "Fundo": label,
                            "Ret.Acum": f"{ret_acum*100:.1f}%",
                            "Ret.Anual": f"{ret_anual*100:.1f}%",
                            "Vol.Anual": f"{vol_anual*100:.1f}%",
                            "Sharpe": f"{sharpe:.2f}",
                            "Max DD": f"{max_dd:.1f}%",
                            "Calmar": f"{calmar:.2f}",
                            "Ulcer": f"{ulcer:.1f}",
                        }
                        if pd.notna(ir):
                            row_data["IR"] = f"{ir:.2f}"
                            row_data["Hit%"] = f"{hit_rate:.0f}%" if pd.notna(hit_rate) else "—"
                            row_data["Up Cap"] = f"{up_cap:.0f}%" if pd.notna(up_cap) else "—"
                            row_data["Dn Cap"] = f"{down_cap:.0f}%" if pd.notna(down_cap) else "—"
                        else:
                            row_data.update({"IR": "—", "Hit%": "—", "Up Cap": "—", "Dn Cap": "—"})
                        metrics_rows.append(row_data)

                    if metrics_rows:
                        df_metrics = pd.DataFrame(metrics_rows)
                        st.dataframe(df_metrics, use_container_width=True, hide_index=True)
                    else:
                        st.info("Dados insuficientes para calcular métricas.")

                    # ─── G9: Rolling Sharpe ───
                    st.markdown(f'<div class="tag-section-title">Sharpe Rolling — Janela {janela_label}</div>', unsafe_allow_html=True)
                    st.caption(f"Sharpe ratio em janelas moveis de {janela_label}. CDI: {CDI_ANUAL*100:.1f}% a.a.")

                    cdi_janela = (1 + CDI_ANUAL) ** (janela_du / 252) - 1
                    fig_sharpe = go.Figure()
                    for i, cnpj in enumerate(fund_cols):
                        if cnpj not in pivot_ret.columns:
                            continue
                        label = cnpj_to_label.get(cnpj, cnpj[:10])
                        ret = pivot_ret[cnpj]
                        roll_ret = ret.rolling(janela_du).apply(lambda x: (1 + x).prod() - 1, raw=False)
                        roll_vol = ret.rolling(janela_du).std() * np.sqrt(janela_du)
                        roll_sharpe = (roll_ret - cdi_janela) / roll_vol
                        roll_sharpe = roll_sharpe.dropna()
                        fig_sharpe.add_trace(go.Scatter(
                            x=roll_sharpe.index, y=roll_sharpe.values,
                            name=label, mode="lines",
                            line=dict(width=2, color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
                            hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>Sharpe: %{{y:.2f}}<extra></extra>",
                        ))
                    for cnpj in bench_cols:
                        if cnpj not in pivot_ret.columns:
                            continue
                        label = cnpj_to_label.get(cnpj, cnpj[:10])
                        style = bench_styles.get(cnpj, dict(color="#999", dash="dash"))
                        ret = pivot_ret[cnpj]
                        roll_ret = ret.rolling(janela_du).apply(lambda x: (1 + x).prod() - 1, raw=False)
                        roll_vol = ret.rolling(janela_du).std() * np.sqrt(janela_du)
                        roll_sharpe = (roll_ret - cdi_janela) / roll_vol
                        roll_sharpe = roll_sharpe.dropna()
                        fig_sharpe.add_trace(go.Scatter(
                            x=roll_sharpe.index, y=roll_sharpe.values,
                            name=label, mode="lines",
                            line=dict(width=1.5, **style),
                            hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>Sharpe: %{{y:.2f}}<extra></extra>",
                        ))
                    fig_sharpe.add_hline(y=0, line_dash="dot", line_color="#ccc", line_width=1)
                    _chart_layout(fig_sharpe, "", height=400, y_title="Sharpe Ratio", y_suffix="")
                    st.plotly_chart(fig_sharpe, use_container_width=True)


if __name__ == "__main__":
    main()
