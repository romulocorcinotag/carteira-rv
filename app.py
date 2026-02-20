import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import base64
from collections import Counter

from data_loader import (
    carregar_todos_dados, carregar_fundos_rv,
    carregar_cotas_fundos, carregar_universo_stats,
    carregar_fundamentals_explosao, BENCHMARK_CNPJS,
)
from sector_map import classificar_setor
import pdf_parser

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
TAG_BG_DARK = "#1E0C14"
TAG_BG_CARD = "#2D1722"
TAG_BG_CARD_ALT = "#361D2A"
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
           SIDEBAR — sempre visível, sem botão de fechar
        ══════════════════════════════════════════════════ */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {TAG_BG_DARK} 0%, #150812 100%) !important;
            border-right: 2px solid {TAG_VERMELHO}40;
            min-width: 270px !important;
            max-width: 290px !important;
        }}
        /* Impedir collapse: esconder botão de fechar e forçar visibilidade */
        [data-testid="stSidebar"][aria-expanded="false"] {{
            display: block !important;
            min-width: 270px !important;
            max-width: 290px !important;
            width: 270px !important;
            transform: none !important;
            margin-left: 0 !important;
        }}
        button[kind="headerNoPadding"] {{
            display: none !important;
        }}
        [data-testid="stSidebarCollapsedControl"] {{
            display: none !important;
        }}
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            padding-top: 0 !important;
        }}
        /* Sidebar logo */
        .sidebar-logo {{
            text-align: center;
            padding: 36px 24px 12px 24px;
        }}
        .sidebar-logo img {{
            width: 170px;
            height: auto;
            margin-bottom: 6px;
            filter: drop-shadow(0 2px 8px rgba(99,13,36,0.3));
        }}
        .sidebar-logo .app-name {{
            font-size: 0.95rem;
            color: {TAG_LARANJA};
            margin-top: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        .sidebar-logo .bar {{
            width: 60px;
            height: 2px;
            background: linear-gradient(90deg, transparent, {TAG_LARANJA}, transparent);
            margin: 10px auto 0;
        }}
        /* Sidebar radio — esconder label "Navegacao" */
        [data-testid="stSidebar"] .stRadio [data-testid="stWidgetLabel"] {{
            display: none !important;
        }}
        [data-testid="stSidebar"] .stRadio > div {{
            gap: 4px !important;
            padding: 0 8px !important;
        }}
        [data-testid="stSidebar"] .stRadio label {{
            padding: 12px 14px !important;
            border-radius: 8px !important;
            cursor: pointer !important;
            font-size: 0.88rem !important;
            font-weight: 500 !important;
            color: {TEXT_MUTED} !important;
            transition: all 0.2s ease !important;
            margin: 0 !important;
            border: 1px solid transparent !important;
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
        }}
        [data-testid="stSidebar"] .stRadio label:hover {{
            background: {TAG_VERMELHO}15 !important;
            color: {TAG_OFFWHITE} !important;
        }}
        /* Active radio item — sutil bg + texto claro */
        [data-testid="stSidebar"] .stRadio label[data-checked="true"],
        [data-testid="stSidebar"] .stRadio [aria-checked="true"] {{
            background: {TAG_VERMELHO}20 !important;
            color: {TAG_OFFWHITE} !important;
            font-weight: 700 !important;
            border-color: {TAG_VERMELHO}35 !important;
        }}
        /* Radio circles — visíveis, estilo dot laranja */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label > div:first-child {{
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            min-width: 18px !important;
            width: 18px !important;
            height: 18px !important;
        }}
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label > div:first-child > div {{
            width: 16px !important;
            height: 16px !important;
            border-radius: 50% !important;
            border: 2px solid {TEXT_MUTED}80 !important;
            background: transparent !important;
            position: relative !important;
            transition: all 0.2s ease !important;
        }}
        /* Active radio dot — laranja preenchido */
        [data-testid="stSidebar"] .stRadio [aria-checked="true"] > div:first-child > div,
        [data-testid="stSidebar"] .stRadio label[data-checked="true"] > div:first-child > div {{
            border-color: {TAG_LARANJA} !important;
            background: {TAG_LARANJA} !important;
            box-shadow: 0 0 8px {TAG_LARANJA}60 !important;
        }}
        /* Sidebar dividers */
        [data-testid="stSidebar"] hr {{
            border-color: {TAG_VERMELHO}20 !important;
            margin: 12px 16px !important;
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


PAGINAS = ["Carteira", "Comparativo", "Performance", "Destaques", "Explosão"]
PAGINAS_ICONS = ["📊", "🔀", "📈", "🏆", "💥"]


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

        # Data atualização no rodapé da sidebar — estilo info panel
        data_atualizacao = _get_data_atualizacao()

        # Contar fundos no parquet
        try:
            _data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            _pos_path = os.path.join(_data_dir, "posicoes_consolidado.parquet")
            if os.path.exists(_pos_path):
                import pyarrow.parquet as pq
                _pf = pq.read_table(_pos_path, columns=["cnpj_fundo"])
                _n_fundos = _pf.column("cnpj_fundo").to_pylist()
                _n_fundos = len(set(_n_fundos))
            else:
                _n_fundos = "—"
        except Exception:
            _n_fundos = "—"

        st.markdown(f"""
        <div style="text-align: center; padding: 14px 16px; margin: 0 8px;
                    background: linear-gradient(135deg, {TAG_VERMELHO}18 0%, {TAG_BG_CARD} 100%);
                    border-radius: 10px;
                    border: 1px solid {TAG_VERMELHO}25;">
            <div style="font-size: 0.6rem; color: {TEXT_MUTED}; text-transform: uppercase;
                        letter-spacing: 2px; font-weight: 600; margin-bottom: 6px;">
                📅 Dados atualizados até</div>
            <div style="font-size: 1rem; color: {TAG_LARANJA}; font-weight: 700;">
                {data_atualizacao}</div>
            <div style="width: 40px; height: 1px; background: {TAG_VERMELHO}30;
                        margin: 8px auto;"></div>
            <div style="font-size: 0.65rem; color: {TEXT_MUTED}; line-height: 1.6;">
                📊 Base: <b style="color:{TAG_OFFWHITE}">{_n_fundos}</b> fundos CVM<br>
                🗂️ Fonte: XML / BTG Pactual
            </div>
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
        orientation="h", yanchor="bottom", y=1.0,
        xanchor="left", x=0,
        font=dict(size=10, color=TEXT_MUTED, family="Tahoma, sans-serif"),
        bgcolor="rgba(0,0,0,0)",
    ) if legend_h else dict(
        font=dict(size=10, color=TEXT_MUTED, family="Tahoma, sans-serif")
    )

    # Margem superior maior quando há título + legenda horizontal
    _mt = 70 if title and legend_h else (50 if title else 30)

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
        margin=dict(l=50, r=16, t=_mt, b=margin_b),
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
        layout_kwargs["title"] = dict(
            text=title,
            font=dict(size=14, color=TAG_LARANJA, family="Tahoma, sans-serif"),
            y=0.98, yanchor="top",
        )
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
        line=dict(width=2.5, color="#58C6F5"),
        marker=dict(size=5, color="#58C6F5"),
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

    # ── Página atual (via sidebar) ──
    pagina = st.session_state.get("pagina", "Carteira")

    # Explosão tem fluxo próprio — sem filtros de Categoria/Tier/Fundo
    if pagina == "Explosão":
        _render_explosao(df_fundos, df_posicoes)
        return

    # ── Filtros (para demais páginas) ──
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
                        line=dict(width=2.5, color="#58C6F5"),
                        marker=dict(size=5, color="#58C6F5"),
                        hovertemplate="<b>HHI</b><br>%{x|%d/%m/%Y}: %{y:.0f}<br>N ativos: %{customdata[0]}<br>Top1: %{customdata[1]:.1f}%<extra></extra>",
                        customdata=list(zip(_n_ativos_hist, _top1_hist)),
                    ))

                    # Faixas calibradas para fundos de ações BR
                    _faixas = [
                        (0, 450, "rgba(107,222,151,0.05)", "#6BDE97", "Diversificado"),
                        (450, 700, "rgba(255,187,0,0.05)", "#FFBB00", "Moderado"),
                        (700, 1200, "rgba(255,187,0,0.03)", "#FF8853", "Concentrado"),
                        (1200, max(max(_hhi_vals) * 1.15, 1500), "rgba(255,136,83,0.03)", "#FF8853", "Muito concentrado"),
                    ]
                    for _y0, _y1, _fill, _lcolor, _label in _faixas:
                        fig_hhi.add_hrect(
                            y0=_y0, y1=_y1,
                            fillcolor=_fill,
                            line_width=0,
                        )
                    # Linhas de referência
                    for _yval, _lcolor, _label in [(450, "#6BDE97", "Diversificado"), (700, "#FFBB00", "Moderado"), (1200, "#FF8853", "Concentrado")]:
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
                        marker_color=_hex_to_rgba(TAG_LARANJA, 0.7),
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

    # ══════════════════════════════════════════════════════════════════════
    # PÁGINA: EXPLOSÃO (Decomposição de fundos TAG em ações subjacentes)
    # ══════════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────────────────────
# EXPLOSÃO — Função dedicada (fora do main para manter legibilidade)
# ──────────────────────────────────────────────────────────────────────────────

# ── ETF → Índice B3: mapeamento de tickers de ETFs para códigos de índice na B3 ──
_ETF_INDEX_MAP = {
    "BOVA11": "IBOV",
    "SMAL11": "SMLL",
    "BOVV11": "IBOV",
    "BOVB11": "IBOV",
    "DIVO11": "IDIV",
    "BRAX11": "IBRX",
    "PIBB11": "IBXX",
    "MATB11": "IMAT",
    "FIND11": "IFNC",
    "ISUS11": "ISEE",
    "ECOO11": "ICO2",
    "GOVE11": "IGCT",
    "UTIP11": "UTIL",
}


@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_etf_composition(ticker: str) -> dict:
    """Busca composição de um ETF via API da B3 (índice subjacente).
    Retorna dict {ticker_acao: peso_pct, ...} ou dict vazio se não disponível.
    """
    idx_code = _ETF_INDEX_MAP.get(ticker.upper())
    if not idx_code:
        return {}

    try:
        import requests, json, base64
        payload = json.dumps({
            "language": "pt-br",
            "pageNumber": 1,
            "pageSize": 200,
            "index": idx_code,
            "action": "3",
        })
        encoded = base64.b64encode(payload.encode()).decode()
        url = f"https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/{encoded}"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return {}
        data = r.json()
        results = data.get("results")
        if not results:
            return {}
        composition = {}
        for item in results:
            cod = item.get("cod", "").strip()
            part_str = item.get("part", "0").replace(",", ".")
            try:
                part = float(part_str)
            except (ValueError, TypeError):
                part = 0.0
            if cod and part > 0:
                composition[cod] = part
        return composition
    except Exception:
        return {}


@st.cache_data(ttl=600)
def _compute_historical_explosion(
    _portfolio_key: str,
    portfolio_cnpjs: list,
    portfolio_pesos: list,
    foco_map_items: list,
    mono_ativo_items: list,
    df_posicoes_serialized: bytes,
    direct_stock_items: list = None,
    etf_composition_json: str = None,
) -> pd.DataFrame:
    """Computa a explosão histórica: para cada mês em posicoes_consolidado,
    aplica os pesos do PDF (proxy fixo) a cada fundo subjacente.
    Inclui ações diretas e ETFs explodidos como peso fixo em todos os meses.

    Retorna DataFrame com: data, ativo, setor, exposicao_pct
    """
    import io as _io
    import json as _json

    df_posicoes = pd.read_parquet(_io.BytesIO(df_posicoes_serialized))
    df_posicoes["data"] = pd.to_datetime(df_posicoes["data"])
    foco_map = dict(foco_map_items)
    mono_map = dict(mono_ativo_items)
    direct_stocks = dict(direct_stock_items) if direct_stock_items else {}
    etf_comps = _json.loads(etf_composition_json) if etf_composition_json else {}

    # Todas as datas disponíveis (para replicar itens fixos em cada mês)
    all_dates = sorted(df_posicoes["data"].unique())

    records = []

    # Parte 1: Fundos investidos (via CVM/XML)
    for cnpj_raw, peso_pct in zip(portfolio_cnpjs, portfolio_pesos):
        if not cnpj_raw:
            continue
        peso = peso_pct / 100.0

        # Caso especial: fundo mono-ativo
        if cnpj_raw in mono_map:
            ticker_mono = mono_map[cnpj_raw]
            setor_mono = classificar_setor(ticker_mono)
            for dt in all_dates:
                records.append({
                    "data": dt,
                    "ativo": ticker_mono,
                    "setor": setor_mono,
                    "exposicao_pct": peso * 100.0,
                })
            continue

        cnpj_busca = foco_map.get(cnpj_raw, cnpj_raw)

        df_fundo = df_posicoes[df_posicoes["cnpj_fundo"] == cnpj_busca]
        if df_fundo.empty:
            df_fundo = df_posicoes[df_posicoes["cnpj_fundo"] == cnpj_raw]
        if df_fundo.empty:
            continue

        for dt, grp in df_fundo.groupby("data"):
            for _, row in grp.iterrows():
                records.append({
                    "data": dt,
                    "ativo": row["ativo"],
                    "setor": row.get("setor", classificar_setor(row["ativo"])),
                    "exposicao_pct": peso * (row.get("pct_pl", 0) or 0),
                })

    # Parte 2: Ações diretas (peso fixo em todos os meses)
    for ticker_dir, peso_dir in direct_stocks.items():
        # Se é ETF com composição disponível, explodir
        if ticker_dir in etf_comps and etf_comps[ticker_dir]:
            comp = etf_comps[ticker_dir]
            for ticker_idx, peso_idx in comp.items():
                exp = peso_dir * (peso_idx / 100.0)
                setor_idx = classificar_setor(ticker_idx)
                for dt in all_dates:
                    records.append({
                        "data": dt,
                        "ativo": ticker_idx,
                        "setor": setor_idx,
                        "exposicao_pct": exp,
                    })
        else:
            # Ação direta simples
            setor_dir = classificar_setor(ticker_dir)
            for dt in all_dates:
                records.append({
                    "data": dt,
                    "ativo": ticker_dir,
                    "setor": setor_dir,
                    "exposicao_pct": peso_dir,
                })

    if not records:
        return pd.DataFrame(columns=["data", "ativo", "setor", "exposicao_pct"])

    df = pd.DataFrame(records)
    # Agregar por (data, ativo) caso múltiplos fundos tenham a mesma ação
    df = df.groupby(["data", "ativo", "setor"]).agg(
        exposicao_pct=("exposicao_pct", "sum")
    ).reset_index()
    return df.sort_values("data")


@st.cache_data(ttl=3600, show_spinner="Buscando dados fundamentalistas...")
def _fetch_fundamentals_yfinance(tickers_sa: tuple) -> pd.DataFrame:
    """Busca dados fundamentalistas do yfinance para uma lista de tickers .SA.
    Retorna DataFrame wide (1 linha por ticker) com múltiplos e marketCap.
    """
    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame()

    _CAMPOS = [
        "trailingPE", "forwardPE", "priceToBook", "dividendYield",
        "returnOnEquity", "profitMargins", "beta", "marketCap",
        "enterpriseValue", "ebitda",
    ]
    rows = []
    # Processar em lotes de 20 para performance
    tickers_list = list(tickers_sa)
    for i in range(0, len(tickers_list), 20):
        batch = tickers_list[i:i + 20]
        try:
            data = yf.Tickers(" ".join(batch))
            for tk in batch:
                try:
                    info = data.tickers[tk].info
                    row = {"ticker": tk}
                    for campo in _CAMPOS:
                        val = info.get(campo)
                        if val is not None:
                            row[campo] = float(val)
                    if len(row) > 1:  # tem pelo menos 1 campo além do ticker
                        rows.append(row)
                except Exception:
                    continue
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # dividendYield: yfinance JÁ retorna em % (12.39 = 12.39%) — NÃO converter
    # returnOnEquity e profitMargins: yfinance retorna como decimal (0.05 = 5%) — converter
    if "returnOnEquity" in df.columns:
        df["returnOnEquity"] = df["returnOnEquity"] * 100
    if "profitMargins" in df.columns:
        df["profitMargins"] = df["profitMargins"] * 100

    return df


def _load_fundamentals_wide(tickers_carteira=None) -> pd.DataFrame:
    """Carrega fundamentalistas: primeiro do parquet/DB local, depois complementa
    via yfinance para tickers faltantes. Retorna DataFrame wide (1 linha por ticker).
    """
    # 1) Carregar dados já disponíveis (parquet ou SQLite local)
    df_raw = carregar_fundamentals_explosao()
    if not df_raw.empty:
        df_local = df_raw.pivot(index="ticker", columns="indicador", values="valor").reset_index()
        _str_cols = {"ticker", "sector", "industry", "longName", "currency"}
        for col in df_local.columns:
            if col not in _str_cols:
                df_local[col] = pd.to_numeric(df_local[col], errors="coerce")
    else:
        df_local = pd.DataFrame(columns=["ticker"])

    # 2) Se temos lista de tickers da carteira, buscar faltantes via yfinance
    if tickers_carteira:
        tickers_sa = [t + ".SA" if not t.endswith(".SA") else t for t in tickers_carteira]
        tickers_existentes = set(df_local["ticker"].tolist()) if not df_local.empty else set()
        tickers_faltantes = [t for t in tickers_sa if t not in tickers_existentes]

        if tickers_faltantes:
            df_yf = _fetch_fundamentals_yfinance(tuple(sorted(tickers_faltantes)))
            if not df_yf.empty:
                # yfinance já retorna DY/ROE/margins como % (convertido acima)
                # DB local: DY já é %, ROE/margins são decimal → converter
                if not df_local.empty:
                    for col in ("returnOnEquity", "profitMargins"):
                        if col in df_local.columns:
                            df_local[col] = df_local[col] * 100
                    # dividendYield do DB local JÁ é % — nada a fazer
                df_local = pd.concat([df_local, df_yf], ignore_index=True)
                # Remover duplicatas (preferir local)
                df_local = df_local.drop_duplicates(subset=["ticker"], keep="first")

    if df_local.empty:
        return pd.DataFrame()

    # Calcular EV/EBITDA se temos os dados
    if "enterpriseValue" in df_local.columns and "ebitda" in df_local.columns:
        df_local["ev_ebitda"] = df_local["enterpriseValue"] / df_local["ebitda"].replace(0, np.nan)

    return df_local


def _render_explosao(df_fundos: pd.DataFrame, df_posicoes: pd.DataFrame):
    """Página Explosão: decomposição de fundos TAG em ações subjacentes via PDFs BTG."""

    # ── Detectar modo: PDFs locais ou parquet cloud ──
    _modo_pdf = pdf_parser._pdf_dir_exists()
    _data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    _parquet_portfolios = os.path.join(_data_dir, "explosao_portfolios.parquet")
    _parquet_resumos = os.path.join(_data_dir, "explosao_resumos.parquet")
    _modo_cloud = os.path.exists(_parquet_portfolios)

    if not _modo_pdf and not _modo_cloud:
        st.warning(
            "📂 Dados de Explosão não disponíveis. "
            "Execute `python export_data.py` localmente para exportar os dados dos PDFs."
        )
        return

    # ── Carregar dados conforme modo ──
    _parquet_acoes_diretas = os.path.join(_data_dir, "explosao_acoes_diretas.parquet")

    if _modo_cloud and not _modo_pdf:
        df_all_portfolios = pd.read_parquet(_parquet_portfolios)
        df_all_resumos = pd.read_parquet(_parquet_resumos) if os.path.exists(_parquet_resumos) else pd.DataFrame()
        df_all_acoes_diretas = pd.read_parquet(_parquet_acoes_diretas) if os.path.exists(_parquet_acoes_diretas) else pd.DataFrame()
        datas_pdf = sorted(df_all_portfolios["data_pdf"].unique(), reverse=True)
    else:
        df_all_portfolios = None  # será lido sob demanda dos PDFs
        df_all_resumos = None
        df_all_acoes_diretas = None
        datas_pdf = pdf_parser.listar_datas_disponiveis()

    if not datas_pdf or len(datas_pdf) == 0:
        st.warning("Nenhuma data disponível.")
        return

    # Lista de fundos TAG de RV que investem em FIAs/ações
    FUNDOS_RV_TAG = [
        "VIT LB FIA",
        "VIT ACOES FIA",
        "TRANCOSO IBOV FIA",
        "DUNAJUKO FIA",
        "JUBA II FIA",
        "PROFITABLE G FIA",
        "SOLIS FIA",
        "TB ATMOS FC FIA",
    ]

    # Fundos TAG com posições diretas em ações (custódia Mellon — sem PDF BTG)
    # CNPJ → nome display
    _SYNTA_DIRETOS = {
        "20214858000166": "SYNTA FIA",
        "51564188000131": "SYNTA FIA II",
    }

    col_data, col_fundos_pdf = st.columns([1, 3])

    with col_data:
        datas_display = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in datas_pdf[:60]]
        data_sel_display = st.selectbox("Data (PDF BTG)", options=datas_display, index=0)
        data_sel = data_sel_display.replace("-", "")

    # ── Listar fundos disponíveis ──
    if _modo_pdf:
        fundos_pdf = pdf_parser.listar_fundos_pdf(data_sel)
        fundos_rv_pdf = [f for f in fundos_pdf if f in FUNDOS_RV_TAG]
        if not fundos_rv_pdf:
            fundos_rv_pdf = [f for f in fundos_pdf if "FIA" in f.upper()]
    else:
        fundos_rv_pdf = sorted(
            df_all_portfolios[df_all_portfolios["data_pdf"] == data_sel]["fundo_tag"].unique()
        )

    # Adicionar fundos SYNTA (posições diretas via XML Mellon, sem PDF BTG)
    for _cnpj_synta, _nome_synta in _SYNTA_DIRETOS.items():
        if _nome_synta not in fundos_rv_pdf:
            # Verificar se temos dados XML para este fundo
            if not df_posicoes.empty and _cnpj_synta in df_posicoes["cnpj_fundo"].values:
                fundos_rv_pdf.append(_nome_synta)

    with col_fundos_pdf:
        fundos_sel_pdf = st.multiselect(
            "Fundo(s) TAG",
            options=fundos_rv_pdf,
            default=fundos_rv_pdf[:1] if fundos_rv_pdf else [],
            max_selections=5,
        )

    if not fundos_sel_pdf:
        st.info("Selecione pelo menos um fundo TAG para explodir.")
        return

    # ── Normalizar CNPJs dos fundos no nosso universo (para cruzamento) ──
    cnpj_to_nome_universo = {}
    for _, row in df_fundos.iterrows():
        cnpj_to_nome_universo[row["cnpj_norm"]] = row["nome"]
        if row.get("cnpj_foco_norm") and row["cnpj_foco_norm"] != "":
            cnpj_to_nome_universo[row["cnpj_foco_norm"]] = row["nome"]

    # ── Processar cada fundo selecionado ──
    for nome_fundo_tag in fundos_sel_pdf:
        st.markdown(f"### 💥 {nome_fundo_tag}")

        # Detectar se é fundo SYNTA (posições XML diretas, sem PDF BTG)
        _synta_cnpj = None
        for _sc, _sn in _SYNTA_DIRETOS.items():
            if _sn == nome_fundo_tag:
                _synta_cnpj = _sc
                break

        if _synta_cnpj:
            # SYNTA: carregar posições diretamente dos XMLs (posicoes_consolidado)
            df_portfolio = pd.DataFrame(columns=["cnpj", "nome_portfolio", "quantidade", "quota",
                                                   "financeiro", "pct_pl", "ganho_diario", "cnpj_norm"])
            resumo = {}
            # Buscar snapshot mais recente do fundo
            _df_synta = df_posicoes[df_posicoes["cnpj_fundo"] == _synta_cnpj].copy()
            if not _df_synta.empty:
                _data_max = _df_synta["data"].max()
                _snap = _df_synta[_df_synta["data"] == _data_max]
                _pl = _snap["pl"].iloc[0] if "pl" in _snap.columns and not _snap["pl"].isna().all() else 0
                resumo = {"patrimonio": _pl, "data": str(_data_max.date())}
                # Converter para formato df_acoes_dir (compatível com seção "Ações")
                df_acoes_dir = pd.DataFrame({
                    "ticker": _snap["ativo"].values,
                    "pct_pl": _snap["pct_pl"].values,
                    "financeiro": _snap["valor"].values if "valor" in _snap.columns else 0,
                    "quantidade": 0,
                    "cotacao": 0,
                    "ganho_diario": 0,
                    "var_dia": 0,
                })
            else:
                df_acoes_dir = pd.DataFrame()

        # Resumo, portfolio e ações diretas — PDF local ou parquet cloud
        elif _modo_pdf:
            resumo = pdf_parser.extrair_resumo(data_sel, nome_fundo_tag)
            df_portfolio = pdf_parser.extrair_portfolio_investido(data_sel, nome_fundo_tag)
            df_acoes_dir = pdf_parser.extrair_acoes_diretas(data_sel, nome_fundo_tag)
        else:
            # Ler do parquet
            mask = (df_all_portfolios["data_pdf"] == data_sel) & (df_all_portfolios["fundo_tag"] == nome_fundo_tag)
            df_portfolio = df_all_portfolios[mask].drop(columns=["data_pdf", "fundo_tag"], errors="ignore").copy()
            resumo = {}
            if not df_all_resumos.empty:
                mask_r = (df_all_resumos["data_pdf"] == data_sel) & (df_all_resumos["fundo_tag"] == nome_fundo_tag)
                resumo_rows = df_all_resumos[mask_r]
                if len(resumo_rows) > 0:
                    resumo = resumo_rows.iloc[0].to_dict()
            # Ações diretas do parquet
            if df_all_acoes_diretas is not None and not df_all_acoes_diretas.empty:
                mask_ad = (df_all_acoes_diretas["data_pdf"] == data_sel) & (df_all_acoes_diretas["fundo_tag"] == nome_fundo_tag)
                df_acoes_dir = df_all_acoes_diretas[mask_ad].drop(columns=["data_pdf", "fundo_tag"], errors="ignore").copy()
            else:
                df_acoes_dir = pd.DataFrame()

        if df_portfolio.empty and df_acoes_dir.empty:
            st.warning(f"Nenhum dado disponível para {nome_fundo_tag}.")
            continue

        patrimonio = resumo.get("patrimonio", 0)
        n_fundos = len(df_portfolio)
        n_acoes_dir = len(df_acoes_dir) if not df_acoes_dir.empty else 0
        total_pct_fundos = df_portfolio["pct_pl"].sum() if not df_portfolio.empty else 0
        total_pct_acoes = df_acoes_dir["pct_pl"].sum() if not df_acoes_dir.empty else 0
        total_pct = total_pct_fundos + total_pct_acoes

        # ── Cards de resumo ──
        _summary_cols = st.columns(4)
        with _summary_cols[0]:
            st.markdown(metric_card(
                "Patrimônio",
                f"R$ {patrimonio:,.0f}" if patrimonio else "N/D"
            ), unsafe_allow_html=True)
        with _summary_cols[1]:
            st.markdown(metric_card("Fundos Investidos", str(n_fundos)), unsafe_allow_html=True)
        with _summary_cols[2]:
            _lbl_acoes_dir = f"Ações Diretas"
            st.markdown(metric_card(_lbl_acoes_dir, str(n_acoes_dir)), unsafe_allow_html=True)
        with _summary_cols[3]:
            st.markdown(metric_card("% PL Total", f"{total_pct:.1f}%"), unsafe_allow_html=True)

        # ── Tabela Nível 1: Fundos investidos + Ações diretas ──
        if _synta_cnpj:
            _title_lv1 = "Posições em Ações (XML Mellon)"
        elif n_acoes_dir > 0:
            _title_lv1 = "Fundos Investidos + Ações Diretas (PDF BTG)"
        else:
            _title_lv1 = "Composição do Portfólio (PDF BTG)"
        st.markdown(f'<div class="tag-section-title">{_title_lv1}</div>', unsafe_allow_html=True)

        # Normalizar CNPJs do PDF para cruzamento
        if not df_portfolio.empty:
            df_portfolio["cnpj_norm"] = df_portfolio["cnpj"].apply(
                lambda x: pdf_parser._normalizar_cnpj(str(x)) if x else ""
            )
        else:
            df_portfolio = pd.DataFrame(columns=["cnpj", "nome_portfolio", "quantidade", "quota",
                                                   "financeiro", "pct_pl", "ganho_diario", "cnpj_norm"])

        # Verificar quais fundos investidos temos dados XML/CVM
        cnpjs_investidos = set(df_portfolio["cnpj_norm"].unique()) - {""}
        cnpjs_com_dados = set(df_posicoes["cnpj_fundo"].unique()) if not df_posicoes.empty else set()

        # Também verificar por cnpj_foco_norm (mapeamento master → feeder)
        foco_to_direto = {}
        for _, row in df_fundos.iterrows():
            foco = row.get("cnpj_foco_norm", "")
            direto = row["cnpj_norm"]
            if foco and foco != direto and foco != "":
                foco_to_direto[foco] = direto

        # Mapeamento manual: feeders exclusivos TB/BTG → feeders equivalentes
        # que temos nos dados XML/CVM (mesmo gestor/master fund)
        _TB_FEEDER_MAP = {
            "36017245000179": "37467515000106",  # NORTE LB FC FIA → NORTE LONG BIAS FIC
            "54116160000120": "32068007000131",  # SHARP LB TB FC FIA → SHARP LONG BIASED FEEDER FIC
            "42902399000146": "16617768000149",  # SPX FALCON 2 FIC FIA → SPX FALCON FIC ACOES
            "42922205000174": "22232927000190",  # TARPON GT 90 FIC FIA → TARPON GT FIC ACOES
            "39346123000114": "22232927000190",  # TARPON GT INS FC FIA → TARPON GT FIC ACOES
            "10309539000180": "26956042000194",  # OCEANA VALOR FIA → OCEANA VALOR FIC ACOES
            "52070019000108": "10500884000105",  # REAL INST FIC FIA → REAL INVESTOR FIC ACOES
            "46961685000133": "11145320000156",  # TB ATMOS FC FIA → ATMOS ACOES FIC ACOES
            "46331366000144": "11145320000156",  # ATME FC FIA (master ATMOS) → ATMOS ACOES FIC ACOES
            "40226121000170": "09401978000130",  # PERFIN ALOC FC FIA → PERFIN FORESIGHT FIC ACOES
        }
        # Só adicionar se o destino realmente tem dados
        for src, dst in _TB_FEEDER_MAP.items():
            if dst in cnpjs_com_dados and src not in foco_to_direto:
                foco_to_direto[src] = dst

        # Mapeamento manual: fundos mono-ativo (100% em uma única ação)
        # Quando o fundo não tem dados CVM/XML, sabemos exatamente o que compram
        _MONO_ATIVO_MAP = {
            "61455544000132": "BAUH4",   # FRASCATI FIA → 100% Excelsior Alimentos PN
            "30366098000166": "SCAR3",   # REGILO FIA → 100% São Carlos ON
        }

        df_portfolio["tem_dados"] = df_portfolio["cnpj_norm"].apply(
            lambda cnpj: "✅" if (cnpj in cnpjs_com_dados or foco_to_direto.get(cnpj, cnpj) in cnpjs_com_dados or cnpj in _MONO_ATIVO_MAP) else ("⚠️" if cnpj == "" else "❌")
        )

        # Montar tabela unificada: fundos + ações diretas
        _display_rows = []
        for _, r in df_portfolio.iterrows():
            _display_rows.append({
                "Nome": r["nome_portfolio"],
                "Tipo": "Fundo",
                "CNPJ/Ticker": r["cnpj"] if r["cnpj"] else "-",
                "% PL": r["pct_pl"],
                "Financeiro (R$)": r["financeiro"],
                "Ganho Diário (R$)": r["ganho_diario"],
                "Dados RV": r["tem_dados"],
            })

        if not df_acoes_dir.empty:
            for _, r in df_acoes_dir.iterrows():
                _is_etf = r["ticker"] in _ETF_INDEX_MAP
                _display_rows.append({
                    "Nome": r["ticker"],
                    "Tipo": "ETF" if _is_etf else "Ação",
                    "CNPJ/Ticker": r["ticker"],
                    "% PL": r["pct_pl"],
                    "Financeiro (R$)": r["financeiro"],
                    "Ganho Diário (R$)": r["ganho_diario"],
                    "Dados RV": "🔄" if _is_etf else "📊",
                })

        df_display = pd.DataFrame(_display_rows)
        if not df_display.empty:
            df_display["Financeiro (R$)"] = df_display["Financeiro (R$)"].apply(lambda x: f"{x:,.2f}")
            df_display["Ganho Diário (R$)"] = df_display["Ganho Diário (R$)"].apply(lambda x: f"{x:,.2f}")
            df_display["% PL"] = df_display["% PL"].apply(lambda x: f"{x:.2f}%")

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                height=min(len(df_display) * 40 + 45, 500),
            )

        # ── Explosão: Cruzar com dados XML/CVM + Ações Diretas + ETFs ──
        st.markdown(f'<div class="tag-section-title">Exposição a Ações (Explosão)</div>', unsafe_allow_html=True)

        exposicoes = []
        fundos_identificados = 0
        _etfs_explodidos = {}  # cache de composição ETF

        # Parte 1: Explodir fundos investidos (via CVM/XML)
        for _, row_pdf in df_portfolio.iterrows():
            cnpj_fundo_investido = row_pdf["cnpj_norm"]
            peso_fundo = row_pdf["pct_pl"] / 100.0  # peso no TAG
            nome_fundo_investido = row_pdf["nome_portfolio"]

            if not cnpj_fundo_investido:
                continue

            # Caso especial: fundos mono-ativo (100% em uma única ação)
            if cnpj_fundo_investido in _MONO_ATIVO_MAP:
                ticker_mono = _MONO_ATIVO_MAP[cnpj_fundo_investido]
                fundos_identificados += 1
                exposicoes.append({
                    "ativo": ticker_mono,
                    "setor": classificar_setor(ticker_mono),
                    "fundo_origem": nome_fundo_investido,
                    "peso_fundo_pct": row_pdf["pct_pl"],
                    "peso_no_fundo_pct": 100.0,
                    "exposicao_pct": peso_fundo * 100.0,
                })
                continue

            # Resolver mapeamento master/foco → direto
            cnpj_busca = foco_to_direto.get(cnpj_fundo_investido, cnpj_fundo_investido)

            # Buscar posições mais recentes desse fundo
            df_fundo_pos = df_posicoes[df_posicoes["cnpj_fundo"] == cnpj_busca].copy()
            if df_fundo_pos.empty:
                # Tentar com CNPJ original
                df_fundo_pos = df_posicoes[df_posicoes["cnpj_fundo"] == cnpj_fundo_investido].copy()

            if df_fundo_pos.empty:
                continue

            fundos_identificados += 1

            # Pegar snapshot mais recente
            data_mais_recente = df_fundo_pos["data"].max()
            df_snapshot = df_fundo_pos[df_fundo_pos["data"] == data_mais_recente].copy()

            for _, acao in df_snapshot.iterrows():
                ticker = acao["ativo"]
                pct_pl_no_fundo = acao.get("pct_pl", 0) or 0
                setor = acao.get("setor", classificar_setor(ticker))

                # Exposição ponderada: peso do fundo no TAG × peso da ação no fundo
                exposicao_ponderada = peso_fundo * pct_pl_no_fundo

                exposicoes.append({
                    "ativo": ticker,
                    "setor": setor,
                    "fundo_origem": nome_fundo_investido,
                    "peso_fundo_pct": row_pdf["pct_pl"],
                    "peso_no_fundo_pct": pct_pl_no_fundo,
                    "exposicao_pct": exposicao_ponderada,
                })

        # Parte 2: Ações diretas (da seção "Ações" do PDF)
        if not df_acoes_dir.empty:
            for _, row_acao in df_acoes_dir.iterrows():
                ticker_dir = row_acao["ticker"]
                peso_direto = row_acao["pct_pl"]  # já é % do PL total

                # Verificar se é um ETF que pode ser explodido
                if ticker_dir in _ETF_INDEX_MAP:
                    # Buscar composição do ETF
                    if ticker_dir not in _etfs_explodidos:
                        _etfs_explodidos[ticker_dir] = _fetch_etf_composition(ticker_dir)

                    etf_comp = _etfs_explodidos[ticker_dir]
                    if etf_comp:
                        # Explodir ETF: cada ação do índice recebe peso proporcional
                        for ticker_idx, peso_idx in etf_comp.items():
                            exposicao_etf = peso_direto * (peso_idx / 100.0)
                            exposicoes.append({
                                "ativo": ticker_idx,
                                "setor": classificar_setor(ticker_idx),
                                "fundo_origem": f"{ticker_dir} (ETF)",
                                "peso_fundo_pct": peso_direto,
                                "peso_no_fundo_pct": peso_idx,
                                "exposicao_pct": exposicao_etf,
                            })
                        continue  # ETF explodido com sucesso

                # Ação direta ou ETF sem dados → incluir como ativo direto
                exposicoes.append({
                    "ativo": ticker_dir,
                    "setor": classificar_setor(ticker_dir),
                    "fundo_origem": "Carteira Direta",
                    "peso_fundo_pct": peso_direto,
                    "peso_no_fundo_pct": 100.0,
                    "exposicao_pct": peso_direto,
                })

        if not exposicoes:
            st.info("Nenhuma ação identificada nos fundos investidos. Os dados XML/CVM podem não estar disponíveis para estes fundos.")
            continue

        df_exp = pd.DataFrame(exposicoes)

        # Card: % identificado (fundos com dados + ações diretas + ETFs explodidos)
        pct_identificado_fundos = df_portfolio[df_portfolio["cnpj_norm"].apply(
            lambda c: c in cnpjs_com_dados or foco_to_direto.get(c, c) in cnpjs_com_dados or c in _MONO_ATIVO_MAP
        )]["pct_pl"].sum() if not df_portfolio.empty else 0
        pct_identificado_direto = total_pct_acoes  # ações diretas são 100% identificadas
        pct_identificado = pct_identificado_fundos + pct_identificado_direto

        _etfs_info = ""
        if _etfs_explodidos:
            _n_etfs_ok = sum(1 for v in _etfs_explodidos.values() if v)
            _etfs_info = f" | {_n_etfs_ok} ETF(s) explodido(s)"

        c4, c5, c6, c7 = st.columns(4)
        with c4:
            st.markdown(metric_card("Fundos c/ Dados RV", f"{fundos_identificados}/{n_fundos}"), unsafe_allow_html=True)
        with c5:
            st.markdown(metric_card("Ações Diretas", f"{n_acoes_dir}"), unsafe_allow_html=True)
        with c6:
            st.markdown(metric_card("% PL Identificado", f"{pct_identificado:.1f}%"), unsafe_allow_html=True)
        with c7:
            n_acoes = df_exp["ativo"].nunique()
            st.markdown(metric_card("Ações Únicas", str(n_acoes)), unsafe_allow_html=True)

        if _etfs_explodidos:
            _etf_names = [f"{k} ({len(v)} ações)" for k, v in _etfs_explodidos.items() if v]
            if _etf_names:
                st.caption(f"🔄 ETFs explodidos em ações subjacentes: {', '.join(_etf_names)}")

        # ── Tabela consolidada por ativo ──
        df_consolidado = df_exp.groupby("ativo").agg(
            exposicao_pct=("exposicao_pct", "sum"),
            setor=("setor", "first"),
            n_fundos=("fundo_origem", "nunique"),
            origens=("fundo_origem", lambda x: ", ".join(sorted(x.unique()))),
        ).reset_index().sort_values("exposicao_pct", ascending=False)

        # ── Top 20 ações — Gráfico de barras horizontal ──
        top_acoes = df_consolidado.head(20).copy()

        fig_barras = go.Figure()
        fig_barras.add_trace(go.Bar(
            y=top_acoes["ativo"][::-1],
            x=top_acoes["exposicao_pct"][::-1],
            orientation="h",
            marker=dict(
                color=[_hex_to_rgba(TAG_LARANJA, 0.7 + 0.3 * (i / max(len(top_acoes) - 1, 1)))
                       for i in range(len(top_acoes))][::-1],
                line=dict(width=0),
            ),
            text=[f"{v:.2f}%" for v in top_acoes["exposicao_pct"][::-1]],
            textposition="outside",
            textfont=dict(size=10, color=TAG_OFFWHITE),
            hovertemplate="%{y}: %{x:.2f}% do PL<extra></extra>",
        ))
        _chart_layout(fig_barras, "Top 20 Ações — Exposição Ponderada",
                      height=max(400, len(top_acoes) * 28),
                      y_title="", y_suffix="%", legend_h=False)
        fig_barras.update_layout(
            xaxis=dict(title="% do PL", ticksuffix="%"),
            yaxis=dict(tickfont=dict(size=10)),
            margin=dict(l=120, r=60, b=40),
        )
        st.plotly_chart(fig_barras, use_container_width=True)

        # ── Exposição por setor — Gráfico treemap / barras ──
        df_setor = df_exp.groupby("setor").agg(
            exposicao_pct=("exposicao_pct", "sum"),
            n_acoes=("ativo", "nunique"),
        ).reset_index().sort_values("exposicao_pct", ascending=False)

        col_setor_chart, col_setor_table = st.columns([3, 2])

        with col_setor_chart:
            # Treemap de setores
            fig_treemap = go.Figure(go.Treemap(
                labels=df_setor["setor"],
                values=df_setor["exposicao_pct"],
                parents=[""] * len(df_setor),
                texttemplate="<b>%{label}</b><br>%{value:.1f}%",
                hovertemplate="<b>%{label}</b><br>Exposição: %{value:.2f}%<br>Ações: %{customdata}<extra></extra>",
                customdata=df_setor["n_acoes"],
                marker=dict(
                    colors=[TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)] for i in range(len(df_setor))],
                    line=dict(width=1, color=TAG_BG_DARK),
                ),
                textfont=dict(size=12, color=TAG_OFFWHITE),
            ))
            fig_treemap.update_layout(
                title=dict(text="Exposição por Setor",
                           font=dict(size=14, color=TAG_LARANJA, family="Tahoma, sans-serif"),
                           y=0.98, yanchor="top"),
                height=400,
                margin=dict(l=10, r=10, t=40, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Tahoma, sans-serif", color=TAG_OFFWHITE),
            )
            st.plotly_chart(fig_treemap, use_container_width=True)

        with col_setor_table:
            # Tabela de setores
            df_setor_display = df_setor.copy()
            df_setor_display["exposicao_pct"] = df_setor_display["exposicao_pct"].apply(lambda x: f"{x:.2f}%")
            df_setor_display.columns = ["Setor", "Exposição (% PL)", "N° Ações"]
            st.dataframe(df_setor_display, use_container_width=True, hide_index=True,
                         height=min(len(df_setor_display) * 40 + 45, 400))

        # ── Tabela detalhada (todas as ações) ──
        with st.expander(f"📋 Tabela Detalhada — {len(df_consolidado)} ações", expanded=False):
            df_detail = df_consolidado.copy()
            df_detail["exposicao_pct"] = df_detail["exposicao_pct"].apply(lambda x: f"{x:.3f}%")
            df_detail.columns = ["Ativo", "Exposição (% PL)", "Setor", "N° Fundos", "Origens"]
            st.dataframe(df_detail, use_container_width=True, hide_index=True,
                         height=min(len(df_detail) * 40 + 45, 600))

        # ── Tabela cruzada: ação × fundo origem ──
        with st.expander(f"🔀 Matriz Ação × Fundo Origem", expanded=False):
            # Pivot: ativo nas linhas, fundo_origem nas colunas, valor = exposição
            top_30_ativos = df_consolidado.head(30)["ativo"].tolist()
            df_matriz = df_exp[df_exp["ativo"].isin(top_30_ativos)].pivot_table(
                index="ativo",
                columns="fundo_origem",
                values="exposicao_pct",
                aggfunc="sum",
                fill_value=0,
            )
            df_matriz["Total"] = df_matriz.sum(axis=1)
            df_matriz = df_matriz.sort_values("Total", ascending=False)

            # Formatar
            df_mat_display = df_matriz.map(lambda x: f"{x:.2f}%" if x > 0 else "-")
            st.dataframe(df_mat_display, use_container_width=True,
                         height=min(len(df_mat_display) * 40 + 45, 600))

        # ══════════════════════════════════════════════════════════════════
        # SEÇÃO A+B: Análise Histórica (Exposição Setorial e por Ativo)
        # ══════════════════════════════════════════════════════════════════
        st.markdown(f'<div class="tag-section-title">Análise Histórica</div>', unsafe_allow_html=True)

        # Preparar dados para explosão histórica
        _port_cnpjs = df_portfolio["cnpj_norm"].tolist() if not df_portfolio.empty else []
        _port_pesos = df_portfolio["pct_pl"].tolist() if not df_portfolio.empty else []
        _foco_items = list(foco_to_direto.items())

        # Preparar ações diretas para histórico
        _direct_stock_items = []
        _etf_comp_items = []
        if not df_acoes_dir.empty:
            for _, r in df_acoes_dir.iterrows():
                _direct_stock_items.append((r["ticker"], r["pct_pl"]))
            # Incluir composições de ETFs já buscadas
            for etf_tk, comp in _etfs_explodidos.items():
                if comp:
                    _etf_comp_items.append((etf_tk, comp))

        # Filtrar posicoes apenas para CNPJs relevantes (performance)
        _cnpjs_relevantes = set()
        for c in _port_cnpjs:
            if c:
                _cnpjs_relevantes.add(c)
                _cnpjs_relevantes.add(foco_to_direto.get(c, c))
        df_pos_filtrado = df_posicoes[df_posicoes["cnpj_fundo"].isin(_cnpjs_relevantes)].copy()

        df_hist = pd.DataFrame(columns=["data", "ativo", "setor", "exposicao_pct"])
        _has_pos_data = not df_pos_filtrado.empty
        _has_direct = len(_direct_stock_items) > 0

        if _has_pos_data or _has_direct:
            # Serializar para cache (st.cache_data precisa de tipos hashable)
            import io as _io
            _buf = _io.BytesIO()
            if _has_pos_data:
                df_pos_filtrado.to_parquet(_buf, index=False)
            else:
                # Se só temos ações diretas, precisamos de um parquet mínimo para as datas
                # Usar df_posicoes completo para obter datas (pegar um subset pequeno)
                _dates_sample = df_posicoes.head(1) if not df_posicoes.empty else pd.DataFrame()
                if not _dates_sample.empty:
                    df_pos_filtrado = df_posicoes.drop_duplicates(subset=["data"])[["data", "cnpj_fundo", "ativo", "pct_pl", "setor"]].head(100)
                    df_pos_filtrado.to_parquet(_buf, index=False)
                else:
                    _buf = None

            if _buf is not None:
                _pos_bytes = _buf.getvalue()

                # Serializar ETF compositions como JSON (dicts não são hashable para cache)
                import json as _json
                _etf_comp_json = _json.dumps(dict(_etf_comp_items)) if _etf_comp_items else None

                df_hist = _compute_historical_explosion(
                    _portfolio_key=f"{nome_fundo_tag}_{data_sel}_v2",
                    portfolio_cnpjs=_port_cnpjs,
                    portfolio_pesos=_port_pesos,
                    foco_map_items=_foco_items,
                    mono_ativo_items=list(_MONO_ATIVO_MAP.items()),
                    df_posicoes_serialized=_pos_bytes,
                    direct_stock_items=_direct_stock_items,
                    etf_composition_json=_etf_comp_json,
                )

            if not df_hist.empty and len(df_hist["data"].unique()) >= 2:
                # Calcular cobertura total (% PL explodido por mês)
                _total_pct_by_date = df_hist.groupby("data")["exposicao_pct"].sum()
                _avg_coverage = _total_pct_by_date.mean()
                st.caption(
                    f"⚠️ Exposição ponderada: cada ação = peso do sub-fundo × peso da ação no sub-fundo. "
                    f"Cobertura média: **{_avg_coverage:.1f}%** do PL (fundos sem dados RV não aparecem)."
                )

                # A) Exposição Setorial Histórica — Stacked Area
                df_hist_setor = df_hist.groupby(["data", "setor"])["exposicao_pct"].sum().reset_index()
                pivot_setor = df_hist_setor.pivot_table(
                    index="data", columns="setor", values="exposicao_pct", aggfunc="sum"
                ).fillna(0)

                fig_hist_setor = grafico_stacked_area(
                    pivot_setor,
                    f"Exposição Setorial Histórica — {nome_fundo_tag}",
                    top_n=12,
                )
                st.plotly_chart(fig_hist_setor, use_container_width=True)

                # B) Evolução Top Ações — Stacked Area + Linhas
                df_hist_ativo = df_hist.groupby(["data", "ativo"])["exposicao_pct"].sum().reset_index()
                pivot_ativo = df_hist_ativo.pivot_table(
                    index="data", columns="ativo", values="exposicao_pct", aggfunc="sum"
                ).fillna(0)

                col_area, col_line = st.columns(2)
                with col_area:
                    fig_hist_ativo = grafico_stacked_area(
                        pivot_ativo,
                        f"Top Ações (Área) — {nome_fundo_tag}",
                        top_n=12,
                    )
                    st.plotly_chart(fig_hist_ativo, use_container_width=True)

                with col_line:
                    fig_hist_linhas = grafico_linhas(
                        pivot_ativo,
                        f"Top Ações (Linhas) — {nome_fundo_tag}",
                        top_n=10,
                    )
                    st.plotly_chart(fig_hist_linhas, use_container_width=True)
            else:
                st.info("Dados históricos insuficientes para gerar gráficos de evolução. "
                        "É necessário pelo menos 2 meses de dados CVM/XML para os fundos subjacentes.")

        # ══════════════════════════════════════════════════════════════════
        # SEÇÃO C: Múltiplos Ponderados do Portfólio
        # ══════════════════════════════════════════════════════════════════
        st.markdown(f'<div class="tag-section-title">Múltiplos do Portfólio</div>', unsafe_allow_html=True)

        # Passar tickers da explosão para buscar fundamentais de TODAS as ações
        _tickers_explosao = df_consolidado["ativo"].unique().tolist() if not df_consolidado.empty else None
        df_fund_wide = _load_fundamentals_wide(tickers_carteira=_tickers_explosao)

        if not df_fund_wide.empty and not df_consolidado.empty:
            # Mapear: carteira_rv usa "VALE3", yahoo usa "VALE3.SA"
            df_cons_fund = df_consolidado.copy()
            df_cons_fund["ticker_sa"] = df_cons_fund["ativo"] + ".SA"

            df_merged = df_cons_fund.merge(
                df_fund_wide, left_on="ticker_sa", right_on="ticker", how="inner"
            )

            total_exposicao = df_consolidado["exposicao_pct"].sum()
            cobertura_exposicao = df_merged["exposicao_pct"].sum()
            cobertura_pct = (cobertura_exposicao / total_exposicao * 100) if total_exposicao > 0 else 0

            # Definir múltiplos a calcular
            MULTIPLOS_CONFIG = [
                ("trailingPE", "P/L", "x", 1),
                ("forwardPE", "P/L Forward", "x", 1),
                ("priceToBook", "P/VP", "x", 2),
                ("ev_ebitda", "EV/EBITDA", "x", 1),
                ("dividendYield", "Div. Yield", "%", 2),
                ("returnOnEquity", "ROE", "%", 1),
                ("beta", "Beta", "", 2),
                ("profitMargins", "Margem Líq.", "%", 1),
            ]

            weighted_multiples = {}
            for col_name, label, suffix, decimals in MULTIPLOS_CONFIG:
                if col_name not in df_merged.columns:
                    continue
                valid = df_merged[df_merged[col_name].notna() & (df_merged[col_name] != 0)].copy()
                if valid.empty:
                    continue
                w = valid["exposicao_pct"] / valid["exposicao_pct"].sum()
                val = (valid[col_name] * w).sum()
                # _load_fundamentals_wide já retorna DY/ROE/margins em %
                weighted_multiples[col_name] = (label, val, suffix, decimals)

            # Cards de múltiplos — 2 linhas de 4
            if weighted_multiples:
                items = list(weighted_multiples.values())
                row1 = items[:4]
                row2 = items[4:8]

                # Card de cobertura primeiro
                st.markdown(f"""<div style="
                    background: linear-gradient(135deg, {TAG_BG_CARD} 0%, {TAG_BG_CARD_ALT} 100%);
                    border: 1px solid {BORDER_COLOR}; border-radius: 8px;
                    padding: 10px 16px; margin-bottom: 12px; text-align: center;
                    font-size: 13px; color: {TEXT_MUTED};">
                    📊 Cobertura Fundamentalista: <b style="color: {TAG_LARANJA};">{cobertura_pct:.1f}%</b> do PL
                    &nbsp;|&nbsp; {len(df_merged)} de {len(df_consolidado)} ações com dados
                </div>""", unsafe_allow_html=True)

                cols1 = st.columns(len(row1))
                for i, (label, val, suffix, decimals) in enumerate(row1):
                    fmt = f"{val:.{decimals}f}{suffix}"
                    with cols1[i]:
                        st.markdown(metric_card(label, fmt), unsafe_allow_html=True)

                if row2:
                    cols2 = st.columns(len(row2))
                    for i, (label, val, suffix, decimals) in enumerate(row2):
                        fmt = f"{val:.{decimals}f}{suffix}"
                        with cols2[i]:
                            st.markdown(metric_card(label, fmt), unsafe_allow_html=True)

                # Tabela expandível com detalhes por ação
                with st.expander(f"📊 Detalhe por Ação — Múltiplos ({len(df_merged)} ações)", expanded=False):
                    df_mult_detail = df_merged[["ativo", "exposicao_pct", "setor"]].copy()
                    for col_name, label, suffix, decimals in MULTIPLOS_CONFIG:
                        if col_name in df_merged.columns:
                            vals = df_merged[col_name].copy()
                            # DY/ROE/margins já em % via _load_fundamentals_wide
                            df_mult_detail[label] = vals.apply(
                                lambda x: f"{x:.{decimals}f}{suffix}" if pd.notna(x) and x != 0 else "-"
                            )
                    df_mult_detail["exposicao_pct"] = df_mult_detail["exposicao_pct"].apply(lambda x: f"{x:.2f}%")
                    df_mult_detail.columns = [c if c not in ("ativo", "exposicao_pct", "setor")
                                              else {"ativo": "Ativo", "exposicao_pct": "Peso (%PL)", "setor": "Setor"}[c]
                                              for c in df_mult_detail.columns]
                    st.dataframe(df_mult_detail, use_container_width=True, hide_index=True,
                                 height=min(len(df_mult_detail) * 40 + 45, 500))
            else:
                st.info("Nenhum dado fundamentalista disponível para as ações deste portfólio.")
        else:
            st.info("Dados fundamentalistas não disponíveis. Execute `python export_data.py` para exportar.")

        # ══════════════════════════════════════════════════════════════════
        # SEÇÃO D: Concentração e Diversificação
        # ══════════════════════════════════════════════════════════════════
        st.markdown(f'<div class="tag-section-title">Concentração e Diversificação</div>', unsafe_allow_html=True)

        if not df_consolidado.empty:
            weights = df_consolidado["exposicao_pct"].dropna()
            weights = weights[weights > 0]

            if not weights.empty:
                w_norm = weights / weights.sum()
                hhi = (w_norm ** 2).sum() * 10000
                n_efetivo = 1 / (w_norm ** 2).sum() if (w_norm ** 2).sum() > 0 else 0
                top1_pct = weights.max()
                top5_pct = weights.nlargest(5).sum()
                top10_pct = weights.nlargest(10).sum()
                n_total = len(weights)
                n_setores = df_consolidado["setor"].nunique()

                # Classificação HHI
                if hhi < 450:
                    hhi_class = "Diversificado"
                    hhi_color = "#6BDE97"
                elif hhi < 700:
                    hhi_class = "Moderado"
                    hhi_color = "#FFBB00"
                elif hhi < 1200:
                    hhi_class = "Concentrado"
                    hhi_color = "#FF8853"
                else:
                    hhi_class = "Muito Concentrado"
                    hhi_color = "#ED5A6E"

                # Cards de concentração
                c_hhi, c_top5, c_top10, c_nef = st.columns(4)
                with c_hhi:
                    st.markdown(f"""<div style="
                        background: {TAG_BG_CARD}; border: 1px solid {BORDER_COLOR};
                        border-radius: 8px; padding: 14px 16px; text-align: center;
                        border-left: 3px solid {hhi_color};">
                        <div style="font-size: 11px; color: {TEXT_MUTED}; text-transform: uppercase; letter-spacing: 0.5px;">HHI (Explosao)</div>
                        <div style="font-size: 22px; font-weight: 700; color: {hhi_color}; margin: 4px 0;">{hhi:.0f}</div>
                        <div style="font-size: 11px; color: {hhi_color};">{hhi_class}</div>
                    </div>""", unsafe_allow_html=True)
                with c_top5:
                    st.markdown(metric_card("Top 5 Ações", f"{top5_pct:.1f}%"), unsafe_allow_html=True)
                with c_top10:
                    st.markdown(metric_card("Top 10 Ações", f"{top10_pct:.1f}%"), unsafe_allow_html=True)
                with c_nef:
                    st.markdown(metric_card("N° Efetivo", f"{n_efetivo:.1f}"), unsafe_allow_html=True)

                c_n, c_set, c_top1 = st.columns(3)
                with c_n:
                    st.markdown(metric_card("Total de Ações", str(n_total)), unsafe_allow_html=True)
                with c_set:
                    st.markdown(metric_card("Setores", str(n_setores)), unsafe_allow_html=True)
                with c_top1:
                    # Usar idx do maior peso para garantir nome correto
                    _idx_top1 = weights.idxmax()
                    top1_nome = df_consolidado.loc[_idx_top1, "ativo"] if _idx_top1 in df_consolidado.index else (df_consolidado.iloc[0]["ativo"] if len(df_consolidado) > 0 else "N/D")
                    st.markdown(metric_card("Maior Posição", f"{top1_nome} ({top1_pct:.1f}%)"), unsafe_allow_html=True)

                # Legenda explicativa sobre o HHI
                st.markdown(f"""<div style="
                    background: {TAG_BG_CARD}; border: 1px solid {BORDER_COLOR};
                    border-radius: 8px; padding: 12px 16px; margin: 8px 0 12px 0;
                    font-size: 12px; line-height: 1.6; color: {TAG_OFFWHITE};">
                    <strong style="color: {TAG_OFFWHITE};">Indice HHI — Concentracao da Carteira Explodida</strong><br>
                    O HHI mede a concentracao considerando <b>todas as acoes subjacentes</b> (apos explosao dos sub-fundos, acoes diretas e ETFs).
                    Quanto maior o HHI, mais concentrado o portfolio em poucas acoes.<br>
                    <b>Calculo:</b> HHI = &Sigma;(w<sub>i</sub>)<sup>2</sup> &times; 10.000 &nbsp;—&nbsp;
                    Ex: 20 acoes iguais &rarr; HHI = 500 &nbsp;|&nbsp; 10 acoes iguais &rarr; HHI = 1.000 &nbsp;|&nbsp; 5 acoes iguais &rarr; HHI = 2.000<br>
                    <span style="color:#6BDE97;">&#9679;</span> <b>&lt;450</b> Diversificado &nbsp;&nbsp;
                    <span style="color:#FFBB00;">&#9679;</span> <b>450-700</b> Moderado &nbsp;&nbsp;
                    <span style="color:#FF8853;">&#9679;</span> <b>700-1.200</b> Concentrado &nbsp;&nbsp;
                    <span style="color:#ED5A6E;">&#9679;</span> <b>&gt;1.200</b> Muito concentrado<br>
                    <span style="color:{TEXT_MUTED};">O grafico historico pode apresentar valores diferentes do card atual porque a cobertura dos dados CVM varia mês a mês
                    (fundos que nao reportaram posicoes em determinado mes reduzem o numero de acoes visiveis, elevando o HHI).</span>
                </div>""", unsafe_allow_html=True)

                # ── Gráfico HHI Histórico com faixas coloridas ──
                # Usar dados de _compute_historical_explosion se disponíveis
                if not df_hist.empty and len(df_hist["data"].unique()) >= 2:
                    _datas_hhi_exp = sorted(df_hist["data"].unique())
                    _hhi_vals_exp = []
                    _hhi_dates_exp = []
                    _n_ativos_exp = []
                    _top1_exp = []
                    _coverage_exp = []

                    for _dt in _datas_hhi_exp:
                        _snap = df_hist[df_hist["data"] == _dt]
                        _w_snap = _snap.groupby("ativo")["exposicao_pct"].sum()
                        _w_snap = _w_snap[_w_snap > 0]
                        if len(_w_snap) > 0:
                            _w_n = _w_snap / _w_snap.sum()
                            _hhi_v = (_w_n ** 2).sum() * 10000
                            _hhi_vals_exp.append(_hhi_v)
                            _hhi_dates_exp.append(_dt)
                            _n_ativos_exp.append(len(_w_snap))
                            _top1_exp.append(_w_snap.max())
                            _coverage_exp.append(_w_snap.sum())

                    if len(_hhi_vals_exp) >= 2:
                        fig_hhi_exp = go.Figure()

                        fig_hhi_exp.add_trace(go.Scatter(
                            x=_hhi_dates_exp, y=_hhi_vals_exp,
                            mode="lines+markers",
                            name="HHI (Explosao)",
                            line=dict(width=2.5, color="#58C6F5"),
                            marker=dict(size=5, color="#58C6F5"),
                            hovertemplate="<b>HHI (Explosao)</b><br>%{x|%d/%m/%Y}: %{y:.0f}<br>N acoes: %{customdata[0]}<br>Top1: %{customdata[1]:.1f}%<br>Cobertura: %{customdata[2]:.1f}% PL<extra></extra>",
                            customdata=list(zip(_n_ativos_exp, _top1_exp, _coverage_exp)),
                        ))

                        # Faixas coloridas de fundo (tons suaves que contrastam com fundo escuro)
                        _max_hhi = max(max(_hhi_vals_exp) * 1.15, 800)
                        _faixas_exp = [
                            (0, 450, "rgba(107,222,151,0.05)", "#6BDE97", "Diversificado"),
                            (450, 700, "rgba(255,187,0,0.05)", "#FFBB00", "Moderado"),
                            (700, 1200, "rgba(255,187,0,0.03)", "#FF8853", "Concentrado"),
                            (1200, max(_max_hhi, 1500), "rgba(255,136,83,0.03)", "#FF8853", "Muito concentrado"),
                        ]
                        for _y0, _y1, _fill, _lc, _lbl in _faixas_exp:
                            fig_hhi_exp.add_hrect(y0=_y0, y1=_y1, fillcolor=_fill, line_width=0)

                        for _yval, _lc, _lbl in [(450, "#6BDE97", "Diversificado"), (700, "#FFBB00", "Moderado"), (1200, "#FF8853", "Concentrado")]:
                            fig_hhi_exp.add_hline(
                                y=_yval, line_dash="dot", line_color=_lc, line_width=1,
                                annotation_text=f"{_lbl} ({_yval})", annotation_position="bottom right",
                                annotation_font_color=_lc, annotation_font_size=9,
                            )

                        _chart_layout(fig_hhi_exp, f"{nome_fundo_tag} — HHI da Carteira Explodida (Historico)",
                                      height=380, y_title="HHI", y_suffix="")
                        fig_hhi_exp.update_yaxes(range=[0, _max_hhi])
                        st.plotly_chart(fig_hhi_exp, use_container_width=True)

                # ── Concentração Top 1 e Top 5 Histórica ──
                if not df_hist.empty and len(df_hist["data"].unique()) >= 2:
                    _datas_conc = sorted(df_hist["data"].unique())
                    _top1_hist_pcts = []
                    _top5_hist_pcts = []
                    _top1_hist_nomes = []
                    _conc_dates = []
                    for _dt in _datas_conc:
                        _snap = df_hist[df_hist["data"] == _dt]
                        _by_ativo = _snap.groupby("ativo")["exposicao_pct"].sum().sort_values(ascending=False)
                        if len(_by_ativo) > 0:
                            _conc_dates.append(_dt)
                            _top1_hist_pcts.append(_by_ativo.iloc[0])
                            _top1_hist_nomes.append(_by_ativo.index[0])
                            _top5_hist_pcts.append(_by_ativo.head(5).sum())

                    if len(_conc_dates) >= 2:
                        fig_conc = go.Figure()
                        fig_conc.add_trace(go.Scatter(
                            x=_conc_dates, y=_top5_hist_pcts,
                            name="Top 5 (soma)",
                            mode="lines",
                            line=dict(width=1, color=TAG_LARANJA),
                            fill="tozeroy",
                            fillcolor=_hex_to_rgba(TAG_LARANJA, 0.15),
                            hovertemplate="<b>%{x|%b/%Y}</b><br>Top 5: %{y:.1f}%<extra></extra>",
                        ))
                        fig_conc.add_trace(go.Scatter(
                            x=_conc_dates, y=_top1_hist_pcts,
                            name="Maior posição",
                            mode="lines+markers",
                            line=dict(width=2.5, color="#58C6F5"),
                            marker=dict(size=5, color="#58C6F5"),
                            customdata=_top1_hist_nomes,
                            hovertemplate="<b>%{x|%b/%Y}</b><br>%{customdata}: %{y:.1f}%<extra></extra>",
                        ))
                        _chart_layout(fig_conc, f"{nome_fundo_tag} — Concentração (Top 1 e Top 5)",
                                      height=380, y_title="% do PL")
                        st.plotly_chart(fig_conc, use_container_width=True)

                # ── Market Cap Breakdown ──
                if not df_fund_wide.empty and not df_consolidado.empty:
                    df_cap = df_consolidado.copy()
                    df_cap["ticker_sa"] = df_cap["ativo"] + ".SA"
                    df_cap = df_cap.merge(
                        df_fund_wide[["ticker", "marketCap"]],
                        left_on="ticker_sa", right_on="ticker", how="left"
                    )

                    def _classify_cap(mcap):
                        if pd.isna(mcap) or mcap is None or mcap == 0:
                            return "Sem Dados"
                        if mcap >= 40e9:
                            return "Large Cap"
                        if mcap >= 10e9:
                            return "Mid Cap"
                        return "Small Cap"

                    df_cap["cap_class"] = df_cap["marketCap"].apply(_classify_cap)
                    cap_breakdown = df_cap.groupby("cap_class")["exposicao_pct"].sum().reset_index()
                    cap_breakdown = cap_breakdown.sort_values("exposicao_pct", ascending=True)

                    cap_colors = {
                        "Large Cap": "#5C85F7",
                        "Mid Cap": "#6BDE97",
                        "Small Cap": "#FFBB00",
                        "Sem Dados": "#6A6864",
                    }

                    col_cap_chart, col_cap_table = st.columns([3, 2])
                    with col_cap_chart:
                        fig_cap = go.Figure()
                        fig_cap.add_trace(go.Bar(
                            y=cap_breakdown["cap_class"],
                            x=cap_breakdown["exposicao_pct"],
                            orientation="h",
                            marker=dict(
                                color=[cap_colors.get(c, TAG_CINZA_MEDIO) for c in cap_breakdown["cap_class"]],
                                line=dict(width=0),
                            ),
                            text=[f"{v:.1f}%" for v in cap_breakdown["exposicao_pct"]],
                            textposition="outside",
                            textfont=dict(size=11, color=TAG_OFFWHITE),
                            hovertemplate="%{y}: %{x:.2f}% do PL<extra></extra>",
                        ))
                        _chart_layout(fig_cap, "Market Cap Breakdown",
                                      height=250, y_title="", y_suffix="%", legend_h=False)
                        fig_cap.update_layout(
                            xaxis=dict(title="% do PL", ticksuffix="%"),
                            margin=dict(l=100, r=60, b=30),
                        )
                        st.plotly_chart(fig_cap, use_container_width=True)

                    with col_cap_table:
                        cap_display = cap_breakdown.sort_values("exposicao_pct", ascending=False).copy()
                        cap_display["exposicao_pct"] = cap_display["exposicao_pct"].apply(lambda x: f"{x:.2f}%")
                        cap_display.columns = ["Classificação", "Exposição (% PL)"]
                        st.dataframe(cap_display, use_container_width=True, hide_index=True)

        # ══════════════════════════════════════════════════════════════════
        # SEÇÃO E: Sobreposição entre Sub-Fundos DENTRO do Portfólio
        # ══════════════════════════════════════════════════════════════════
        st.markdown(f'<div class="tag-section-title">Sobreposição entre Sub-Fundos</div>', unsafe_allow_html=True)
        st.caption("Overlap entre os fundos investidos que compõem este portfólio TAG. "
                   "Para cada par, calcula-se a soma do min(% PL) dos ativos em comum.")

        # Computar carteira de cada sub-fundo
        subfund_carts = {}
        for _, row_sub in df_portfolio.iterrows():
            cnpj_sub = row_sub["cnpj_norm"]
            nome_sub = row_sub["nome_portfolio"]
            if not cnpj_sub:
                continue

            # Mono-ativo
            if cnpj_sub in _MONO_ATIVO_MAP:
                subfund_carts[nome_sub] = {_MONO_ATIVO_MAP[cnpj_sub]: 100.0}
                continue

            cnpj_busca_sub = foco_to_direto.get(cnpj_sub, cnpj_sub)
            df_sub_pos = df_posicoes[df_posicoes["cnpj_fundo"] == cnpj_busca_sub]
            if df_sub_pos.empty:
                df_sub_pos = df_posicoes[df_posicoes["cnpj_fundo"] == cnpj_sub]
            if df_sub_pos.empty:
                continue

            dt_max_sub = df_sub_pos["data"].max()
            snap_sub = df_sub_pos[df_sub_pos["data"] == dt_max_sub]
            cart_sub = dict(zip(snap_sub["ativo"], snap_sub["pct_pl"]))
            if cart_sub:
                subfund_carts[nome_sub] = cart_sub

        if len(subfund_carts) >= 2:
            sf_names = list(subfund_carts.keys())
            n_sf = len(sf_names)

            # Nomes curtos para heatmap
            sf_labels = []
            for nm in sf_names:
                parts = nm.split()
                short = " ".join(parts[:2]) if len(parts) > 2 else nm
                if len(short) > 20:
                    short = short[:17] + "..."
                sf_labels.append(short)

            # Heatmap: sobreposição por ativo entre sub-fundos
            overlap_matrix = np.full((n_sf, n_sf), np.nan)
            for i in range(n_sf):
                for j in range(n_sf):
                    if i != j:
                        overlap_matrix[i][j] = _calcular_sobreposicao_ativos(
                            subfund_carts[sf_names[i]], subfund_carts[sf_names[j]]
                        )

            text_matrix = []
            for i in range(n_sf):
                row_txt = []
                for j in range(n_sf):
                    if i == j:
                        n_at = len(subfund_carts[sf_names[i]])
                        row_txt.append(f"{n_at} ativos")
                    else:
                        row_txt.append(f"{overlap_matrix[i][j]:.1f}%")
                text_matrix.append(row_txt)

            fig_heat_sub = go.Figure(data=go.Heatmap(
                z=overlap_matrix,
                x=sf_labels,
                y=sf_labels,
                text=text_matrix,
                texttemplate="%{text}",
                textfont=dict(size=10, color=TEXT_COLOR),
                colorscale=[
                    [0, TAG_BG_CARD], [0.25, "#2A3060"],
                    [0.5, "#3f51b5"], [0.75, "#5C85F7"],
                    [1, "#58C6F5"]
                ],
                hovertemplate="<b>%{y}</b> x <b>%{x}</b><br>Sobreposição: %{text}<extra></extra>",
                showscale=True,
                colorbar=dict(title="% PL", ticksuffix="%", tickfont=dict(color=TEXT_MUTED)),
            ))
            fig_heat_sub.update_layout(
                height=max(400, 65 * n_sf + 140),
                template="plotly_dark",
                xaxis=dict(tickangle=45, side="bottom", tickfont=dict(color=TEXT_MUTED, size=9)),
                yaxis=dict(autorange="reversed", tickfont=dict(color=TEXT_MUTED, size=9)),
                font=dict(family="Tahoma, sans-serif", size=11, color=TEXT_COLOR),
                margin=dict(l=10, r=10, t=20, b=140),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_heat_sub, use_container_width=True)

            # Tabela pairwise com overlap
            overlap_pairs = []
            for i in range(n_sf):
                for j in range(i + 1, n_sf):
                    ovl = _calcular_sobreposicao_ativos(subfund_carts[sf_names[i]], subfund_carts[sf_names[j]])
                    common = set(subfund_carts[sf_names[i]].keys()) & set(subfund_carts[sf_names[j]].keys())
                    overlap_pairs.append({
                        "Fundo A": sf_labels[i],
                        "Fundo B": sf_labels[j],
                        "Sobreposição (%)": f"{ovl:.1f}%",
                        "Ativos Comuns": len(common),
                    })

            if overlap_pairs:
                df_ovl_pairs = pd.DataFrame(overlap_pairs).sort_values("Ativos Comuns", ascending=False)
                with st.expander(f"📋 Tabela de Sobreposição — {len(overlap_pairs)} pares", expanded=False):
                    st.dataframe(df_ovl_pairs, use_container_width=True, hide_index=True)

            # ── Gráfico Histórico de Sobreposição entre Sub-Fundos ──
            st.caption("Evolução da sobreposição (soma min % PL dos ativos em comum) ao longo do tempo "
                       "para cada par de sub-fundos.")

            # Para cada par de sub-fundos, calcular overlap em cada data histórica
            # Precisamos dos CNPJs para buscar posições históricas
            _subfund_cnpjs = {}
            for _, row_sub in df_portfolio.iterrows():
                cnpj_sub = row_sub["cnpj_norm"]
                nome_sub = row_sub["nome_portfolio"]
                if cnpj_sub and nome_sub in subfund_carts:
                    cnpj_busca_sub = foco_to_direto.get(cnpj_sub, cnpj_sub)
                    _subfund_cnpjs[nome_sub] = cnpj_busca_sub

            # Selecionar top pares por overlap para graficar (máx 10 linhas)
            if overlap_pairs:
                _pares_top = sorted(overlap_pairs, key=lambda x: float(x["Sobreposição (%)"].replace("%", "")),
                                    reverse=True)[:10]
                _name_to_idx = {sf_labels[i]: i for i in range(n_sf)}

                fig_hist_ovl = go.Figure()
                _color_idx = 0

                for par in _pares_top:
                    nome_a_short = par["Fundo A"]
                    nome_b_short = par["Fundo B"]
                    idx_a = _name_to_idx.get(nome_a_short)
                    idx_b = _name_to_idx.get(nome_b_short)
                    if idx_a is None or idx_b is None:
                        continue

                    nome_a_full = sf_names[idx_a]
                    nome_b_full = sf_names[idx_b]
                    cnpj_a = _subfund_cnpjs.get(nome_a_full)
                    cnpj_b = _subfund_cnpjs.get(nome_b_full)
                    if not cnpj_a or not cnpj_b:
                        continue

                    # Mono-ativo: não tem histórico de posições
                    if nome_a_full not in _subfund_cnpjs or nome_b_full not in _subfund_cnpjs:
                        continue

                    df_a = df_posicoes[df_posicoes["cnpj_fundo"] == cnpj_a]
                    df_b = df_posicoes[df_posicoes["cnpj_fundo"] == cnpj_b]
                    if df_a.empty or df_b.empty:
                        continue

                    common_dates = sorted(set(df_a["data"].unique()) & set(df_b["data"].unique()))
                    if len(common_dates) < 2:
                        continue

                    overlap_series = []
                    for dt in common_dates:
                        cart_a = dict(zip(df_a[df_a["data"] == dt]["ativo"], df_a[df_a["data"] == dt]["pct_pl"]))
                        cart_b = dict(zip(df_b[df_b["data"] == dt]["ativo"], df_b[df_b["data"] == dt]["pct_pl"]))
                        overlap_series.append(_calcular_sobreposicao_ativos(cart_a, cart_b))

                    pair_label = f"{nome_a_short} x {nome_b_short}"
                    fig_hist_ovl.add_trace(go.Scatter(
                        x=common_dates, y=overlap_series,
                        mode="lines+markers", name=pair_label,
                        line=dict(width=2.5, color=TAG_CHART_COLORS[_color_idx % len(TAG_CHART_COLORS)]),
                        marker=dict(size=4),
                        hovertemplate=f"<b>{pair_label}</b><br>%{{x|%b/%Y}}: %{{y:.1f}}%<extra></extra>",
                    ))
                    _color_idx += 1

                if fig_hist_ovl.data:
                    _chart_layout(fig_hist_ovl, f"Sobreposição Histórica — Sub-Fundos de {nome_fundo_tag}",
                                  y_title="% PL Sobreposto")
                    st.plotly_chart(fig_hist_ovl, use_container_width=True)
                else:
                    st.info("Dados históricos insuficientes para gráfico de sobreposição entre sub-fundos.")

            # Ações em comum entre todos os sub-fundos
            all_sf_tickers = {nm: set(cart.keys()) for nm, cart in subfund_carts.items()}
            common_all_sf = set.intersection(*all_sf_tickers.values()) if all_sf_tickers else set()
            if common_all_sf:
                st.markdown(f"""<div style="
                    background: {TAG_BG_CARD}; border: 1px solid {BORDER_COLOR};
                    border-radius: 8px; padding: 12px 16px; margin-top: 8px;
                    font-size: 13px; color: {TEXT_MUTED};">
                    🔗 <b style="color: {TAG_LARANJA};">{len(common_all_sf)}</b> ações em comum entre todos os sub-fundos:
                    <span style="color: {TAG_OFFWHITE};">{', '.join(sorted(common_all_sf)[:20])}</span>
                    {'...' if len(common_all_sf) > 20 else ''}
                </div>""", unsafe_allow_html=True)

        else:
            st.info("Dados insuficientes para calcular sobreposição entre sub-fundos (necessário ≥ 2 fundos com dados RV).")

        st.markdown("---")

    # ══════════════════════════════════════════════════════════════════
    # SEÇÃO E2: Overlap entre Fundos TAG (fora do loop, quando múltiplos)
    # ══════════════════════════════════════════════════════════════════
    if len(fundos_sel_pdf) > 1:
        st.markdown(f'<div class="tag-section-title">Sobreposição entre Fundos TAG</div>', unsafe_allow_html=True)
        st.caption("Overlap entre os diferentes fundos TAG selecionados (nível explodido em ações).")

        # Recomputar explosões para cada fundo TAG (incluindo ações diretas e ETFs)
        fund_explosions = {}
        for nome_fundo_tag_ovl in fundos_sel_pdf:
            if _modo_pdf:
                df_port_ovl = pdf_parser.extrair_portfolio_investido(data_sel, nome_fundo_tag_ovl)
                df_ad_ovl = pdf_parser.extrair_acoes_diretas(data_sel, nome_fundo_tag_ovl)
            else:
                mask_ovl = (df_all_portfolios["data_pdf"] == data_sel) & (df_all_portfolios["fundo_tag"] == nome_fundo_tag_ovl)
                df_port_ovl = df_all_portfolios[mask_ovl].drop(columns=["data_pdf", "fundo_tag"], errors="ignore").copy()
                if df_all_acoes_diretas is not None and not df_all_acoes_diretas.empty:
                    mask_ad_ovl = (df_all_acoes_diretas["data_pdf"] == data_sel) & (df_all_acoes_diretas["fundo_tag"] == nome_fundo_tag_ovl)
                    df_ad_ovl = df_all_acoes_diretas[mask_ad_ovl].drop(columns=["data_pdf", "fundo_tag"], errors="ignore").copy()
                else:
                    df_ad_ovl = pd.DataFrame()

            if df_port_ovl.empty and df_ad_ovl.empty:
                continue

            if not df_port_ovl.empty:
                df_port_ovl["cnpj_norm"] = df_port_ovl["cnpj"].apply(
                    lambda x: pdf_parser._normalizar_cnpj(str(x)) if x else ""
                )

            exposicoes_ovl = {}
            # Fundos investidos
            if not df_port_ovl.empty:
                for _, row_pdf_ovl in df_port_ovl.iterrows():
                    cnpj_inv = row_pdf_ovl["cnpj_norm"]
                    peso_f = row_pdf_ovl["pct_pl"] / 100.0
                    if not cnpj_inv:
                        continue
                    # Mono-ativo
                    if cnpj_inv in _MONO_ATIVO_MAP:
                        tk = _MONO_ATIVO_MAP[cnpj_inv]
                        exposicoes_ovl[tk] = exposicoes_ovl.get(tk, 0) + peso_f * 100.0
                        continue
                    cnpj_b = foco_to_direto.get(cnpj_inv, cnpj_inv)
                    df_fp = df_posicoes[df_posicoes["cnpj_fundo"] == cnpj_b]
                    if df_fp.empty:
                        df_fp = df_posicoes[df_posicoes["cnpj_fundo"] == cnpj_inv]
                    if df_fp.empty:
                        continue
                    dt_max = df_fp["data"].max()
                    df_snap = df_fp[df_fp["data"] == dt_max]
                    for _, acao_ovl in df_snap.iterrows():
                        ticker = acao_ovl["ativo"]
                        exp = peso_f * (acao_ovl.get("pct_pl", 0) or 0)
                        exposicoes_ovl[ticker] = exposicoes_ovl.get(ticker, 0) + exp

            # Ações diretas + ETFs
            if not df_ad_ovl.empty:
                for _, r_ad in df_ad_ovl.iterrows():
                    tk_dir = r_ad["ticker"]
                    peso_dir = r_ad["pct_pl"]
                    if tk_dir in _ETF_INDEX_MAP:
                        etf_comp = _fetch_etf_composition(tk_dir)
                        if etf_comp:
                            for tk_idx, p_idx in etf_comp.items():
                                exp = peso_dir * (p_idx / 100.0)
                                exposicoes_ovl[tk_idx] = exposicoes_ovl.get(tk_idx, 0) + exp
                            continue
                    exposicoes_ovl[tk_dir] = exposicoes_ovl.get(tk_dir, 0) + peso_dir

            if exposicoes_ovl:
                fund_explosions[nome_fundo_tag_ovl] = exposicoes_ovl

        # Calcular sobreposição par-a-par
        if len(fund_explosions) >= 2:
            fund_names = list(fund_explosions.keys())
            overlap_data = []
            for i in range(len(fund_names)):
                for j in range(i + 1, len(fund_names)):
                    a, b = fund_names[i], fund_names[j]
                    ovl = _calcular_sobreposicao_ativos(fund_explosions[a], fund_explosions[b])
                    overlap_data.append({"Fundo A": a, "Fundo B": b, "Sobreposição (%)": f"{ovl:.2f}%"})

            if overlap_data:
                df_overlap = pd.DataFrame(overlap_data)
                st.dataframe(df_overlap, use_container_width=True, hide_index=True)

                # Ações em comum
                all_tickers_sets = {name: set(exp.keys()) for name, exp in fund_explosions.items()}
                common_all = set.intersection(*all_tickers_sets.values()) if all_tickers_sets else set()
                if common_all:
                    st.markdown(f"""<div style="
                        background: {TAG_BG_CARD}; border: 1px solid {BORDER_COLOR};
                        border-radius: 8px; padding: 12px 16px; margin-top: 8px;
                        font-size: 13px; color: {TEXT_MUTED};">
                        🔗 <b style="color: {TAG_LARANJA};">{len(common_all)}</b> ações em comum entre todos os fundos selecionados:
                        <span style="color: {TAG_OFFWHITE};">{', '.join(sorted(common_all)[:20])}</span>
                        {'...' if len(common_all) > 20 else ''}
                    </div>""", unsafe_allow_html=True)
        else:
            st.info("Dados insuficientes para calcular sobreposição entre os fundos selecionados.")


if __name__ == "__main__":
    main()
