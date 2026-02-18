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
# Paleta TAG Investimentos — Dark Theme (igual Simulador de Realocação)
# ──────────────────────────────────────────────────────────────────────────────
TAG_VERMELHO = "#630D24"
TAG_VERMELHO_LIGHT = "#8B1A3A"
TAG_VERMELHO_DARK = "#3D0816"
TAG_OFFWHITE = "#E6E4DB"
TAG_LARANJA = "#FF8853"
TAG_LARANJA_DARK = "#E06B35"
TAG_BRANCO = "#FFFFFF"
TAG_CINZA_ESCURO = "#2C1A1A"
TAG_CINZA_MEDIO = "#6A6864"
TAG_AZUL_ESCURO = "#002A6E"
# Dark theme tokens
TAG_BG_DARK = "#1A0A10"
TAG_BG_CARD = "#2A1520"
TAG_BG_CARD_ALT = "#321A28"
CARD_BG = TAG_BG_CARD
TEXT_COLOR = TAG_OFFWHITE
TEXT_MUTED = "#9A9590"
BORDER_COLOR = f"{TAG_VERMELHO}30"
CHART_GRID = "rgba(230,228,219,0.08)"
# Paleta de apoio para gráficos (vibrantes sobre fundo escuro)
TAG_CHART_COLORS = [
    "#FF8853",  # Laranja
    "#5C85F7",  # Azul
    "#6BDE97",  # Verde
    "#FFBB00",  # Amarelo
    "#ED5A6E",  # Rosa
    "#58C6F5",  # Azul claro
    "#A485F2",  # Lilás
    "#477C88",  # Teal
    "#002A6E",  # Azul escuro
    "#6A6864",  # Cinza
]

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Carteira RV - TAG Investimentos",
    page_icon="\U0001F4C8",
    layout="wide",
    initial_sidebar_state="expanded",
)

_APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Logo grande para sidebar
LOGO_SIDEBAR_PATH = os.path.join(_APP_DIR, "assets", "logo_sidebar.png")
if not os.path.exists(LOGO_SIDEBAR_PATH):
    LOGO_SIDEBAR_PATH = os.path.join(_APP_DIR, "..", "luz_amarela", "logo_sidebar.png")

# Logo rodapé (fallback)
LOGO_PATH = os.path.join(_APP_DIR, "assets", "tag_logo_rodape.png")
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = os.path.join(_APP_DIR, "..", "luz_amarela", "tag_logo_rodape.png")


def get_logo_base64(path=None):
    p = path or LOGO_SIDEBAR_PATH
    if os.path.exists(p):
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


# ──────────────────────────────────────────────────────────────────────────────
# CSS — Dark Theme TAG Investimentos (igual Simulador de Realocação)
# ──────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
        /* ══════════════════════════════════════════════════
           TYPOGRAPHY
        ══════════════════════════════════════════════════ */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', 'Tahoma', sans-serif;
        }}
        .stMarkdown p, .stMarkdown li {{
            font-size: 1.05rem !important;
            line-height: 1.7 !important;
        }}
        .stMarkdown h4 {{ font-size: 1.35rem !important; font-weight: 700 !important; }}
        .stMarkdown h5 {{ font-size: 1.15rem !important; font-weight: 600 !important; }}
        .stCaption, [data-testid="stCaptionContainer"] {{ font-size: 0.9rem !important; }}

        /* ── Headers ── */
        h1 {{
            color: {TAG_OFFWHITE} !important;
            font-weight: 600 !important;
            letter-spacing: -0.02em;
            border-bottom: 2px solid {TAG_LARANJA}40;
            padding-bottom: 12px !important;
        }}
        h2, h3 {{ color: {TAG_OFFWHITE} !important; font-weight: 500 !important; }}

        /* ══════════════════════════════════════════════════
           BUTTONS
        ══════════════════════════════════════════════════ */
        .stButton > button {{
            padding: 0.6rem 1.5rem !important;
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            background: linear-gradient(135deg, {TAG_VERMELHO} 0%, {TAG_VERMELHO_DARK} 100%) !important;
            color: {TAG_OFFWHITE} !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(99,13,36,0.3) !important;
        }}
        .stButton > button:hover {{
            box-shadow: 0 6px 20px rgba(99,13,36,0.5) !important;
            transform: translateY(-1px);
        }}

        /* ── Selectbox / Multiselect labels ── */
        .stSelectbox label, .stMultiSelect label,
        [data-testid="stWidgetLabel"] label {{
            font-size: 1rem !important;
            font-weight: 600 !important;
            color: {TEXT_MUTED} !important;
        }}

        .stMainBlockContainer {{
            max-width: 1400px;
            padding-top: 0.5rem !important;
        }}

        /* ── Hide decoration ── */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* ══════════════════════════════════════════════════
           SIDEBAR
        ══════════════════════════════════════════════════ */
        [data-testid="stSidebar"] {{
            background: {TAG_BG_DARK} !important;
            border-right: 1px solid {TAG_VERMELHO}25;
            min-width: 260px !important;
            max-width: 280px !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            padding-top: 0 !important;
        }}
        /* Sidebar logo */
        .sidebar-logo {{
            text-align: center;
            padding: 32px 20px 8px 20px;
        }}
        .sidebar-logo img {{
            width: 160px;
            height: auto;
            margin-bottom: 6px;
        }}
        .sidebar-logo .app-name {{
            font-size: 0.85rem;
            color: {TAG_LARANJA};
            margin-top: 8px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        .sidebar-logo .bar {{
            width: 40px;
            height: 2px;
            background: {TAG_LARANJA};
            margin: 8px auto 0;
        }}
        /* Sidebar radio navigation */
        [data-testid="stSidebar"] .stRadio > div {{
            gap: 4px !important;
        }}
        [data-testid="stSidebar"] .stRadio label {{
            padding: 12px 20px !important;
            border-radius: 8px !important;
            cursor: pointer !important;
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            color: {TEXT_MUTED} !important;
            transition: all 0.2s ease !important;
            margin: 0 !important;
        }}
        [data-testid="stSidebar"] .stRadio label:hover {{
            background: {TAG_BG_CARD} !important;
            color: {TAG_OFFWHITE} !important;
        }}
        [data-testid="stSidebar"] .stRadio label[data-checked="true"],
        [data-testid="stSidebar"] .stRadio [aria-checked="true"] {{
            background: linear-gradient(135deg, {TAG_VERMELHO} 0%, {TAG_VERMELHO_DARK} 100%) !important;
            color: {TAG_OFFWHITE} !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 12px rgba(99,13,36,0.3) !important;
        }}
        /* Hide radio circles */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label > div:first-child {{
            display: none !important;
        }}

        /* ══════════════════════════════════════════════════
           TABS
        ══════════════════════════════════════════════════ */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            border-bottom: 2px solid {TAG_VERMELHO}30;
        }}
        .stTabs [data-baseweb="tab"] {{
            font-size: 16px !important;
            font-weight: 500 !important;
            padding: 10px 24px !important;
            border-radius: 8px 8px 0 0;
            color: {TEXT_MUTED} !important;
        }}
        .stTabs [aria-selected="true"] {{
            font-weight: 700 !important;
            color: {TAG_LARANJA} !important;
            background: {TAG_VERMELHO}20 !important;
            border-bottom: 3px solid {TAG_LARANJA} !important;
        }}

        /* ══════════════════════════════════════════════════
           DATAFRAMES
        ══════════════════════════════════════════════════ */
        [data-testid="stDataFrame"] {{
            border: 1px solid {TAG_VERMELHO}20;
            border-radius: 8px;
            overflow: hidden;
        }}
        .stDataFrame table {{ font-size: 15px !important; }}
        .stDataFrame th {{
            font-size: 15px !important;
            font-weight: 700 !important;
            padding: 12px 16px !important;
            background: {TAG_BG_CARD} !important;
            color: {TAG_OFFWHITE} !important;
            border-bottom: 2px solid {TAG_VERMELHO}40 !important;
        }}
        .stDataFrame td {{
            padding: 10px 16px !important;
            line-height: 1.5 !important;
        }}
        .stDataFrame [role="columnheader"] {{
            color: {TAG_OFFWHITE} !important;
            background: {TAG_BG_CARD} !important;
        }}

        /* ── Markdown pipe tables ── */
        .stMarkdown table {{
            width: 100% !important;
            border-collapse: collapse !important;
            margin: 12px 0 !important;
            font-size: 1rem !important;
        }}
        .stMarkdown table th {{
            background: {TAG_BG_CARD} !important;
            color: {TAG_OFFWHITE} !important;
            padding: 12px 18px !important;
            text-align: left !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            border-bottom: 2px solid {TAG_VERMELHO}40 !important;
        }}
        .stMarkdown table td {{
            padding: 10px 18px !important;
            border-bottom: 1px solid {TAG_VERMELHO}15 !important;
            font-size: 1rem !important;
            color: {TAG_OFFWHITE} !important;
        }}
        .stMarkdown table tr:nth-child(even) td {{
            background: {TAG_BG_CARD}40 !important;
        }}

        /* ══════════════════════════════════════════════════
           HEADER
        ══════════════════════════════════════════════════ */
        .tag-header {{
            display: flex;
            align-items: center;
            gap: 24px;
            padding: 24px 0 18px 0;
            margin-bottom: 8px;
        }}
        .tag-logo-box {{
            background: {TAG_VERMELHO};
            border-radius: 14px;
            padding: 14px 22px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 56px;
            box-shadow: 0 4px 16px rgba(99,13,36,0.3);
        }}
        .tag-logo-box img {{
            height: 56px;
            filter: brightness(0) invert(1);
        }}
        .tag-header-text h1 {{
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
            color: {TAG_OFFWHITE} !important;
            letter-spacing: -0.5px;
            border: none !important;
            padding-bottom: 0 !important;
        }}
        .tag-header-text p {{
            margin: 4px 0 0 0;
            font-size: 1.1rem;
            color: {TEXT_MUTED};
            font-weight: 400;
        }}

        /* ── Dividers ── */
        .tag-divider {{
            height: 3px;
            background: linear-gradient(90deg, {TAG_VERMELHO}, {TAG_LARANJA}, transparent);
            margin: 22px 0;
            border: none;
        }}
        .tag-section-divider {{
            height: 1px; border: none;
            background: linear-gradient(90deg, {TAG_VERMELHO}40, transparent);
            margin: 32px 0 24px 0;
        }}

        /* ══════════════════════════════════════════════════
           METRIC CARDS — dark theme
        ══════════════════════════════════════════════════ */
        .tag-metric-card {{
            background: linear-gradient(135deg, {TAG_BG_CARD} 0%, {TAG_BG_CARD_ALT} 100%);
            border-radius: 12px;
            padding: 28px 20px;
            text-align: center;
            border: 1px solid {TAG_VERMELHO}30;
            box-shadow: 0 4px 16px rgba(99,13,36,0.15);
        }}
        .tag-metric-card .value {{
            font-size: 3rem;
            font-weight: 700;
            color: {TAG_OFFWHITE};
            line-height: 1;
        }}
        .tag-metric-card .label {{
            font-size: 0.85rem;
            color: {TEXT_MUTED};
            margin-top: 8px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        /* ── Section titles ── */
        .tag-section-title {{
            font-size: 1.1rem; font-weight: 700; color: {TAG_LARANJA};
            margin: 32px 0 12px 0; padding-bottom: 8px;
            border-bottom: 2px solid {TAG_VERMELHO}40;
        }}

        /* ══════════════════════════════════════════════════
           MISC ELEMENTS
        ══════════════════════════════════════════════════ */
        .stCaption {{
            font-size: 0.9rem !important;
        }}
        /* sidebar now visible — navigation */

        /* ── Expander ── */
        details {{
            border-radius: 10px !important;
        }}
        details summary {{
            font-weight: 600 !important;
            font-size: 0.95rem !important;
        }}

        /* ── Plotly containers ── */
        .stPlotlyChart {{
            border-radius: 12px !important;
            margin-bottom: 16px !important;
        }}

        /* ── Dividers ── */
        hr {{ border-color: {TAG_VERMELHO}25 !important; }}

        /* ── Info/Warning boxes ── */
        [data-testid="stAlert"] {{ border-radius: 8px; }}
    </style>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────
def _get_data_atualizacao():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    cotas_path = os.path.join(data_dir, "cotas_consolidado.parquet")
    if os.path.exists(cotas_path):
        try:
            import pyarrow.parquet as pq
            pf = pq.read_table(cotas_path, columns=["data"])
            col_data = pf.column("data").to_pylist()
            if col_data:
                max_dt = max(col_data)
                return max_dt.strftime("%d/%m/%Y") if hasattr(max_dt, "strftime") else str(max_dt)[:10]
        except Exception:
            pass
    return "—"


PAGINAS = ["Carteira", "Comparativo", "Performance", "Destaques"]
PAGINAS_ICONS = ["📊", "🔀", "📈", "🏆"]


def render_sidebar():
    """Sidebar com logo grande + radio navigation."""
    with st.sidebar:
        # Logo centralizada grande
        logo_b64 = get_logo_base64()
        if logo_b64:
            st.markdown(f"""
            <div class="sidebar-logo">
                <img src="data:image/png;base64,{logo_b64}" alt="TAG Investimentos"/>
                <div class="bar"></div>
                <div class="app-name">Carteira RV</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")

        # Navegação via radio
        opcoes = [f"{PAGINAS_ICONS[i]}  {p}" for i, p in enumerate(PAGINAS)]
        default_idx = 0
        if "pagina" in st.session_state:
            try:
                default_idx = PAGINAS.index(st.session_state.pagina)
            except ValueError:
                default_idx = 0

        sel = st.radio(
            "Navegacao",
            options=opcoes,
            index=default_idx,
            label_visibility="collapsed",
        )
        # Extrair nome da página sem o emoji
        pagina_sel = sel.split("  ", 1)[1] if "  " in sel else sel
        st.session_state.pagina = pagina_sel

        st.markdown("---")

        # Data atualização no rodapé da sidebar
        data_atualizacao = _get_data_atualizacao()
        st.markdown(f"""
        <div style="text-align: center; padding: 8px 0;">
            <div style="font-size: 0.7rem; color: {TEXT_MUTED}; text-transform: uppercase;
                        letter-spacing: 1px; font-weight: 600;">Dados ate</div>
            <div style="font-size: 0.9rem; color: {TAG_OFFWHITE}; font-weight: 700;
                        margin-top: 2px;">{data_atualizacao}</div>
        </div>
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
    """Aplica layout dark TAG a um gráfico Plotly."""
    legend = dict(
        orientation="h", yanchor="bottom", y=1.02,
        font=dict(size=10, color=TEXT_MUTED, family="Tahoma, sans-serif"),
        bgcolor="rgba(0,0,0,0)",
    ) if legend_h else dict(
        font=dict(size=10, color=TEXT_MUTED, family="Tahoma, sans-serif")
    )

    layout_kwargs = dict(
        height=height, template="plotly_dark",
        xaxis=dict(
            tickfont=dict(size=9, color=TEXT_MUTED),
            gridcolor=CHART_GRID, gridwidth=1,
            zerolinecolor=CHART_GRID,
        ),
        legend=legend,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=50, r=16, t=50 if title else 30, b=margin_b),
        font=dict(family="Tahoma, sans-serif", color=TAG_OFFWHITE),
        hoverlabel=dict(
            bgcolor=TAG_BG_CARD, font_size=12,
            font_color=TAG_OFFWHITE,
            bordercolor=_hex_to_rgba(TAG_LARANJA, 0.4),
        ),
        hovermode="x unified",
        colorway=TAG_CHART_COLORS,
    )
    if title:
        layout_kwargs["title"] = dict(text=title, font=dict(size=14, color=TAG_LARANJA, family="Tahoma, sans-serif"))
    if y_title:
        layout_kwargs["yaxis"] = dict(
            title=dict(text=y_title, font=dict(size=10, color=TEXT_MUTED)),
            ticksuffix=y_suffix,
            tickfont=dict(size=9, color=TEXT_MUTED),
            gridcolor=CHART_GRID, gridwidth=1,
            zeroline=True, zerolinecolor=CHART_GRID, zerolinewidth=1,
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
        line=dict(width=2.5, color=TAG_LARANJA),
        marker=dict(size=5, color=TAG_LARANJA),
        fill="tozeroy", fillcolor=_hex_to_rgba(TAG_LARANJA, 0.15),
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
        marker=dict(size=5, color=TAG_VERMELHO),
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
        # Cor da barra gradiente
        if row["pct_pl"] >= max_pct * 0.5:
            bar_color = TAG_LARANJA
        elif row["pct_pl"] >= max_pct * 0.25:
            bar_color = "#5C85F7"
        else:
            bar_color = "#58C6F5"

        rank = i + 1
        zebra = TAG_BG_CARD_ALT if i % 2 == 1 else CARD_BG

        rows_html += f"""
        <tr style="background: {zebra}; transition: background 0.2s;">
            <td style="padding: 10px 14px; text-align: center; font-weight: 600; color: {TEXT_MUTED}; font-size: 12px; width: 40px;">{rank}</td>
            <td style="padding: 10px 14px; font-weight: 700; color: {TEXT_COLOR}; font-size: 14px; white-space: nowrap;">
                {row['Ativo']}
            </td>
            <td style="padding: 10px 14px; color: {TEXT_MUTED}; font-size: 13px;">{row['Setor']}</td>
            <td style="padding: 10px 14px; text-align: right; font-family: 'Inter', monospace; font-size: 13px; color: {TEXT_COLOR};">
                {row['Valor']}
            </td>
            <td style="padding: 10px 14px; width: 200px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="flex: 1; background: {BORDER_COLOR}; border-radius: 4px; height: 18px; overflow: hidden;">
                        <div style="width: {bar_width}%; height: 100%; background: linear-gradient(90deg, {bar_color}, {TAG_LARANJA}80); border-radius: 4px; transition: width 0.3s;"></div>
                    </div>
                    <span style="font-weight: 700; font-size: 13px; color: {TEXT_COLOR}; min-width: 52px; text-align: right;">
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
        <tr style="background: {CARD_BG};">
            <td colspan="5" style="padding: 8px 14px; font-size: 10px; color: {TEXT_MUTED}; text-align: center;">
                * O % PL e calculado sobre o patrimonio total do fundo. Fundos com posicoes em renda fixa, caixa ou derivativos terao alocacao em acoes inferior a 100%.
            </td>
        </tr>"""

    html = f"""
    <div style="border-radius: 12px; overflow: hidden; border: 1px solid {BORDER_COLOR}; margin: 8px 0 16px 0; background: {CARD_BG};">
        <table style="width: 100%; border-collapse: collapse; font-family: Tahoma, sans-serif;">
            <thead>
                <tr style="background: {TAG_BG_CARD}; border-bottom: 2px solid {TAG_VERMELHO}40;">
                    <th style="padding: 10px 14px; color: {TAG_OFFWHITE}; font-size: 10px; font-weight: 700; text-align: center; width: 36px; text-transform: uppercase; letter-spacing: 0.8px;">#</th>
                    <th style="padding: 10px 14px; color: {TAG_OFFWHITE}; font-size: 10px; font-weight: 700; text-align: left; text-transform: uppercase; letter-spacing: 0.8px;">Ativo</th>
                    <th style="padding: 10px 14px; color: {TAG_OFFWHITE}; font-size: 10px; font-weight: 700; text-align: left; text-transform: uppercase; letter-spacing: 0.8px;">Setor</th>
                    <th style="padding: 10px 14px; color: {TAG_OFFWHITE}; font-size: 10px; font-weight: 700; text-align: right; text-transform: uppercase; letter-spacing: 0.8px;">Valor</th>
                    <th style="padding: 10px 14px; color: {TAG_OFFWHITE}; font-size: 10px; font-weight: 700; text-align: left; width: 200px; text-transform: uppercase; letter-spacing: 0.8px;">% PL</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
            <tfoot>
                <tr style="background: {CARD_BG}; border-top: 1px solid {BORDER_COLOR};">
                    <td colspan="4" style="padding: 10px 14px; font-weight: 600; color: {TEXT_MUTED}; font-size: 12px; text-align: right;">
                        {n_ativos} ativos &nbsp;|&nbsp; Total alocado em acoes:
                    </td>
                    <td style="padding: 10px 14px; font-weight: 700; font-size: 14px; color: {TAG_LARANJA};">
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
    render_sidebar()

    # Carregar dados
    df_fundos, df_posicoes = carregar_todos_dados()

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

    # ── Página atual (via sidebar) ──
    pagina = st.session_state.get("pagina", "Carteira")

    # ══════════════════════════════════════════════════════════════════════
    # PÁGINA: CARTEIRA
    # ══════════════════════════════════════════════════════════════════════
    if pagina == "Carteira":
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
                    if html_table:
                        st.html(html_table)

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

            # ─── Composição por Setor ───
            _ultima_data_s = df_f["data"].max()
            _setor_atual = df_f[df_f["data"] == _ultima_data_s].groupby("setor")["pct_pl"].sum().sort_values(ascending=False)
            _setor_df = _setor_atual.reset_index()
            _setor_df.columns = ["Setor", "% PL"]
            _setor_df["% PL"] = _setor_df["% PL"].map(lambda x: f"{x:.1f}%")
            with st.expander("Alocacao Setorial Atual", expanded=False):
                st.dataframe(_setor_df, width="stretch", hide_index=True)

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

            # Gráfico de concentração (top 1 e top 5)
            fig_conc = grafico_concentracao(df_pos, cnpj, nome_fundo)
            if fig_conc is not None:
                st.plotly_chart(fig_conc, width="stretch")

            # ─── HHI de Concentração (calibrado para fundos de ações) ───
            # HHI = sum(w_i^2) * 10.000
            # Faixas baseadas na distribuição real de ~200 fundos de ações BR:
            # Mediana ~450, P75 ~550, P90 ~800
            _datas_hhi = sorted(df_f["data"].unique())
            if len(_datas_hhi) >= 2:
                _hhi_vals = []
                _hhi_dates = []
                _n_ativos_hist = []
                _top1_hist = []
                for _dt in _datas_hhi:
                    _snap = df_f[df_f["data"] == _dt]
                    _weights = _snap["pct_pl"].dropna() / 100.0
                    _weights = _weights[_weights > 0]
                    if len(_weights) > 0:
                        _hhi = (_weights ** 2).sum() * 10000
                        _hhi_vals.append(_hhi)
                        _hhi_dates.append(_dt)
                        _n_ativos_hist.append(len(_weights))
                        _top1_hist.append(_weights.max() * 100)

                if len(_hhi_vals) >= 2:
                    # --- Legenda explicativa ---
                    _last_hhi = _hhi_vals[-1]
                    _last_n = _n_ativos_hist[-1]
                    _last_top1 = _top1_hist[-1]
                    _eq_weight = 10000 / _last_n if _last_n > 0 else 10000
                    # Classificação
                    if _last_hhi < 450:
                        _classif = "Diversificado"
                        _classif_color = "#6BDE97"
                    elif _last_hhi < 700:
                        _classif = "Moderado"
                        _classif_color = "#FFBB00"
                    elif _last_hhi < 1200:
                        _classif = "Concentrado"
                        _classif_color = "#FF8853"
                    else:
                        _classif = "Muito Concentrado"
                        _classif_color = "#ED5A6E"

                    st.markdown(f"""
<div style="background: linear-gradient(135deg, {TAG_BG_CARD}, {TAG_BG_CARD_ALT}); border: 1px solid {TAG_VERMELHO}30; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; font-size: 0.82rem; color: {TEXT_MUTED};">
<strong style="color: {TAG_OFFWHITE};">Indice HHI — Concentracao da Carteira</strong><br>
O HHI (Herfindahl-Hirschman) mede a concentracao somando o quadrado dos pesos de cada ativo. Quanto maior, mais concentrado.<br>
<b>Calculo:</b> HHI = &Sigma;(w<sub>i</sub>)<sup>2</sup> &times; 10.000 &nbsp;—&nbsp;
Ex: 20 ativos iguais → HHI = 500 &nbsp;|&nbsp; 10 ativos iguais → HHI = 1.000 &nbsp;|&nbsp; 5 ativos iguais → HHI = 2.000<br>
<span style="color:#6BDE97;">&#9679;</span> <b>&lt;450</b> Diversificado &nbsp;
<span style="color:#FFBB00;">&#9679;</span> <b>450–700</b> Moderado &nbsp;
<span style="color:#FF8853;">&#9679;</span> <b>700–1.200</b> Concentrado &nbsp;
<span style="color:#ED5A6E;">&#9679;</span> <b>&gt;1.200</b> Muito concentrado<br>
<span style="font-size:0.78rem; color:{TEXT_MUTED};">Faixas calibradas com base na distribuicao de ~200 fundos de acoes brasileiros (mediana ~450).</span><br>
<b style="color:{TAG_OFFWHITE};">Atual:</b> HHI = <b style="color:{_classif_color};">{_last_hhi:.0f}</b> ({_classif}) &nbsp;|&nbsp;
{_last_n} ativos &nbsp;|&nbsp; Top holding: {_last_top1:.1f}% &nbsp;|&nbsp;
Equal-weight seria: {_eq_weight:.0f}
</div>""", unsafe_allow_html=True)

                    fig_hhi = go.Figure()
                    fig_hhi.add_trace(go.Scatter(
                        x=_hhi_dates, y=_hhi_vals,
                        mode="lines+markers",
                        name="HHI",
                        line=dict(width=2.5, color=TAG_CHART_COLORS[4]),
                        marker=dict(size=5, color=TAG_CHART_COLORS[4]),
                        hovertemplate="<b>HHI</b><br>%{x|%d/%m/%Y}: %{y:.0f}<br>N ativos: %{customdata[0]}<br>Top1: %{customdata[1]:.1f}%<extra></extra>",
                        customdata=list(zip(_n_ativos_hist, _top1_hist)),
                    ))

                    # Faixas calibradas para fundos de ações BR
                    _faixas = [
                        (0, 450, "rgba(107,222,151,0.06)", "#6BDE97", "Diversificado"),
                        (450, 700, "rgba(255,187,0,0.06)", "#FFBB00", "Moderado"),
                        (700, 1200, "rgba(255,136,83,0.06)", "#FF8853", "Concentrado"),
                        (1200, max(max(_hhi_vals) * 1.15, 1500), "rgba(237,90,110,0.06)", "#ED5A6E", "Muito concentrado"),
                    ]
                    for _y0, _y1, _fill, _lcolor, _label in _faixas:
                        fig_hhi.add_hrect(
                            y0=_y0, y1=_y1,
                            fillcolor=_fill,
                            line_width=0,
                        )
                    # Linhas de referência
                    for _yval, _lcolor, _label in [(450, "#6BDE97", "Diversificado"), (700, "#FFBB00", "Moderado"), (1200, "#ED5A6E", "Concentrado")]:
                        fig_hhi.add_hline(
                            y=_yval, line_dash="dot", line_color=_lcolor, line_width=1,
                            annotation_text=f"{_label} ({_yval})", annotation_position="bottom right",
                            annotation_font_color=_lcolor, annotation_font_size=9,
                        )

                    _chart_layout(fig_hhi, f"{nome_fundo} — Indice HHI de Concentracao",
                                  height=380, y_title="HHI", y_suffix="")
                    fig_hhi.update_yaxes(range=[0, max(max(_hhi_vals) * 1.15, 800)])
                    st.plotly_chart(fig_hhi, use_container_width=True)

            # ─── Turnover da Carteira ───
            # Mede mudanças na composição mês a mês
            if len(_datas_hhi) >= 2:
                _turnover_dates = []
                _turnover_vals = []
                _entradas_list = []
                _saidas_list = []
                _datas_sorted = sorted(_datas_hhi)
                for _ti in range(1, len(_datas_sorted)):
                    _dt_prev = _datas_sorted[_ti - 1]
                    _dt_curr = _datas_sorted[_ti]

                    _snap_prev = df_f[df_f["data"] == _dt_prev]
                    _snap_curr = df_f[df_f["data"] == _dt_curr]

                    _w_prev = dict(zip(_snap_prev["ativo"], _snap_prev["pct_pl"].fillna(0)))
                    _w_curr = dict(zip(_snap_curr["ativo"], _snap_curr["pct_pl"].fillna(0)))

                    _all_ativos = set(_w_prev.keys()) | set(_w_curr.keys())
                    _turnover = sum(abs(_w_curr.get(a, 0) - _w_prev.get(a, 0)) for a in _all_ativos) / 2

                    _entradas = set(_w_curr.keys()) - set(_w_prev.keys())
                    _saidas = set(_w_prev.keys()) - set(_w_curr.keys())

                    _turnover_dates.append(_dt_curr)
                    _turnover_vals.append(_turnover)
                    _entradas_list.append(len(_entradas))
                    _saidas_list.append(len(_saidas))

                if len(_turnover_vals) >= 2:
                    fig_turn = go.Figure()
                    fig_turn.add_trace(go.Bar(
                        x=_turnover_dates, y=_turnover_vals,
                        name="Turnover (% PL)",
                        marker_color=_hex_to_rgba(TAG_VERMELHO, 0.7),
                        hovertemplate="<b>Turnover</b><br>%{x|%d/%m/%Y}: %{y:.1f}%<extra></extra>",
                    ))
                    _chart_layout(fig_turn, f"{nome_fundo} — Turnover da Carteira",
                                  height=320, y_title="Turnover (% PL)")
                    st.plotly_chart(fig_turn, use_container_width=True)

                    # Entradas e Saídas
                    fig_es = go.Figure()
                    fig_es.add_trace(go.Bar(
                        x=_turnover_dates, y=_entradas_list,
                        name="Entradas",
                        marker_color=_hex_to_rgba("#6BDE97", 0.8),
                        hovertemplate="<b>Entradas</b><br>%{x|%d/%m/%Y}: %{y} ativos<extra></extra>",
                    ))
                    fig_es.add_trace(go.Bar(
                        x=_turnover_dates, y=[-s for s in _saidas_list],
                        name="Saidas",
                        marker_color=_hex_to_rgba("#ED5A6E", 0.8),
                        hovertemplate="<b>Saidas</b><br>%{x|%d/%m/%Y}: %{customdata} ativos<extra></extra>",
                        customdata=_saidas_list,
                    ))
                    _chart_layout(fig_es, f"{nome_fundo} — Entradas e Saidas de Ativos",
                                  height=300, y_title="Qtd Ativos", y_suffix="")
                    fig_es.update_layout(barmode="relative")
                    st.plotly_chart(fig_es, use_container_width=True)

                    # Tabela resumo do último turnover
                    if len(_turnover_dates) >= 1:
                        _last_dt = _datas_sorted[-1]
                        _prev_dt = _datas_sorted[-2]
                        _snap_last = df_f[df_f["data"] == _last_dt]
                        _snap_prev2 = df_f[df_f["data"] == _prev_dt]
                        _ativos_last = set(_snap_last["ativo"].tolist())
                        _ativos_prev2 = set(_snap_prev2["ativo"].tolist())
                        _novos = _ativos_last - _ativos_prev2
                        _removidos = _ativos_prev2 - _ativos_last

                        if _novos or _removidos:
                            with st.expander(f"Movimentacoes: {pd.Timestamp(_prev_dt).strftime('%d/%m/%Y')} → {pd.Timestamp(_last_dt).strftime('%d/%m/%Y')}", expanded=False):
                                _mov_cols = st.columns(2)
                                with _mov_cols[0]:
                                    if _novos:
                                        st.markdown("**Entradas:**")
                                        for _a in sorted(_novos):
                                            _pct = _snap_last[_snap_last["ativo"] == _a]["pct_pl"].values
                                            _pct_str = f" ({_pct[0]:.1f}%)" if len(_pct) > 0 else ""
                                            st.markdown(f"- :green[{_a}]{_pct_str}")
                                    else:
                                        st.markdown("*Sem novas entradas*")
                                with _mov_cols[1]:
                                    if _removidos:
                                        st.markdown("**Saidas:**")
                                        for _a in sorted(_removidos):
                                            _pct = _snap_prev2[_snap_prev2["ativo"] == _a]["pct_pl"].values
                                            _pct_str = f" ({_pct[0]:.1f}%)" if len(_pct) > 0 else ""
                                            st.markdown(f"- :red[{_a}]{_pct_str}")
                                    else:
                                        st.markdown("*Sem saidas*")

            # ─── Principais Mudanças vs Mês Anterior ───
            _datas_all = sorted(df_f["data"].unique())
            if len(_datas_all) >= 2:
                _dt_curr = _datas_all[-1]
                _dt_prev = _datas_all[-2]
                _snap_curr = df_f[df_f["data"] == _dt_curr].copy()
                _snap_prev = df_f[df_f["data"] == _dt_prev].copy()

                st.markdown(f"""<div style="margin-top: 18px; padding: 6px 0 4px 0; border-bottom: 2px solid {TAG_VERMELHO}40;">
                    <span style="color: {TAG_LARANJA}; font-weight: 700; font-size: 1.05rem;">
                    Principais Mudancas: {pd.Timestamp(_dt_prev).strftime('%b/%Y')} → {pd.Timestamp(_dt_curr).strftime('%b/%Y')}
                    </span></div>""", unsafe_allow_html=True)

                # --- Mudanças por SETOR ---
                _setor_curr = _snap_curr.groupby("setor")["pct_pl"].sum()
                _setor_prev = _snap_prev.groupby("setor")["pct_pl"].sum()
                _all_setores = sorted(set(_setor_curr.index) | set(_setor_prev.index))

                _setor_changes = []
                for _s in _all_setores:
                    _curr_v = _setor_curr.get(_s, 0.0)
                    _prev_v = _setor_prev.get(_s, 0.0)
                    _diff = _curr_v - _prev_v
                    if abs(_diff) >= 0.1:  # só mostra se mudou >= 0.1pp
                        _setor_changes.append({"Setor": _s, "Anterior": _prev_v, "Atual": _curr_v, "Var (pp)": _diff})

                _setor_changes.sort(key=lambda x: abs(x["Var (pp)"]), reverse=True)

                if _setor_changes:
                    # Gráfico de variação setorial (barras horizontais, full width)
                    _sc_sorted = sorted(_setor_changes, key=lambda x: x["Var (pp)"])
                    _sc_names = [x["Setor"] for x in _sc_sorted]
                    _sc_vals = [x["Var (pp)"] for x in _sc_sorted]
                    _sc_colors = [_hex_to_rgba("#6BDE97", 0.8) if v > 0 else _hex_to_rgba("#ED5A6E", 0.8) for v in _sc_vals]

                    fig_setor_ch = go.Figure()
                    fig_setor_ch.add_trace(go.Bar(
                        y=_sc_names, x=_sc_vals,
                        orientation="h",
                        marker_color=_sc_colors,
                        hovertemplate="<b>%{y}</b><br>Anterior: %{customdata[0]:.1f}%<br>Atual: %{customdata[1]:.1f}%<br>Variacao: %{x:+.1f} pp<extra></extra>",
                        customdata=[(x["Anterior"], x["Atual"]) for x in _sc_sorted],
                        text=[f"{v:+.1f}pp" for v in _sc_vals],
                        textposition="outside",
                        textfont=dict(size=10, color=TAG_OFFWHITE),
                    ))
                    fig_setor_ch.add_vline(x=0, line_color=TEXT_MUTED, line_width=1)
                    _chart_layout(fig_setor_ch, "Variacao Setorial (pp)",
                                  height=max(250, len(_sc_names) * 32 + 80),
                                  y_title="", y_suffix="")
                    fig_setor_ch.update_xaxes(title_text="pp", ticksuffix="pp")
                    st.plotly_chart(fig_setor_ch, use_container_width=True)

                # --- Mudanças por ATIVO (top aumentos e reduções) ---
                _w_curr = dict(zip(_snap_curr["ativo"], _snap_curr["pct_pl"].fillna(0)))
                _w_prev = dict(zip(_snap_prev["ativo"], _snap_prev["pct_pl"].fillna(0)))
                _all_at = set(_w_curr.keys()) | set(_w_prev.keys())

                _ativo_changes = []
                for _a in _all_at:
                    _cv = _w_curr.get(_a, 0.0)
                    _pv = _w_prev.get(_a, 0.0)
                    _d = _cv - _pv
                    if abs(_d) >= 0.1:
                        _status = "Novo" if _a not in _w_prev else ("Saiu" if _a not in _w_curr else "")
                        _ativo_changes.append({"Ativo": _a, "Anterior": _pv, "Atual": _cv, "Var (pp)": _d, "Status": _status})

                _ativo_changes.sort(key=lambda x: x["Var (pp)"], reverse=True)

                if _ativo_changes:
                    _top_up = [x for x in _ativo_changes if x["Var (pp)"] > 0][:10]
                    _top_dn = [x for x in _ativo_changes if x["Var (pp)"] < 0]
                    _top_dn = sorted(_top_dn, key=lambda x: x["Var (pp)"])[:10]

                    _at_cols = st.columns(2)

                    # Gráfico: Maiores Aumentos
                    with _at_cols[0]:
                        if _top_up:
                            _up_sorted = sorted(_top_up, key=lambda x: x["Var (pp)"])
                            _up_names = [f"{x['Ativo']} {'(NOVO)' if x['Status'] == 'Novo' else ''}" for x in _up_sorted]
                            _up_vals = [x["Var (pp)"] for x in _up_sorted]

                            fig_up = go.Figure()
                            fig_up.add_trace(go.Bar(
                                y=_up_names, x=_up_vals,
                                orientation="h",
                                marker_color=_hex_to_rgba("#6BDE97", 0.8),
                                hovertemplate="<b>%{customdata[0]}</b><br>Anterior: %{customdata[1]:.1f}%<br>Atual: %{customdata[2]:.1f}%<br>Variacao: +%{x:.1f} pp<extra></extra>",
                                customdata=[(x["Ativo"], x["Anterior"], x["Atual"]) for x in _up_sorted],
                                text=[f"+{v:.1f}pp" for v in _up_vals],
                                textposition="outside",
                                textfont=dict(size=10, color="#6BDE97"),
                            ))
                            _chart_layout(fig_up, "Maiores Aumentos (pp)",
                                          height=max(220, len(_up_names) * 28 + 80),
                                          y_title="", y_suffix="")
                            fig_up.update_xaxes(title_text="pp", ticksuffix="pp")
                            st.plotly_chart(fig_up, use_container_width=True)
                        else:
                            st.caption("Sem aumentos significativos")

                    # Gráfico: Maiores Reduções
                    with _at_cols[1]:
                        if _top_dn:
                            _dn_sorted = sorted(_top_dn, key=lambda x: x["Var (pp)"], reverse=True)
                            _dn_names = [f"{x['Ativo']} {'(SAIU)' if x['Status'] == 'Saiu' else ''}" for x in _dn_sorted]
                            _dn_vals = [x["Var (pp)"] for x in _dn_sorted]

                            fig_dn = go.Figure()
                            fig_dn.add_trace(go.Bar(
                                y=_dn_names, x=_dn_vals,
                                orientation="h",
                                marker_color=_hex_to_rgba("#ED5A6E", 0.8),
                                hovertemplate="<b>%{customdata[0]}</b><br>Anterior: %{customdata[1]:.1f}%<br>Atual: %{customdata[2]:.1f}%<br>Variacao: %{x:.1f} pp<extra></extra>",
                                customdata=[(x["Ativo"], x["Anterior"], x["Atual"]) for x in _dn_sorted],
                                text=[f"{v:.1f}pp" for v in _dn_vals],
                                textposition="outside",
                                textfont=dict(size=10, color="#ED5A6E"),
                            ))
                            _chart_layout(fig_dn, "Maiores Reducoes (pp)",
                                          height=max(220, len(_dn_names) * 28 + 80),
                                          y_title="", y_suffix="")
                            fig_dn.update_xaxes(title_text="pp", ticksuffix="pp")
                            st.plotly_chart(fig_dn, use_container_width=True)
                        else:
                            st.caption("Sem reducoes significativas")

            # ─── Evolução do PL ───
            _pl_mensal = df_f.groupby("data")["pl"].first().reset_index()
            st.plotly_chart(
                grafico_pl(_pl_mensal, f"{nome_fundo} — Patrimonio Liquido"),
                width="stretch",
            )

            if idx < len(fundos_sel) - 1:
                st.markdown('<div class="tag-section-divider"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # PÁGINA: COMPARATIVO
    # ══════════════════════════════════════════════════════════════════════
    elif pagina == "Comparativo":
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
                textfont=dict(size=11, color=TEXT_COLOR),
                colorscale=[
                    [0, TAG_BG_CARD], [0.25, "#2A3060"],
                    [0.5, "#3f51b5"], [0.75, "#5C85F7"],
                    [1, "#58C6F5"]
                ],
                hovertemplate="<b>%{y}</b> x <b>%{x}</b><br>Sobreposicao: %{text}<extra></extra>",
                showscale=True,
                colorbar=dict(title="% PL", ticksuffix="%", tickfont=dict(color=TEXT_MUTED)),
            ))
            fig_heat_a.update_layout(
                height=max(420, 70 * n + 140),
                template="plotly_dark",
                xaxis=dict(tickangle=45, side="bottom", tickfont=dict(color=TEXT_MUTED)),
                yaxis=dict(autorange="reversed", tickfont=dict(color=TEXT_MUTED)),
                font=dict(family="Tahoma, sans-serif", size=11, color=TEXT_COLOR),
                margin=dict(l=10, r=10, t=20, b=120),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
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
                textfont=dict(size=11, color=TEXT_COLOR),
                colorscale=[
                    [0, TAG_BG_CARD], [0.25, "#3D1520"],
                    [0.5, "#7A1E35"], [0.75, "#B44A5E"],
                    [1, TAG_LARANJA]
                ],
                hovertemplate="<b>%{y}</b> x <b>%{x}</b><br>Sobreposicao: %{text}<extra></extra>",
                showscale=True,
                colorbar=dict(title="% PL", ticksuffix="%", tickfont=dict(color=TEXT_MUTED)),
            ))
            fig_heat_s.update_layout(
                height=max(420, 70 * n + 140),
                template="plotly_dark",
                xaxis=dict(tickangle=45, side="bottom", tickfont=dict(color=TEXT_MUTED)),
                yaxis=dict(autorange="reversed", tickfont=dict(color=TEXT_MUTED)),
                font=dict(family="Tahoma, sans-serif", size=11, color=TEXT_COLOR),
                margin=dict(l=10, r=10, t=20, b=120),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
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
                    height=480, template="plotly_dark",
                    yaxis=dict(title="% do PL", ticksuffix="%", gridcolor=CHART_GRID,
                               tickfont=dict(color=TEXT_MUTED)),
                    xaxis=dict(tickfont=dict(color=TEXT_MUTED)),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Tahoma, sans-serif", color=TEXT_COLOR),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                font=dict(size=10, color=TEXT_MUTED)),
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

            # ─── 7. HEATMAP: Correlação de Retornos entre Fundos ───
            st.markdown('<div class="tag-section-title">Correlacao de Retornos entre Fundos</div>', unsafe_allow_html=True)
            st.caption("Correlacao de Pearson dos retornos diarios de cotas (CVM). Valores proximos de 1 indicam fundos que se movem juntos; valores baixos indicam diversificacao.")

            # Buscar cotas dos fundos selecionados + benchmarks
            _corr_cnpjs = tuple(set([nome_cnpj_map[n] for n in nomes_comp]) | set(BENCHMARK_CNPJS.values()))
            _df_cotas_corr = carregar_cotas_fundos(_corr_cnpjs, meses=36)

            if _df_cotas_corr.empty:
                st.info("Sem dados de cotas para calcular correlacoes.")
            else:
                _pivot_q = _df_cotas_corr.pivot_table(index="data", columns="cnpj_fundo", values="vl_quota")
                _pivot_q = _pivot_q.sort_index().ffill()
                _pivot_r = _pivot_q.pct_change().dropna(how="all")

                # Mapear CNPJ -> label curto
                _corr_labels = {}
                for nm in nomes_comp:
                    cnpj = nome_cnpj_map[nm]
                    parts = nm.split()
                    short = " ".join(parts[:3]) if len(parts) > 3 else nm
                    if len(short) > 25:
                        short = short[:22] + "..."
                    _corr_labels[cnpj] = short
                for cnpj, name in {v: k for k, v in BENCHMARK_CNPJS.items()}.items():
                    _corr_labels[cnpj] = name

                _corr_cols = [nome_cnpj_map[n] for n in nomes_comp if nome_cnpj_map[n] in _pivot_r.columns]
                _corr_bench = [c for c in BENCHMARK_CNPJS.values() if c in _pivot_r.columns]
                _corr_all = _corr_cols + _corr_bench

                if len(_corr_all) >= 2:
                    _corr_matrix = _pivot_r[_corr_all].corr()
                    _corr_labels_list = [_corr_labels.get(c, c[:10]) for c in _corr_all]

                    # Texto anotado na matrix
                    _corr_text = [[f"{_corr_matrix.iloc[i, j]:.2f}" for j in range(len(_corr_all))] for i in range(len(_corr_all))]

                    fig_corr = go.Figure(data=go.Heatmap(
                        z=_corr_matrix.values,
                        x=_corr_labels_list,
                        y=_corr_labels_list,
                        text=_corr_text,
                        texttemplate="%{text}",
                        textfont=dict(size=11, color=TEXT_COLOR),
                        colorscale=[
                            [0.0, TAG_BG_CARD],
                            [0.3, "#3D1520"],
                            [0.5, "#7A1E35"],
                            [0.7, "#e94560"],
                            [1.0, "#630D24"],
                        ],
                        zmin=0, zmax=1,
                        colorbar=dict(
                            title=dict(text="Correlacao", font=dict(size=10, color=TEXT_MUTED)),
                            tickfont=dict(size=9, color=TEXT_MUTED),
                            bgcolor="rgba(0,0,0,0)",
                        ),
                        hovertemplate="<b>%{x}</b> × <b>%{y}</b><br>Correlacao: %{z:.3f}<extra></extra>",
                    ))

                    fig_corr.update_layout(
                        height=max(400, 60 * len(_corr_all)),
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Tahoma, sans-serif", color=TEXT_COLOR),
                        xaxis=dict(tickfont=dict(size=9, color=TEXT_MUTED), side="bottom"),
                        yaxis=dict(tickfont=dict(size=9, color=TEXT_MUTED), autorange="reversed"),
                        margin=dict(l=120, r=50, t=30, b=120),
                        hoverlabel=dict(bgcolor=CARD_BG, font_size=12, bordercolor=_hex_to_rgba(TAG_LARANJA, 0.4)),
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)

                    # ─── 8. Correlacao Rolling (janela 63du = 3 meses) ───
                    st.markdown('<div class="tag-section-title">Correlacao Rolling vs IBOVESPA (63 du)</div>', unsafe_allow_html=True)
                    st.caption("Correlacao movel de 63 dias uteis (~3 meses) entre cada fundo e o IBOVESPA. Queda na correlacao pode indicar mudanca de estrategia ou diversificacao.")

                    _ibov_cnpj_corr = list(BENCHMARK_CNPJS.values())[0]
                    if _ibov_cnpj_corr in _pivot_r.columns:
                        _ibov_r_corr = _pivot_r[_ibov_cnpj_corr].dropna()
                        fig_rcorr = go.Figure()
                        for i, cnpj in enumerate(_corr_cols):
                            _fr = _pivot_r[cnpj].dropna()
                            _common_idx = _fr.index.intersection(_ibov_r_corr.index)
                            if len(_common_idx) < 63:
                                continue
                            _roll_corr = _fr.loc[_common_idx].rolling(63).corr(_ibov_r_corr.loc[_common_idx]).dropna()
                            label = _corr_labels.get(cnpj, cnpj[:10])
                            fig_rcorr.add_trace(go.Scatter(
                                x=_roll_corr.index, y=_roll_corr.values,
                                name=label, mode="lines",
                                line=dict(width=2, color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
                                hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}: %{{y:.3f}}<extra></extra>",
                            ))

                        fig_rcorr.add_hline(y=1.0, line_dash="dot", line_color="#555", line_width=0.5)
                        fig_rcorr.add_hline(y=0.5, line_dash="dot", line_color="#555", line_width=0.5)
                        fig_rcorr.add_hline(y=0.0, line_dash="dot", line_color="#888", line_width=1)
                        _chart_layout(fig_rcorr, "", height=400, y_title="Correlacao", y_suffix="")
                        st.plotly_chart(fig_rcorr, use_container_width=True)
                else:
                    st.info("Selecione ao menos 2 fundos com dados de cotas para ver a correlacao.")


    # ══════════════════════════════════════════════════════════════════════
    # PÁGINA: PERFORMANCE
    # ══════════════════════════════════════════════════════════════════════
    elif pagina == "Performance":
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
                    list(BENCHMARK_CNPJS.values())[1]: dict(color="#58C6F5", dash="dash"),
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
                    fig_ret.add_hline(y=0, line_dash="dot", line_color="rgba(230,228,219,0.2)", line_width=1)
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

                    # ─── G3: Percentil (janela móvel) — usando amostra de fundos RV ───
                    st.markdown(f'<div class="tag-section-title">Percentil — Janela {janela_label}</div>', unsafe_allow_html=True)
                    st.caption(f"Posicao relativa do fundo na amostra de fundos RV acompanhados (0%=pior, 100%=melhor). Janela movel de {janela_label}.")

                    # Carregar cotas de TODOS os fundos da amostra para ranking correto
                    all_sample_cnpjs = tuple(set(df_fundos["cnpj_norm"].dropna().tolist()) | set(BENCHMARK_CNPJS.values()))
                    df_cotas_universe = carregar_cotas_fundos(all_sample_cnpjs, meses=120)

                    if not df_cotas_universe.empty:
                        # Pivot: data × cnpj → vl_quota
                        pivot_univ = df_cotas_universe.pivot_table(
                            index="data", columns="cnpj_fundo", values="vl_quota"
                        ).sort_index().ffill()

                        # Filtrar pelo período selecionado
                        mask_u = (pivot_univ.index >= pd.Timestamp(dt_inicio)) & (pivot_univ.index <= pd.Timestamp(dt_fim))
                        pivot_univ = pivot_univ.loc[mask_u]

                        # Retorno diário de todos os fundos
                        ret_univ = pivot_univ.pct_change()

                        # Rolling return (janela) para TODOS os fundos — vectorizado
                        # Usar log returns para velocidade: log_ret.rolling().sum() → exp() - 1
                        log_ret = np.log(1 + ret_univ)
                        roll_log = log_ret.rolling(janela_du, min_periods=max(1, janela_du // 2)).sum()
                        roll_ret_all = np.exp(roll_log) - 1

                        # Para cada data, calcular o percentil de cada fundo vs o universo
                        # Rank percentil: % de fundos que tiveram retorno PIOR (menor)
                        # rank(pct=True) dá exatamente isso
                        roll_pctl = roll_ret_all.rank(axis=1, pct=True, method="average") * 100

                        fig_rank = go.Figure()
                        # Quintil bands (dark theme)
                        quintil_colors = [
                            ("rgba(107,222,151,0.08)", "Q1 (top)"), ("rgba(255,187,0,0.06)", "Q2"),
                            ("rgba(255,136,83,0.05)", "Q3"), ("rgba(237,90,110,0.06)", "Q4"),
                            ("rgba(255,60,60,0.08)", "Q5 (bottom)")
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
                            if cnpj not in roll_pctl.columns:
                                continue
                            label = cnpj_to_label.get(cnpj, cnpj[:10])
                            is_bench = cnpj in bench_cols
                            pctls = roll_pctl[cnpj].dropna()
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

                        n_fundos_univ = roll_pctl.count(axis=1).median()
                        fig_rank.add_hline(y=50, line_dash="dot", line_color="#999", line_width=1)
                        _chart_layout(fig_rank, "", height=450, y_title="Percentil", y_suffix="%")
                        fig_rank.update_yaxes(range=[0, 100])
                        st.plotly_chart(fig_rank, use_container_width=True)
                        st.caption(f"Universo: ~{int(n_fundos_univ)} fundos RV da amostra acompanhada.")
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
                                height=480, template="plotly_dark",
                                xaxis=dict(title=dict(text="Downside Capture (%)", font=dict(size=10, color=TEXT_MUTED)),
                                           ticksuffix="%", tickfont=dict(size=9, color=TEXT_MUTED), gridcolor=CHART_GRID),
                                yaxis=dict(title=dict(text="Upside Capture (%)", font=dict(size=10, color=TEXT_MUTED)),
                                           ticksuffix="%", tickfont=dict(size=9, color=TEXT_MUTED), gridcolor=CHART_GRID),
                                font=dict(family="Tahoma, sans-serif", color=TEXT_COLOR),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10, color=TEXT_MUTED)),
                                margin=dict(l=50, r=16, t=40, b=50),
                                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                hoverlabel=dict(bgcolor=CARD_BG, font_size=12, bordercolor=_hex_to_rgba(TAG_LARANJA, 0.4)),
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
                        fig_alpha.add_hline(y=0, line_dash="dot", line_color="rgba(230,228,219,0.2)", line_width=1)
                        _chart_layout(fig_alpha, "", height=400, y_title="Alpha (% a.a.)")
                        st.plotly_chart(fig_alpha, use_container_width=True)

                    # ─── G6: Rolling Tracking Error ───
                    st.markdown(f'<div class="tag-section-title">Tracking Error Rolling — Janela {janela_label}</div>', unsafe_allow_html=True)
                    st.caption("Desvio dos retornos em relação ao IBOVESPA. TE < 2% = closet indexer. TE 2-8% = gestão ativa moderada. TE > 8% = alta convicção.")

                    if ibov_cnpj in pivot_ret.columns:
                        fig_te = go.Figure()
                        # Faixas de referência (dark)
                        fig_te.add_hrect(y0=0, y1=2, fillcolor="rgba(42,42,58,0.5)", line_width=0, layer="below")
                        fig_te.add_hrect(y0=2, y1=8, fillcolor="rgba(92,133,247,0.06)", line_width=0, layer="below")
                        fig_te.add_hline(y=2, line_dash="dot", line_color="rgba(230,228,219,0.2)", line_width=1, annotation_text="Closet Indexer", annotation_position="top left", annotation_font_color=TEXT_MUTED)
                        fig_te.add_hline(y=8, line_dash="dot", line_color="rgba(230,228,219,0.2)", line_width=1, annotation_text="Alta Convicção", annotation_position="top left", annotation_font_color=TEXT_MUTED)

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
                        fig_scatter.add_hline(y=0, line_dash="dot", line_color="rgba(230,228,219,0.2)", line_width=1)
                        fig_scatter.update_layout(
                            height=480, template="plotly_dark",
                            xaxis=dict(title=dict(text="Ulcer Index (risco)", font=dict(size=10, color=TEXT_MUTED)),
                                       zeroline=True, tickfont=dict(size=9, color=TEXT_MUTED), gridcolor=CHART_GRID),
                            yaxis=dict(title=dict(text="Retorno Anualizado (%)", font=dict(size=10, color=TEXT_MUTED)),
                                       ticksuffix="%", tickfont=dict(size=9, color=TEXT_MUTED), gridcolor=CHART_GRID),
                            font=dict(family="Tahoma, sans-serif", color=TEXT_COLOR),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10, color=TEXT_MUTED)),
                            margin=dict(l=50, r=16, t=40, b=50),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            hoverlabel=dict(bgcolor=CARD_BG, font_size=12, bordercolor=_hex_to_rgba(TAG_LARANJA, 0.4)),
                            hovermode="closest",
                        )
                        st.plotly_chart(fig_scatter, use_container_width=True)

                    # ─── G8: Tabela de Métricas Completa (expandida) ───
                    st.markdown('<div class="tag-section-title">Metricas de Performance e Gestao</div>', unsafe_allow_html=True)
                    st.caption("Sortino = retorno exc./vol. queda | Treynor = retorno exc./beta | M² = retorno ajustado ao risco do mercado | Omega = ganhos/perdas vs CDI | VaR/CVaR = risco de cauda 95% | Recup.DD = dias para recuperar do pior drawdown | Consist. = % janelas 12M que bateu IBOV")

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

                        # ── Sortino (downside deviation) ──
                        excess_daily = ret - cdi_diario
                        downside = excess_daily[excess_daily < 0]
                        downside_dev = np.sqrt((downside ** 2).mean()) * np.sqrt(252) if len(downside) > 0 else 0
                        sortino = (ret_anual - CDI_ANUAL) / downside_dev if downside_dev > 0 else 0

                        # ── VaR 95% e CVaR (Expected Shortfall) ──
                        var_95 = np.nanpercentile(ret, 5) * 100  # 5º percentil = VaR 95%
                        cvar_95 = ret[ret <= np.nanpercentile(ret, 5)].mean() * 100 if len(ret[ret <= np.nanpercentile(ret, 5)]) > 0 else var_95

                        # ── Tempo de recuperação do drawdown (dias) ──
                        dd_decimal = cum / cum.cummax() - 1
                        underwater = dd_decimal < -0.001  # tolerância 0.1%
                        if underwater.any():
                            # Encontrar períodos de drawdown
                            dd_groups = (~underwater).cumsum()
                            dd_durations = underwater.groupby(dd_groups).sum()
                            max_recovery_days = int(dd_durations.max()) if len(dd_durations) > 0 else 0
                        else:
                            max_recovery_days = 0

                        # ── Omega Ratio (ganhos/perdas vs CDI diário) ──
                        gains = excess_daily[excess_daily > 0].sum()
                        losses = excess_daily[excess_daily < 0].abs().sum()
                        omega = gains / losses if losses > 0 else 0

                        # ── Métricas vs benchmark (IBOV) ──
                        ir, hit_rate, up_cap, down_cap = np.nan, np.nan, np.nan, np.nan
                        beta_val, treynor, m2_val, consist_pct = np.nan, np.nan, np.nan, np.nan
                        if ibov_cnpj in pivot_ret.columns and cnpj != ibov_cnpj:
                            bench_r = pivot_ret[ibov_cnpj].reindex(ret.index).dropna()
                            common_idx = ret.index.intersection(bench_r.index)
                            if len(common_idx) > 20:
                                fr = ret.loc[common_idx]
                                br = bench_r.loc[common_idx]
                                active = fr - br
                                te = active.std() * np.sqrt(252)
                                ir = active.mean() * 252 / te if te > 0 else 0

                                # ── Beta e Treynor ──
                                cov_fb = np.cov(fr - cdi_diario, br - cdi_diario)[0, 1]
                                var_b = np.var(br - cdi_diario)
                                beta_val = cov_fb / var_b if var_b > 0 else 1.0
                                treynor = (ret_anual - CDI_ANUAL) / beta_val if beta_val != 0 else 0

                                # ── M² (Modigliani) ──
                                vol_bench = br.std() * np.sqrt(252)
                                if vol_anual > 0:
                                    m2_val = (sharpe * vol_bench + CDI_ANUAL) * 100  # em %
                                else:
                                    m2_val = CDI_ANUAL * 100

                                # Monthly hit rate & capture
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

                                # ── Consistência: % de janelas rolling 252d que bateu IBOV ──
                                if len(common_idx) >= 252:
                                    roll_f = fr.rolling(252).apply(lambda x: (1 + x).prod() - 1, raw=False)
                                    roll_b = br.rolling(252).apply(lambda x: (1 + x).prod() - 1, raw=False)
                                    valid = roll_f.dropna().index.intersection(roll_b.dropna().index)
                                    if len(valid) > 20:
                                        consist_pct = (roll_f.loc[valid] > roll_b.loc[valid]).sum() / len(valid) * 100

                        # UPI vs IBOV
                        upi_vs_ibov = np.nan
                        if ibov_cnpj in pivot_ret.columns and cnpj != ibov_cnpj:
                            excess_total = ret_anual - ((1 + pivot_ret[ibov_cnpj].dropna()).prod() ** (252 / max(1, len(pivot_ret[ibov_cnpj].dropna()))) - 1)
                            if ulcer > 0:
                                upi_vs_ibov = (excess_total * 100) / ulcer

                        label = cnpj_to_label.get(cnpj, cnpj[:10])
                        row_data = {
                            "Fundo": label,
                            "Ret.Acum": f"{ret_acum*100:.1f}%",
                            "Ret.Anual": f"{ret_anual*100:.1f}%",
                            "Vol.Anual": f"{vol_anual*100:.1f}%",
                            "Sharpe": f"{sharpe:.2f}",
                            "Sortino": f"{sortino:.2f}",
                            "Max DD": f"{max_dd:.1f}%",
                            "Recup.DD": f"{max_recovery_days}d",
                            "Calmar": f"{calmar:.2f}",
                            "Ulcer": f"{ulcer:.1f}",
                            "VaR 95%": f"{var_95:.2f}%",
                            "CVaR": f"{cvar_95:.2f}%",
                            "Omega": f"{omega:.2f}",
                            "UPI vs IBOV": f"{upi_vs_ibov:.2f}" if pd.notna(upi_vs_ibov) else "—",
                        }
                        if pd.notna(ir):
                            row_data["Beta"] = f"{beta_val:.2f}" if pd.notna(beta_val) else "—"
                            row_data["Treynor"] = f"{treynor:.2f}" if pd.notna(treynor) else "—"
                            row_data["M²"] = f"{m2_val:.1f}%" if pd.notna(m2_val) else "—"
                            row_data["IR"] = f"{ir:.2f}"
                            row_data["Hit%"] = f"{hit_rate:.0f}%" if pd.notna(hit_rate) else "—"
                            row_data["Consist."] = f"{consist_pct:.0f}%" if pd.notna(consist_pct) else "—"
                            row_data["Up Cap"] = f"{up_cap:.0f}%" if pd.notna(up_cap) else "—"
                            row_data["Dn Cap"] = f"{down_cap:.0f}%" if pd.notna(down_cap) else "—"
                        else:
                            row_data.update({"Beta": "—", "Treynor": "—", "M²": "—", "IR": "—",
                                             "Hit%": "—", "Consist.": "—", "Up Cap": "—", "Dn Cap": "—"})
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
                    fig_sharpe.add_hline(y=0, line_dash="dot", line_color="rgba(230,228,219,0.2)", line_width=1)
                    _chart_layout(fig_sharpe, "", height=400, y_title="Sharpe Ratio", y_suffix="")
                    st.plotly_chart(fig_sharpe, use_container_width=True)

                    # ─── G10: Rolling UPI vs IBOVESPA (Ulcer Performance Index) ───
                    st.markdown(f'<div class="tag-section-title">UPI vs IBOVESPA Rolling — Janela {janela_label}</div>', unsafe_allow_html=True)
                    st.caption(f"Ulcer Performance Index: (Retorno excedente sobre IBOV) / Ulcer Index. Quanto maior, melhor o retorno ajustado pelo risco de drawdown.")

                    if ibov_cnpj in pivot_ret.columns:
                        fig_upi = go.Figure()
                        bench_cum = (1 + pivot_ret[ibov_cnpj]).cumprod()

                        for i, cnpj in enumerate(fund_cols):
                            if cnpj not in pivot_ret.columns:
                                continue
                            label = cnpj_to_label.get(cnpj, cnpj[:10])
                            fund_cum = (1 + pivot_ret[cnpj]).cumprod()
                            # Rolling excess return vs IBOV
                            excess_ret = pivot_ret[cnpj] - pivot_ret[ibov_cnpj]
                            roll_excess = excess_ret.rolling(janela_du).apply(
                                lambda x: (1 + x).prod() - 1, raw=False
                            )
                            # Rolling Ulcer Index do fundo
                            def _rolling_ulcer(series, window):
                                cum = (1 + series).cumprod()
                                dd = (cum / cum.cummax() - 1) * 100
                                return dd.rolling(window).apply(lambda x: np.sqrt((x**2).mean()), raw=True)
                            roll_ulcer = _rolling_ulcer(pivot_ret[cnpj], janela_du)
                            # UPI = excess return / ulcer index
                            roll_upi = (roll_excess * 100) / roll_ulcer.replace(0, np.nan)
                            roll_upi = roll_upi.dropna()
                            # Clip extremes for readability
                            roll_upi = roll_upi.clip(-5, 5)
                            fig_upi.add_trace(go.Scatter(
                                x=roll_upi.index, y=roll_upi.values,
                                name=label, mode="lines",
                                line=dict(width=2, color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
                                hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>UPI: %{{y:.2f}}<extra></extra>",
                            ))

                        for cnpj in bench_cols:
                            if cnpj == ibov_cnpj or cnpj not in pivot_ret.columns:
                                continue
                            label = cnpj_to_label.get(cnpj, cnpj[:10])
                            style = bench_styles.get(cnpj, dict(color="#999", dash="dash"))
                            excess_ret = pivot_ret[cnpj] - pivot_ret[ibov_cnpj]
                            roll_excess = excess_ret.rolling(janela_du).apply(
                                lambda x: (1 + x).prod() - 1, raw=False
                            )
                            roll_ulcer = _rolling_ulcer(pivot_ret[cnpj], janela_du)
                            roll_upi = (roll_excess * 100) / roll_ulcer.replace(0, np.nan)
                            roll_upi = roll_upi.dropna().clip(-5, 5)
                            fig_upi.add_trace(go.Scatter(
                                x=roll_upi.index, y=roll_upi.values,
                                name=label, mode="lines",
                                line=dict(width=1.5, **style),
                                hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>UPI: %{{y:.2f}}<extra></extra>",
                            ))

                        fig_upi.add_hline(y=0, line_dash="dot", line_color="rgba(230,228,219,0.2)", line_width=1)
                        _chart_layout(fig_upi, "", height=400, y_title="UPI vs IBOV", y_suffix="")
                        st.plotly_chart(fig_upi, use_container_width=True)

                    # ─── G11: Beta Rolling vs IBOVESPA ───
                    st.markdown(f'<div class="tag-section-title">Beta Rolling vs IBOVESPA — Janela {janela_label}</div>', unsafe_allow_html=True)
                    st.caption("Beta mede a sensibilidade ao mercado. Beta > 1 = amplifica o mercado. Beta < 1 = mais defensivo. Mostra se o gestor está aumentando ou diminuindo exposição.")

                    if ibov_cnpj in pivot_ret.columns:
                        fig_beta = go.Figure()
                        bench_r_full = pivot_ret[ibov_cnpj]
                        for i, cnpj in enumerate(fund_cols):
                            if cnpj not in pivot_ret.columns:
                                continue
                            label = cnpj_to_label.get(cnpj, cnpj[:10])
                            fund_r = pivot_ret[cnpj]
                            # Rolling beta: cov(fund, bench) / var(bench)
                            roll_cov = fund_r.rolling(janela_du).cov(bench_r_full)
                            roll_var = bench_r_full.rolling(janela_du).var()
                            roll_beta = (roll_cov / roll_var).dropna()
                            roll_beta = roll_beta.clip(0, 3)  # clip extremos
                            fig_beta.add_trace(go.Scatter(
                                x=roll_beta.index, y=roll_beta.values,
                                name=label, mode="lines",
                                line=dict(width=2, color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
                                hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>Beta: %{{y:.2f}}<extra></extra>",
                            ))
                        for cnpj in bench_cols:
                            if cnpj == ibov_cnpj or cnpj not in pivot_ret.columns:
                                continue
                            label = cnpj_to_label.get(cnpj, cnpj[:10])
                            style = bench_styles.get(cnpj, dict(color="#999", dash="dash"))
                            roll_cov = pivot_ret[cnpj].rolling(janela_du).cov(bench_r_full)
                            roll_var = bench_r_full.rolling(janela_du).var()
                            roll_beta = (roll_cov / roll_var).dropna().clip(0, 3)
                            fig_beta.add_trace(go.Scatter(
                                x=roll_beta.index, y=roll_beta.values,
                                name=label, mode="lines",
                                line=dict(width=1.5, **style),
                                hovertemplate=f"<b>{label}</b><br>%{{x|%d/%m/%Y}}<br>Beta: %{{y:.2f}}<extra></extra>",
                            ))
                        fig_beta.add_hline(y=1, line_dash="dot", line_color="rgba(230,228,219,0.2)", line_width=1,
                                           annotation_text="Beta = 1", annotation_position="top left",
                                           annotation_font_color=TEXT_MUTED)
                        _chart_layout(fig_beta, "", height=400, y_title="Beta vs IBOV", y_suffix="")
                        st.plotly_chart(fig_beta, use_container_width=True)

                    # ─── G12: Performance por Regime de Mercado ───
                    st.markdown('<div class="tag-section-title">Performance por Regime de Mercado</div>', unsafe_allow_html=True)
                    st.caption("Retorno medio mensal dos fundos em meses BULL (IBOV > 0) e BEAR (IBOV < 0). Mostra se o fundo protege na queda ou so vai bem na alta.")

                    if ibov_cnpj in pivot_ret.columns:
                        # Calcular retornos mensais
                        monthly_all = pivot_ret[all_cols].resample("ME").apply(lambda x: (1 + x).prod() - 1)
                        monthly_ibov = monthly_all[ibov_cnpj].dropna() if ibov_cnpj in monthly_all.columns else pd.Series(dtype=float)

                        if len(monthly_ibov) > 6:
                            bull_months = monthly_ibov > 0
                            bear_months = monthly_ibov < 0

                            regime_data = []
                            for cnpj in all_cols:
                                if cnpj not in monthly_all.columns:
                                    continue
                                m_ret = monthly_all[cnpj].dropna()
                                common_m = m_ret.index.intersection(monthly_ibov.index)
                                if len(common_m) < 6:
                                    continue
                                m_ret_c = m_ret.loc[common_m]
                                bull_ret = m_ret_c[bull_months.reindex(common_m, fill_value=False)].mean() * 100
                                bear_ret = m_ret_c[bear_months.reindex(common_m, fill_value=False)].mean() * 100
                                n_bull = bull_months.reindex(common_m, fill_value=False).sum()
                                n_bear = bear_months.reindex(common_m, fill_value=False).sum()
                                regime_data.append({
                                    "cnpj": cnpj,
                                    "label": cnpj_to_label.get(cnpj, cnpj[:10]),
                                    "bull": bull_ret, "bear": bear_ret,
                                    "is_fund": cnpj in fund_cols, "is_bench": cnpj in bench_cols,
                                })

                            if regime_data:
                                df_regime = pd.DataFrame(regime_data)
                                fig_regime = go.Figure()
                                for idx_r, row_r in df_regime.iterrows():
                                    if row_r["is_fund"]:
                                        color = TAG_CHART_COLORS[list(df_regime[df_regime["is_fund"]].index).index(idx_r) % len(TAG_CHART_COLORS)]
                                        size = 16
                                    elif row_r["is_bench"]:
                                        color = bench_styles.get(row_r["cnpj"], {}).get("color", "#999")
                                        size = 14
                                    else:
                                        continue
                                    fig_regime.add_trace(go.Scatter(
                                        x=[row_r["bear"]], y=[row_r["bull"]],
                                        mode="markers+text", name=row_r["label"],
                                        marker=dict(symbol="star", size=size, color=color,
                                                    line=dict(width=1, color="white")),
                                        text=[row_r["label"]], textposition="top center",
                                        textfont=dict(size=9),
                                        hovertemplate=f"<b>{row_r['label']}</b><br>Bull: {row_r['bull']:.2f}%/mes<br>Bear: {row_r['bear']:.2f}%/mes<extra></extra>",
                                    ))
                                fig_regime.update_layout(
                                    height=480, template="plotly_dark",
                                    xaxis=dict(title=dict(text="Ret. Medio Mensal BEAR (%)", font=dict(size=10, color=TEXT_MUTED)),
                                               ticksuffix="%", tickfont=dict(size=9, color=TEXT_MUTED), gridcolor=CHART_GRID),
                                    yaxis=dict(title=dict(text="Ret. Medio Mensal BULL (%)", font=dict(size=10, color=TEXT_MUTED)),
                                               ticksuffix="%", tickfont=dict(size=9, color=TEXT_MUTED), gridcolor=CHART_GRID),
                                    font=dict(family="Tahoma, sans-serif", color=TEXT_COLOR),
                                    legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10, color=TEXT_MUTED)),
                                    margin=dict(l=50, r=16, t=40, b=50),
                                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                    hoverlabel=dict(bgcolor=CARD_BG, font_size=12, bordercolor=_hex_to_rgba(TAG_LARANJA, 0.4)),
                                    hovermode="closest",
                                )
                                st.plotly_chart(fig_regime, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════
    # PÁGINA: DESTAQUES (Rankings multi-janela — inspirado relatório RV Long Only)
    # ══════════════════════════════════════════════════════════════════════
    elif pagina == "Destaques":
        # ── Filtros de Categoria e Tier para Destaques ──
        col_dest_cat, col_dest_tier = st.columns(2)
        with col_dest_cat:
            dest_categorias = sorted(df_fundos["categoria"].dropna().unique().tolist())
            dest_cat_sel = st.multiselect(
                "Categoria", options=dest_categorias, default=[],
                key="dest_cat_filter"
            )
        with col_dest_tier:
            dest_tiers = sorted(df_fundos["tier"].dropna().unique().tolist())
            dest_tier_sel = st.multiselect(
                "Tier", options=dest_tiers, default=[],
                key="dest_tier_filter"
            )

        # Aplicar filtros ao universo de fundos
        df_fundos_dest = df_fundos.copy()
        if dest_cat_sel:
            df_fundos_dest = df_fundos_dest[df_fundos_dest["categoria"].isin(dest_cat_sel)]
        if dest_tier_sel:
            df_fundos_dest = df_fundos_dest[df_fundos_dest["tier"].isin(dest_tier_sel)]

        all_cnpjs_destaques = tuple(set(df_fundos_dest["cnpj_norm"].dropna().tolist()))
        df_cotas_all = carregar_cotas_fundos(
            tuple(set(all_cnpjs_destaques) | set(BENCHMARK_CNPJS.values())), meses=120
        )

        if df_cotas_all.empty:
            st.warning("Sem dados de cotas para gerar destaques.")
        else:
            cnpj_to_name = dict(zip(df_fundos["cnpj_norm"], df_fundos["nome"]))
            bench_cnpj_to_name_d = {v: k for k, v in BENCHMARK_CNPJS.items()}

            # Calcular retornos para cada janela
            janelas_destaques = {
                "MTD": None,  # calculado separado
                "YTD": None,  # calculado separado
                "3M": 63,
                "6M": 126,
                "12M": 252,
                "24M": 504,
                "36M": 756,
                "60M": 1260,
            }

            # ── ABORDAGEM CORRETA: usar retorno_diario (pct_change) e compor ──
            # Pivotar retornos diários (NÃO cotas) — sem ffill para não contaminar
            pivot_ret = df_cotas_all.pivot_table(
                index="data", columns="cnpj_fundo", values="retorno_diario"
            ).sort_index()
            # Filtrar retornos diários absurdos (>30% num único dia → provavelmente erro/reset)
            pivot_ret = pivot_ret.where(pivot_ret.abs() <= 0.30)

            if pivot_ret.empty:
                st.warning("Sem dados de cotas suficientes.")
            else:
                max_date = pivot_ret.index.max()
                results = {}

                # Helper: compor retornos diários em janela → retorno acumulado %
                def _compound_returns(ret_slice):
                    """Recebe slice do pivot_ret, retorna Series com retorno acumulado (%) por fundo."""
                    # Exigir pelo menos 60% dos dias com dados para considerar válido
                    min_valid = max(2, int(len(ret_slice) * 0.6))
                    valid_mask = ret_slice.notna().sum() >= min_valid
                    comp = (1 + ret_slice.fillna(0)).prod() - 1
                    # Zerar fundos com dados insuficientes
                    comp[~valid_mask] = np.nan
                    return comp * 100

                # MTD: retornos do mês atual (compostos)
                month_mask = (pivot_ret.index.month == max_date.month) & (pivot_ret.index.year == max_date.year)
                month_slice = pivot_ret.loc[month_mask]
                if len(month_slice) >= 1:
                    results["MTD"] = _compound_returns(month_slice)

                # YTD: retornos do ano atual (compostos)
                year_mask = pivot_ret.index.year == max_date.year
                year_slice = pivot_ret.loc[year_mask]
                if len(year_slice) >= 1:
                    results["YTD"] = _compound_returns(year_slice)

                # Janelas fixas: últimos N dias úteis
                for label, dias in janelas_destaques.items():
                    if dias is None:
                        continue
                    if len(pivot_ret) < dias:
                        continue
                    window_slice = pivot_ret.iloc[-dias:]
                    results[label] = _compound_returns(window_slice)

                if not results:
                    st.warning("Dados insuficientes para calcular retornos.")
                else:
                    # Montar DataFrame consolidado
                    df_ret_all = pd.DataFrame(results)
                    # Filtrar: só fundos com dados (excluir NaN em todas colunas)
                    df_ret_all = df_ret_all.dropna(how="all")
                    # Sanity check: excluir retornos absurdos (>500% ou <-99%)
                    for col in df_ret_all.columns:
                        if col == "nome":
                            continue
                        df_ret_all.loc[df_ret_all[col].abs() > 500, col] = np.nan

                    # Separar fundos da carteira vs benchmarks
                    fund_cnpjs_d = set(df_ret_all.index) - set(BENCHMARK_CNPJS.values())

                    # Adicionar nomes
                    df_ret_all["nome"] = df_ret_all.index.map(
                        lambda x: cnpj_to_name.get(x, bench_cnpj_to_name_d.get(x, x[:14]))
                    )

                    # Calcular estatísticas do universo
                    df_funds_only = df_ret_all.loc[df_ret_all.index.isin(fund_cnpjs_d)]

                    # ── 1. Resumo do Universo ──
                    st.markdown('<div class="tag-section-title">Desempenho do Universo de Fundos RV</div>', unsafe_allow_html=True)
                    filtro_desc = ""
                    if dest_cat_sel:
                        filtro_desc += f" | Cat: {', '.join(dest_cat_sel)}"
                    if dest_tier_sel:
                        filtro_desc += f" | Tier: {', '.join(str(t) for t in dest_tier_sel)}"
                    st.caption(f"Amostra de {len(df_funds_only)} fundos de acoes. Data ref: {max_date.strftime('%d/%m/%Y')}.{filtro_desc}")

                    # Tabela de resumo (tipo o PDF)
                    summary_rows = []
                    for col in df_ret_all.columns:
                        if col == "nome":
                            continue
                        fund_vals = df_funds_only[col].dropna()
                        if fund_vals.empty:
                            continue
                        summary_rows.append({
                            "": f"Media Top 20",
                            col: f"{fund_vals.nlargest(20).mean():.1f}%",
                        })

                    # Construir tabela HTML profissional com resumo
                    janelas_disp = [c for c in results.keys() if c in df_ret_all.columns]
                    bench_names = list(BENCHMARK_CNPJS.keys())

                    # Retornos do IBOVESPA por janela (referência para colorir)
                    ibov_cnpj_d = BENCHMARK_CNPJS.get("IBOVESPA", "")
                    ibov_rets = {}
                    for col in janelas_disp:
                        if ibov_cnpj_d and ibov_cnpj_d in df_ret_all.index and col in df_ret_all.columns:
                            v = df_ret_all.loc[ibov_cnpj_d, col]
                            ibov_rets[col] = v if pd.notna(v) else 0.0
                        else:
                            ibov_rets[col] = 0.0

                    def _ibov_color(val, col):
                        """Verde se bateu IBOV, vermelho se perdeu. Cores para tema dark."""
                        ibov_v = ibov_rets.get(col, 0.0)
                        diff = val - ibov_v
                        if diff >= 0:
                            return "background: rgba(107,222,151,0.15); color: #6BDE97;"
                        else:
                            return "background: rgba(237,90,110,0.15); color: #ED5A6E;"

                    # Build summary table HTML
                    th_cells = "".join(f'<th style="padding:10px 12px; text-align:right; color:{TAG_OFFWHITE}; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.8px;">{j}</th>' for j in janelas_disp)
                    summary_html = f"""
                    <div style="border-radius:12px; overflow:hidden; border:1px solid {BORDER_COLOR}; background:{CARD_BG}; margin:8px 0 24px 0;">
                    <table style="width:100%; border-collapse:collapse; font-family:Tahoma,sans-serif;">
                    <thead><tr style="background:{TAG_BG_CARD}; border-bottom:1px solid {BORDER_COLOR};">
                        <th style="padding:10px 14px; text-align:left; color:{TAG_OFFWHITE}; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; min-width:180px;">—</th>
                        {th_cells}
                    </tr></thead><tbody>"""

                    # Rows: Média Top 20, Benchmarks, Mediana, Média, Média Bottom 20
                    stat_rows = []
                    for label_stat, calc_fn in [
                        ("Media Top 20", lambda s: s.nlargest(min(20, len(s))).mean()),
                    ]:
                        stat_rows.append((label_stat, calc_fn, TAG_LARANJA))

                    # Benchmarks (BENCHMARK_CNPJS: name → cnpj)
                    for b_name, b_cnpj in BENCHMARK_CNPJS.items():
                        if b_cnpj in df_ret_all.index:
                            stat_rows.append((b_name, None, "#58C6F5"))

                    stat_rows.extend([
                        ("Mediana", lambda s: s.median(), TEXT_COLOR),
                        ("Media", lambda s: s.mean(), TEXT_MUTED),
                        ("Media Bottom 20", lambda s: s.nsmallest(min(20, len(s))).mean(), "#ED5A6E"),
                    ])

                    for sr_label, sr_fn, sr_color in stat_rows:
                        cells = ""
                        for col in janelas_disp:
                            if sr_fn is not None:
                                vals = df_funds_only[col].dropna()
                                if vals.empty:
                                    cells += f'<td style="padding:8px 12px; text-align:right; color:{TEXT_MUTED};">—</td>'
                                    continue
                                v = sr_fn(vals)
                            else:
                                # Benchmark: BENCHMARK_CNPJS maps name→cnpj
                                b_cnpj = [cnpj_v for name_k, cnpj_v in BENCHMARK_CNPJS.items() if name_k == sr_label]
                                if b_cnpj and b_cnpj[0] in df_ret_all.index and col in df_ret_all.columns:
                                    v = df_ret_all.loc[b_cnpj[0], col]
                                    if pd.isna(v):
                                        cells += f'<td style="padding:8px 12px; text-align:right; color:{TEXT_MUTED};">—</td>'
                                        continue
                                else:
                                    cells += f'<td style="padding:8px 12px; text-align:right; color:{TEXT_MUTED};">—</td>'
                                    continue
                            neg = "color:#ED5A6E;" if v < 0 else ""
                            cells += f'<td style="padding:8px 12px; text-align:right; font-weight:600; font-size:13px; {neg} color:{sr_color};">{v:.1f}%</td>'
                        summary_html += f'<tr style="border-bottom:1px solid {BORDER_COLOR}60;"><td style="padding:8px 14px; font-weight:600; font-size:13px; color:{sr_color};">{sr_label}</td>{cells}</tr>'

                    summary_html += "</tbody></table></div>"
                    st.html(summary_html)

                    # ── 2. Seletor de janela para ranking ──
                    janela_rank = st.selectbox(
                        "Ordenar ranking por:", janelas_disp,
                        index=min(0, len(janelas_disp) - 1),
                        key="dest_janela"
                    )

                    # Destacar fundos selecionados na carteira
                    sel_cnpjs_set = set(cnpjs_sel)

                    # ── 3. Ranking Completo (com scroll) ──
                    n_fundos_total = len(df_funds_only[janela_rank].dropna())
                    opcoes_qtd = [20, 50, 100, n_fundos_total]
                    opcoes_labels = ["Top 20", "Top 50", "Top 100", f"Todos ({n_fundos_total})"]
                    # Remover opções > total de fundos
                    opcoes_filtradas = [(lbl, qtd) for lbl, qtd in zip(opcoes_labels, opcoes_qtd) if qtd <= n_fundos_total or qtd == n_fundos_total]
                    if not opcoes_filtradas:
                        opcoes_filtradas = [(f"Todos ({n_fundos_total})", n_fundos_total)]

                    col_rank_opt1, col_rank_opt2 = st.columns([1, 3])
                    with col_rank_opt1:
                        vis_label = st.selectbox(
                            "Exibir:", [lbl for lbl, _ in opcoes_filtradas],
                            index=0, key="dest_n_fundos"
                        )
                        n_show = dict(opcoes_filtradas)[vis_label]

                    # Helper: render benchmark rows for ranking table
                    def _render_bench_rows(janelas_disp_inner, janela_rank_inner):
                        bench_html = ""
                        for b_name, b_cnpj in BENCHMARK_CNPJS.items():
                            if b_cnpj not in df_ret_all.index:
                                continue
                            bench_html += f'<tr style="background:rgba(88,198,245,0.06);border-bottom:2px solid {BORDER_COLOR};position:sticky;top:0;z-index:2;">'
                            bench_html += f'<td style="padding:6px 10px;text-align:center;color:#58C6F5;font-size:10px;font-weight:700;">▸</td>'
                            bench_html += f'<td style="padding:6px 10px;font-size:12px;color:#58C6F5;font-weight:700;white-space:nowrap;">{b_name}</td>'
                            for jcol in janelas_disp_inner:
                                v = df_ret_all.loc[b_cnpj, jcol] if jcol in df_ret_all.columns else np.nan
                                if pd.isna(v):
                                    bench_html += f'<td style="padding:6px 8px;text-align:right;color:{TEXT_MUTED};font-size:11px;">—</td>'
                                else:
                                    neg = "color:#ED5A6E;" if v < 0 else ""
                                    bold = "font-weight:700;" if jcol == janela_rank_inner else ""
                                    bench_html += f'<td style="padding:6px 8px;text-align:right;font-size:11px;color:#58C6F5;{neg}{bold}">{v:.1f}%</td>'
                            bench_html += '</tr>'
                        return bench_html

                    # Melhores (top N)
                    st.markdown(f'<div class="tag-section-title" style="color:#6BDE97;">Ranking Melhores — {janela_rank} <span style="color:{TEXT_MUTED};font-size:11px;font-weight:400;">({n_show} fundos) | 🟢 acima do IBOV | 🔴 abaixo do IBOV</span></div>', unsafe_allow_html=True)
                    topN = df_funds_only.nlargest(n_show, janela_rank)[[janela_rank, "nome"]].copy()
                    topN = topN.dropna(subset=[janela_rank])

                    # Wrapper com scroll
                    max_h = "600px" if n_show > 25 else "none"
                    top_html = f'<div style="border-radius:12px; border:1px solid {BORDER_COLOR}; background:{CARD_BG}; max-height:{max_h}; overflow-y:auto;">'
                    top_html += f'<table style="width:100%; border-collapse:collapse; font-family:Tahoma,sans-serif;">'
                    top_html += f'<thead><tr style="background:{TAG_BG_CARD};border-bottom:1px solid {BORDER_COLOR};position:sticky;top:0;z-index:3;">'
                    top_html += f'<th style="padding:8px 10px;color:{TAG_OFFWHITE};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;width:30px;background:{TAG_BG_CARD};">#</th>'
                    top_html += f'<th style="padding:8px 10px;color:{TAG_OFFWHITE};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;background:{TAG_BG_CARD};">Fundo</th>'

                    for jcol in janelas_disp:
                        bold = "font-weight:800;" if jcol == janela_rank else ""
                        top_html += f'<th style="padding:8px 8px;color:{TAG_OFFWHITE};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;text-align:right;{bold}background:{TAG_BG_CARD};">{jcol}</th>'
                    top_html += '</tr></thead><tbody>'

                    # Benchmark rows first (reference — sticky)
                    top_html += _render_bench_rows(janelas_disp, janela_rank)

                    for rank_i, (cnpj_row, row) in enumerate(topN.iterrows()):
                        is_selected = cnpj_row in sel_cnpjs_set
                        bg = f"background:rgba(107,222,151,0.10);" if is_selected else ""
                        name_style = f"color:{TAG_LARANJA};font-weight:700;" if is_selected else f"color:{TEXT_COLOR};"
                        zb = "background:{TAG_BG_CARD_ALT};" if rank_i % 2 == 1 and not is_selected else ""
                        top_html += f'<tr style="{bg}{zb}border-bottom:1px solid {TAG_VERMELHO}20;">'
                        top_html += f'<td style="padding:6px 10px;text-align:center;color:{TEXT_MUTED};font-size:11px;font-weight:600;">{rank_i+1}</td>'
                        nome_short = row["nome"][:40] + "…" if len(row["nome"]) > 40 else row["nome"]
                        top_html += f'<td style="padding:6px 10px;font-size:12px;{name_style}white-space:nowrap;">{nome_short}</td>'

                        for jcol in janelas_disp:
                            v = df_ret_all.loc[cnpj_row, jcol] if cnpj_row in df_ret_all.index and jcol in df_ret_all.columns else np.nan
                            if pd.isna(v):
                                top_html += f'<td style="padding:6px 8px;text-align:right;color:{TEXT_MUTED};font-size:11px;">—</td>'
                            else:
                                qstyle = _ibov_color(v, jcol)
                                neg = "color:#ED5A6E;" if v < 0 else ""
                                bold = "font-weight:700;" if jcol == janela_rank else ""
                                top_html += f'<td style="padding:6px 8px;text-align:right;font-size:11px;{qstyle}{neg}{bold}border-radius:4px;">{v:.1f}%</td>'
                        top_html += '</tr>'
                    top_html += '</tbody></table></div>'
                    st.html(top_html)

                    # Piores (bottom N)
                    st.markdown(f'<div class="tag-section-title" style="color:#ED5A6E;">Ranking Piores — {janela_rank}</div>', unsafe_allow_html=True)
                    botN = df_funds_only.nsmallest(n_show, janela_rank)[[janela_rank, "nome"]].copy()
                    botN = botN.dropna(subset=[janela_rank])

                    bot_html = f'<div style="border-radius:12px; border:1px solid {BORDER_COLOR}; background:{CARD_BG}; max-height:{max_h}; overflow-y:auto;">'
                    bot_html += f'<table style="width:100%; border-collapse:collapse; font-family:Tahoma,sans-serif;">'
                    bot_html += f'<thead><tr style="background:{TAG_BG_CARD};border-bottom:1px solid {BORDER_COLOR};position:sticky;top:0;z-index:3;">'
                    bot_html += f'<th style="padding:8px 10px;color:{TAG_OFFWHITE};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;width:30px;background:{TAG_BG_CARD};">#</th>'
                    bot_html += f'<th style="padding:8px 10px;color:{TAG_OFFWHITE};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;background:{TAG_BG_CARD};">Fundo</th>'
                    for jcol in janelas_disp:
                        bold = "font-weight:800;" if jcol == janela_rank else ""
                        bot_html += f'<th style="padding:8px 8px;color:{TAG_OFFWHITE};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;text-align:right;{bold}background:{TAG_BG_CARD};">{jcol}</th>'
                    bot_html += '</tr></thead><tbody>'

                    # Benchmark rows first (reference)
                    bot_html += _render_bench_rows(janelas_disp, janela_rank)

                    for rank_i, (cnpj_row, row) in enumerate(botN.iterrows()):
                        is_selected = cnpj_row in sel_cnpjs_set
                        bg = f"background:rgba(237,90,110,0.10);" if is_selected else ""
                        name_style = f"color:{TAG_LARANJA};font-weight:700;" if is_selected else f"color:{TEXT_COLOR};"
                        zb = "background:{TAG_BG_CARD_ALT};" if rank_i % 2 == 1 and not is_selected else ""
                        bot_html += f'<tr style="{bg}{zb}border-bottom:1px solid {TAG_VERMELHO}20;">'
                        bot_html += f'<td style="padding:6px 10px;text-align:center;color:{TEXT_MUTED};font-size:11px;font-weight:600;">{rank_i+1}</td>'
                        nome_short = row["nome"][:40] + "…" if len(row["nome"]) > 40 else row["nome"]
                        bot_html += f'<td style="padding:6px 10px;font-size:12px;{name_style}white-space:nowrap;">{nome_short}</td>'

                        for jcol in janelas_disp:
                            v = df_ret_all.loc[cnpj_row, jcol] if cnpj_row in df_ret_all.index and jcol in df_ret_all.columns else np.nan
                            if pd.isna(v):
                                bot_html += f'<td style="padding:6px 8px;text-align:right;color:{TEXT_MUTED};font-size:11px;">—</td>'
                            else:
                                qstyle = _ibov_color(v, jcol)
                                neg = "color:#ED5A6E;" if v < 0 else ""
                                bold = "font-weight:700;" if jcol == janela_rank else ""
                                bot_html += f'<td style="padding:6px 8px;text-align:right;font-size:11px;{qstyle}{neg}{bold}border-radius:4px;">{v:.1f}%</td>'
                        bot_html += '</tr>'
                    bot_html += '</tbody></table></div>'
                    st.html(bot_html)

                    # ── 4. Posição dos fundos selecionados no ranking ──
                    st.markdown('<div class="tag-section-title">Posicao dos Fundos Selecionados no Ranking</div>', unsafe_allow_html=True)

                    ranking_full = df_funds_only[janela_rank].dropna().rank(ascending=False, method="min")
                    total_ranked = len(ranking_full)

                    sel_rank_rows = []
                    for nome in fundos_sel:
                        cnpj = nome_cnpj_map[nome]
                        if cnpj in ranking_full.index:
                            pos = int(ranking_full.loc[cnpj])
                            pctl = (1 - pos / total_ranked) * 100
                            ret_val = df_funds_only.loc[cnpj, janela_rank] if cnpj in df_funds_only.index else np.nan

                            # Quartil label
                            if pctl >= 75:
                                q_label = "Q1"
                                q_color = "#6BDE97"
                            elif pctl >= 50:
                                q_label = "Q2"
                                q_color = "#FFBB00"
                            elif pctl >= 25:
                                q_label = "Q3"
                                q_color = "#FF8853"
                            else:
                                q_label = "Q4"
                                q_color = "#ED5A6E"

                            sel_rank_rows.append({
                                "nome": nome, "pos": pos, "total": total_ranked,
                                "pctl": pctl, "ret": ret_val, "q_label": q_label, "q_color": q_color,
                            })

                    if sel_rank_rows:
                        sel_cols = st.columns(min(len(sel_rank_rows), 4))
                        for i, sr in enumerate(sel_rank_rows):
                            with sel_cols[i % len(sel_cols)]:
                                ret_str = f"{sr['ret']:.1f}%" if pd.notna(sr['ret']) else "—"
                                st.markdown(f"""
                                <div class="tag-metric-card" style="text-align:center;">
                                    <div class="label">{sr['nome'][:25]}</div>
                                    <div class="value" style="font-size:2rem;">{sr['pos']}<span style="font-size:0.9rem;color:{TEXT_MUTED};">/{sr['total']}</span></div>
                                    <div style="margin-top:8px;display:flex;justify-content:center;gap:12px;align-items:center;">
                                        <span style="background:{sr['q_color']}20;color:{sr['q_color']};padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;">{sr['q_label']}</span>
                                        <span style="color:{TEXT_MUTED};font-size:12px;">{ret_str} ({janela_rank})</span>
                                    </div>
                                    <div style="margin-top:8px;">
                                        <div style="background:{BORDER_COLOR};border-radius:4px;height:6px;overflow:hidden;">
                                            <div style="width:{sr['pctl']:.0f}%;height:100%;background:linear-gradient(90deg,{sr['q_color']},{TAG_LARANJA});border-radius:4px;"></div>
                                        </div>
                                        <div style="font-size:10px;color:{TEXT_MUTED};margin-top:3px;">Percentil {sr['pctl']:.0f}%</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                    # ── 5. Distribuição de Retornos (histograma) ──
                    if janela_rank in df_funds_only.columns:
                        st.markdown(f'<div class="tag-section-title">Distribuicao de Retornos — {janela_rank}</div>', unsafe_allow_html=True)

                        ret_vals = df_funds_only[janela_rank].dropna()
                        fig_hist = go.Figure()
                        fig_hist.add_trace(go.Histogram(
                            x=ret_vals, nbinsx=30,
                            marker=dict(color=_hex_to_rgba(TAG_LARANJA, 0.6), line=dict(width=1, color=TAG_LARANJA)),
                            hovertemplate="Retorno: %{x:.1f}%<br>Fundos: %{y}<extra></extra>",
                        ))

                        # Marcar fundos selecionados
                        for nome in fundos_sel:
                            cnpj = nome_cnpj_map[nome]
                            if cnpj in ret_vals.index:
                                v = ret_vals.loc[cnpj]
                                fig_hist.add_vline(x=v, line_dash="dash", line_color=TAG_CHART_COLORS[0], line_width=2,
                                                   annotation_text=nome.split()[0], annotation_position="top",
                                                   annotation_font_color=TEXT_COLOR, annotation_font_size=10)

                        # Marcar benchmarks
                        for b_name, b_cnpj in BENCHMARK_CNPJS.items():
                            if b_cnpj in df_ret_all.index and janela_rank in df_ret_all.columns:
                                bv = df_ret_all.loc[b_cnpj, janela_rank]
                                if pd.notna(bv):
                                    fig_hist.add_vline(x=bv, line_dash="dot", line_color="#58C6F5", line_width=1.5,
                                                       annotation_text=b_name.split("(")[0].strip()[:10],
                                                       annotation_position="top",
                                                       annotation_font_color=TEXT_MUTED, annotation_font_size=9)

                        _chart_layout(fig_hist, "", height=350, y_title="Qtd. Fundos", y_suffix="")
                        st.plotly_chart(fig_hist, use_container_width=True)


if __name__ == "__main__":
    main()
