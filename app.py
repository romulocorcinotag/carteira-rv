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
# Paleta TAG Investimentos — Dark Futurista
# ──────────────────────────────────────────────────────────────────────────────
TAG_VERMELHO = "#630D24"
TAG_OFFWHITE = "#E6E4DB"
TAG_LARANJA = "#FF8853"
TAG_BRANCO = "#FFFFFF"
TAG_CINZA_ESCURO = "#2C1A1A"
TAG_CINZA_MEDIO = "#6A6864"
TAG_AZUL_ESCURO = "#002A6E"
# Dark theme tokens
DARK_BG = "#0A0A0F"            # Fundo principal quase preto
DARK_SURFACE = "#12121A"       # Cards, containers
DARK_SURFACE_2 = "#1A1A25"     # Elevação secundária
DARK_BORDER = "#2A2A3A"        # Bordas sutis
DARK_TEXT = "#E8E8F0"          # Texto principal
DARK_TEXT_MUTED = "#8888A0"    # Texto secundário
ACCENT_GLOW = "#FF885340"      # Laranja com glow
ACCENT_RED_GLOW = "#630D2450"  # Vermelho com glow
# Paleta de apoio para gráficos (cores vibrantes sobre fundo escuro)
TAG_CHART_COLORS = [
    "#FF8853",  # Laranja (alta visibilidade no dark)
    "#5C85F7",  # Azul
    "#6BDE97",  # Verde
    "#A485F2",  # Lilás
    "#58C6F5",  # Azul claro
    "#FFBB00",  # Amarelo
    "#ED5A6E",  # Rosa
    "#FF6B6B",  # Coral
    "#477C88",  # Teal
    "#C4B5FD",  # Lavanda
    "#34D399",  # Esmeralda
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
# CSS — Dark Futurista com glassmorphism
# ──────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* ══════════════════════════════════════════════════
           BASE — Dark theme, no gray bars
        ══════════════════════════════════════════════════ */
        .stApp {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background: {DARK_BG} !important;
            color: {DARK_TEXT} !important;
        }}
        /* Remove Streamlit's default top bar / toolbar / deploy button */
        header[data-testid="stHeader"] {{
            background: {DARK_BG} !important;
            border-bottom: none !important;
        }}
        .stDeployButton, [data-testid="stToolbar"] {{
            display: none !important;
        }}
        /* Remove Streamlit bottom footer */
        footer {{
            display: none !important;
        }}
        /* Subtle background gradient overlay */
        .stApp::before {{
            content: ''; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: radial-gradient(ellipse at 15% 0%, rgba(99,13,36,0.12) 0%, transparent 50%),
                        radial-gradient(ellipse at 85% 100%, rgba(88,198,245,0.04) 0%, transparent 50%);
            pointer-events: none; z-index: 0;
        }}
        .stMainBlockContainer {{
            max-width: 1400px;
            padding-top: 0.5rem !important;
        }}
        /* ── Text — brighter defaults ── */
        .stMarkdown p, .stMarkdown li {{
            font-size: 0.9rem !important;
            line-height: 1.6 !important;
            color: #C0C0D0 !important;
        }}
        h1, h2, h3 {{
            color: #F0F0F8 !important;
            font-family: 'Inter', sans-serif !important;
        }}
        h3 {{
            font-size: 1.1rem !important;
            font-weight: 700 !important;
            color: {DARK_TEXT} !important;
        }}

        /* ══════════════════════════════════════════════════
           TABS — pill style
        ══════════════════════════════════════════════════ */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 2px; background: {DARK_SURFACE};
            border-radius: 10px; padding: 4px;
            border: 1px solid {DARK_BORDER};
        }}
        .stTabs [data-baseweb="tab"] {{
            font-size: 12px !important; font-weight: 600 !important;
            padding: 10px 20px !important; color: #A0A0B8 !important;
            text-transform: uppercase !important; letter-spacing: 0.8px !important;
            border-radius: 8px !important; border: none !important;
            transition: all 0.25s ease !important;
            background: transparent !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            color: {TAG_LARANJA} !important;
            background: {DARK_SURFACE_2} !important;
        }}
        .stTabs [aria-selected="true"] {{
            font-weight: 700 !important; color: #FFFFFF !important;
            background: linear-gradient(135deg, {TAG_LARANJA}, #FF6B3D) !important;
            box-shadow: 0 2px 12px {ACCENT_GLOW} !important;
        }}
        .stTabs [data-baseweb="tab-highlight"],
        .stTabs [data-baseweb="tab-border"] {{
            display: none !important;
        }}

        /* ══════════════════════════════════════════════════
           DATAFRAMES (st.dataframe)
        ══════════════════════════════════════════════════ */
        .stDataFrame {{
            border-radius: 10px !important;
            overflow: hidden !important;
        }}
        .stDataFrame th {{
            font-size: 10px !important; font-weight: 700 !important;
            padding: 10px 14px !important; text-transform: uppercase !important;
            letter-spacing: 0.6px !important;
            background: {DARK_SURFACE_2} !important; color: {TAG_LARANJA} !important;
            border-bottom: 1px solid {DARK_BORDER} !important;
        }}
        .stDataFrame td {{
            padding: 8px 14px !important; font-size: 13px !important;
            color: {DARK_TEXT} !important;
            background: {DARK_SURFACE} !important;
            border-bottom: 1px solid {DARK_BORDER}80 !important;
        }}
        .stDataFrame [role="columnheader"] {{
            color: {TAG_LARANJA} !important;
            background: {DARK_SURFACE_2} !important;
        }}
        .stDataFrame [role="gridcell"] {{
            color: {DARK_TEXT} !important;
            background: {DARK_SURFACE} !important;
        }}

        /* ══════════════════════════════════════════════════
           MARKDOWN TABLES
        ══════════════════════════════════════════════════ */
        .stMarkdown table {{
            width: 100% !important; border-collapse: collapse !important;
            margin: 12px 0 !important; border-radius: 10px !important;
            overflow: hidden !important;
        }}
        .stMarkdown table th {{
            background: {DARK_SURFACE_2} !important; color: {TAG_LARANJA} !important;
            padding: 11px 16px !important; text-align: left !important;
            font-weight: 700 !important; font-size: 10px !important;
            text-transform: uppercase !important; letter-spacing: 0.6px !important;
            border-bottom: 1px solid {DARK_BORDER} !important;
        }}
        .stMarkdown table td {{
            padding: 10px 16px !important; border-bottom: 1px solid {DARK_BORDER}60 !important;
            font-size: 13px !important; color: {DARK_TEXT} !important;
            background: transparent !important;
        }}
        .stMarkdown table tr:nth-child(even) td {{
            background: {DARK_SURFACE_2}80 !important;
        }}
        .stMarkdown table tr:hover td {{
            background: {DARK_SURFACE_2} !important;
        }}

        /* ══════════════════════════════════════════════════
           INPUTS — dark background + bright text (agressivo)
        ══════════════════════════════════════════════════ */
        /* --- Labels de todos os widgets --- */
        .stSelectbox label, .stMultiSelect label, .stDateInput label,
        .stSlider label, .stNumberInput label, .stTextInput label,
        .stRadio label, .stCheckbox label,
        [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
        label, .stApp label {{
            color: #D0D0E0 !important;
            font-size: 11px !important; text-transform: uppercase !important;
            letter-spacing: 0.5px !important; font-weight: 600 !important;
        }}

        /* --- Container do select/multiselect — flush com fundo --- */
        .stSelectbox > div > div,
        .stMultiSelect > div > div,
        .stDateInput > div > div,
        .stSelectbox [data-baseweb="select"],
        .stMultiSelect [data-baseweb="select"],
        [data-baseweb="select"],
        [data-baseweb="select"] > div {{
            background: {DARK_BG} !important;
            background-color: {DARK_BG} !important;
            border: 1px solid {DARK_BORDER} !important;
            border-radius: 8px !important;
            color: {DARK_TEXT} !important;
        }}

        /* --- Texto dentro dos selects (valor selecionado, placeholder) --- */
        [data-baseweb="select"] span,
        [data-baseweb="select"] div,
        [data-baseweb="select"] input,
        [data-baseweb="select"] [data-testid="stMarkdownContainer"],
        [data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
        .stSelectbox div[data-baseweb="select"] *,
        .stMultiSelect div[data-baseweb="select"] * {{
            color: {DARK_TEXT} !important;
            -webkit-text-fill-color: {DARK_TEXT} !important;
        }}
        /* Placeholder "Choose options" / "Select..." */
        [data-baseweb="select"] [aria-live="polite"],
        [data-baseweb="select"] .css-1dimb5e-singleValue,
        [data-baseweb="select"] .css-qbdosj-Input input,
        [data-baseweb="select"] input::placeholder {{
            color: #9898B0 !important;
            -webkit-text-fill-color: #9898B0 !important;
            opacity: 1 !important;
        }}

        /* --- Focus state --- */
        .stSelectbox > div > div:focus-within,
        .stMultiSelect > div > div:focus-within {{
            border-color: {TAG_LARANJA} !important;
            box-shadow: 0 0 0 2px {ACCENT_GLOW} !important;
        }}

        /* --- Todos os inputs genéricos --- */
        .stDateInput input, .stNumberInput input, .stTextInput input {{
            color: {DARK_TEXT} !important;
            -webkit-text-fill-color: {DARK_TEXT} !important;
            background: {DARK_BG} !important;
        }}
        .stApp input, .stApp select, .stApp textarea {{
            color: {DARK_TEXT} !important;
            -webkit-text-fill-color: {DARK_TEXT} !important;
            background-color: {DARK_BG} !important;
        }}

        /* --- Dropdown arrow / icons --- */
        .stSelectbox svg, .stMultiSelect svg, .stDateInput svg {{
            fill: #B0B0C8 !important;
        }}

        /* --- Slider --- */
        .stSlider [data-testid="stTickBarMin"],
        .stSlider [data-testid="stTickBarMax"],
        .stSlider div[data-baseweb="slider"] div {{
            color: {DARK_TEXT} !important;
        }}

        /* ── Multiselect pills ── */
        span[data-baseweb="tag"] {{
            background: linear-gradient(135deg, {TAG_VERMELHO}, #8B1A3A) !important;
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            border-radius: 6px !important; font-size: 11px !important;
            font-weight: 600 !important;
        }}
        .stMultiSelect [data-baseweb="tag"] button {{
            color: white !important;
        }}

        /* ── Dropdown / Popover menus ── */
        [data-baseweb="popover"] {{
            background: {DARK_SURFACE} !important;
            border: 1px solid {DARK_BORDER} !important;
        }}
        [data-baseweb="menu"] {{
            background: {DARK_SURFACE} !important;
        }}
        [role="option"] {{
            color: {DARK_TEXT} !important;
        }}
        [role="option"]:hover {{
            background: {DARK_SURFACE_2} !important;
        }}
        [aria-selected="true"][role="option"] {{
            background: {TAG_VERMELHO}30 !important;
        }}
        /* Calendar */
        [data-baseweb="calendar"], [data-baseweb="calendar"] div {{
            background: {DARK_SURFACE} !important;
            color: {DARK_TEXT} !important;
        }}

        /* ══════════════════════════════════════════════════
           HEADER
        ══════════════════════════════════════════════════ */
        .tag-header {{
            display: flex; align-items: center; gap: 20px;
            padding: 16px 0 12px 0;
        }}
        .tag-logo-box {{
            background: linear-gradient(135deg, {TAG_VERMELHO}, #8B1A3A);
            border-radius: 14px;
            padding: 14px 20px; display: flex; align-items: center;
            justify-content: center; min-height: 56px;
            box-shadow: 0 4px 20px {ACCENT_RED_GLOW};
        }}
        .tag-logo-box img {{ height: 48px; filter: brightness(0) invert(1); }}
        .tag-header-text h1 {{
            margin: 0; font-size: 2rem; font-weight: 800;
            background: linear-gradient(135deg, #FFFFFF, {TAG_LARANJA});
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }}
        .tag-header-text p {{
            margin: 4px 0 0 0; font-size: 0.75rem; color: #8888A8;
            letter-spacing: 2px; text-transform: uppercase; font-weight: 500;
        }}

        /* ── Dividers ── */
        .tag-divider {{
            height: 2px; border: none;
            background: linear-gradient(90deg, {TAG_LARANJA}, {TAG_VERMELHO}80, transparent);
            margin: 12px 0 20px 0; opacity: 0.7;
        }}
        .tag-section-divider {{
            height: 1px; border: none;
            background: linear-gradient(90deg, {DARK_BORDER}, transparent);
            margin: 32px 0 24px 0;
        }}

        /* ══════════════════════════════════════════════════
           METRIC CARDS (glass)
        ══════════════════════════════════════════════════ */
        .tag-metric-card {{
            background: {DARK_SURFACE};
            border: 1px solid {DARK_BORDER};
            border-radius: 12px;
            padding: 20px 14px; text-align: center;
            position: relative; overflow: hidden;
            transition: all 0.3s ease;
        }}
        .tag-metric-card::before {{
            content: ''; position: absolute; top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, {TAG_LARANJA}, {TAG_VERMELHO});
        }}
        .tag-metric-card:hover {{
            border-color: {TAG_LARANJA}40;
            box-shadow: 0 4px 24px rgba(255,136,83,0.08);
            transform: translateY(-1px);
        }}
        .tag-metric-card .value {{
            font-size: 1.5rem; font-weight: 800;
            color: #F0F0F8; line-height: 1.15;
            font-family: 'Inter', sans-serif;
        }}
        .tag-metric-card .label {{
            font-size: 0.68rem; color: #9898B0;
            margin-bottom: 8px; font-weight: 600;
            text-transform: uppercase; letter-spacing: 1px;
        }}

        /* ── Section titles ── */
        .tag-section-title {{
            font-size: 0.85rem; font-weight: 700; color: {TAG_LARANJA};
            margin: 32px 0 12px 0; padding-bottom: 8px;
            border-bottom: 1px solid {DARK_BORDER};
            text-transform: uppercase; letter-spacing: 1.2px;
            font-family: 'Inter', sans-serif;
        }}

        /* ══════════════════════════════════════════════════
           MISC ELEMENTS
        ══════════════════════════════════════════════════ */
        .stCaption {{
            font-size: 0.78rem !important; color: #9898B0 !important;
        }}
        .stAlert {{
            background: {DARK_SURFACE} !important;
            border-color: {DARK_BORDER} !important;
        }}
        .stAlert p {{
            color: {DARK_TEXT} !important;
        }}
        div[data-testid="stSidebar"] {{ display: none !important; }}

        /* ── Expander ── */
        details {{
            background: {DARK_SURFACE} !important;
            border: 1px solid {DARK_BORDER} !important;
            border-radius: 10px !important;
        }}
        details summary {{
            font-weight: 600 !important; color: {TAG_LARANJA} !important;
            font-size: 0.85rem !important;
        }}
        details summary span {{
            color: {TAG_LARANJA} !important;
        }}

        /* ── Scrollbar ── */
        ::-webkit-scrollbar {{ width: 5px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: {DARK_BORDER}; border-radius: 3px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: {TAG_LARANJA}60; }}

        /* ── Plotly containers ── */
        .stPlotlyChart {{
            background: {DARK_SURFACE} !important;
            border: 1px solid {DARK_BORDER} !important;
            border-radius: 12px !important;
            padding: 8px !important;
            margin-bottom: 16px !important;
        }}
        .stPlotlyChart .modebar {{
            background: transparent !important;
        }}
        .stPlotlyChart .modebar-btn path {{
            fill: #7070888 !important;
        }}

        /* ── Labels / Radio / Checkbox / Metric ── */
        .stRadio label, .stCheckbox label, .stRadio span, .stCheckbox span {{
            color: {DARK_TEXT} !important;
        }}
        /* Streamlit caption / small text */
        .stCaption, .stCaption p, small {{
            color: #B0B0C8 !important;
        }}
        /* Select box placeholder text */
        [data-baseweb="select"] [data-testid="stMarkdownContainer"] p {{
            color: {DARK_TEXT} !important;
        }}
        /* All paragraph text inside widgets */
        .stSelectbox p, .stMultiSelect p, .stDateInput p,
        .stSlider p, .stNumberInput p, .stTextInput p {{
            color: #D0D0E0 !important;
        }}
        [data-testid="stMetricValue"] {{
            color: {DARK_TEXT} !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: #9898B0 !important;
        }}
    </style>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────
def render_header():
    logo_b64 = get_logo_base64()
    logo_html = f'<div class="tag-logo-box"><img src="data:image/png;base64,{logo_b64}"></div>' if logo_b64 else ""

    # Data da última atualização: ler a data mais recente dos próprios dados de cotas
    data_atualizacao = "—"
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    cotas_path = os.path.join(data_dir, "cotas_consolidado.parquet")
    if os.path.exists(cotas_path):
        try:
            import pyarrow.parquet as pq
            pf = pq.read_table(cotas_path, columns=["data"])
            col_data = pf.column("data").to_pylist()
            if col_data:
                max_dt = max(col_data)
                if hasattr(max_dt, "strftime"):
                    data_atualizacao = max_dt.strftime("%d/%m/%Y")
                else:
                    data_atualizacao = str(max_dt)[:10]
        except Exception:
            data_atualizacao = "—"

    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 0;">
        <div class="tag-header">
            {logo_html}
            <div class="tag-header-text">
                <h1>Carteira RV</h1>
                <p>Monitoramento de Fundos de Renda Variavel</p>
            </div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.65rem; color: {DARK_TEXT_MUTED}; text-transform: uppercase;
                        letter-spacing: 1px; font-weight: 600;">Dados ate</div>
            <div style="font-size: 0.85rem; color: {DARK_TEXT}; font-weight: 700;
                        margin-top: 2px; font-family: 'Inter', monospace;">{data_atualizacao}</div>
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
    """Aplica layout dark futurista a um gráfico Plotly."""
    legend = dict(
        orientation="h", yanchor="bottom", y=1.02,
        font=dict(size=10, color=DARK_TEXT_MUTED, family="Inter, sans-serif"),
        bgcolor="rgba(0,0,0,0)",
    ) if legend_h else dict(
        font=dict(size=10, color=DARK_TEXT_MUTED, family="Inter, sans-serif")
    )

    grid_color = "#1E1E2E"  # grid sutil no dark

    layout_kwargs = dict(
        height=height, template="plotly_dark",
        xaxis=dict(
            tickfont=dict(size=9, color=DARK_TEXT_MUTED),
            gridcolor=grid_color, gridwidth=1,
            linecolor=DARK_BORDER, linewidth=1,
        ),
        legend=legend,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=50, r=16, t=50 if title else 30, b=margin_b),
        font=dict(family="Inter, sans-serif", color=DARK_TEXT),
        hoverlabel=dict(
            bgcolor=DARK_SURFACE, font_size=12,
            font_color=DARK_TEXT,
            bordercolor=_hex_to_rgba(TAG_LARANJA, 0.4),
        ),
        hovermode="x unified",
    )
    if title:
        layout_kwargs["title"] = dict(text=title, font=dict(size=13, color=TAG_LARANJA, family="Inter, sans-serif"))
    if y_title:
        layout_kwargs["yaxis"] = dict(
            title=dict(text=y_title, font=dict(size=10, color=DARK_TEXT_MUTED)),
            ticksuffix=y_suffix,
            tickfont=dict(size=9, color=DARK_TEXT_MUTED),
            gridcolor=grid_color, gridwidth=1,
            zeroline=True, zerolinecolor="#2A2A3A", zerolinewidth=1,
            linecolor=DARK_BORDER, linewidth=1,
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
        # Cor da barra gradiente
        if row["pct_pl"] >= max_pct * 0.5:
            bar_color = TAG_LARANJA
        elif row["pct_pl"] >= max_pct * 0.25:
            bar_color = "#5C85F7"
        else:
            bar_color = "#58C6F5"

        rank = i + 1
        zebra = DARK_SURFACE_2 if i % 2 == 1 else DARK_SURFACE

        rows_html += f"""
        <tr style="background: {zebra}; transition: background 0.2s;">
            <td style="padding: 10px 14px; text-align: center; font-weight: 600; color: {DARK_TEXT_MUTED}; font-size: 12px; width: 40px;">{rank}</td>
            <td style="padding: 10px 14px; font-weight: 700; color: {DARK_TEXT}; font-size: 14px; white-space: nowrap;">
                {row['Ativo']}
            </td>
            <td style="padding: 10px 14px; color: {DARK_TEXT_MUTED}; font-size: 13px;">{row['Setor']}</td>
            <td style="padding: 10px 14px; text-align: right; font-family: 'Inter', monospace; font-size: 13px; color: {DARK_TEXT};">
                {row['Valor']}
            </td>
            <td style="padding: 10px 14px; width: 200px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="flex: 1; background: {DARK_BORDER}; border-radius: 4px; height: 18px; overflow: hidden;">
                        <div style="width: {bar_width}%; height: 100%; background: linear-gradient(90deg, {bar_color}, {TAG_LARANJA}80); border-radius: 4px; transition: width 0.3s;"></div>
                    </div>
                    <span style="font-weight: 700; font-size: 13px; color: {DARK_TEXT}; min-width: 52px; text-align: right;">
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
        <tr style="background: {DARK_SURFACE};">
            <td colspan="5" style="padding: 8px 14px; font-size: 10px; color: {DARK_TEXT_MUTED}; text-align: center;">
                * O % PL e calculado sobre o patrimonio total do fundo. Fundos com posicoes em renda fixa, caixa ou derivativos terao alocacao em acoes inferior a 100%.
            </td>
        </tr>"""

    html = f"""
    <div style="border-radius: 12px; overflow: hidden; border: 1px solid {DARK_BORDER}; margin: 8px 0 16px 0; background: {DARK_SURFACE};">
        <table style="width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif;">
            <thead>
                <tr style="background: {DARK_SURFACE_2}; border-bottom: 1px solid {DARK_BORDER};">
                    <th style="padding: 10px 14px; color: {TAG_LARANJA}; font-size: 10px; font-weight: 700; text-align: center; width: 36px; text-transform: uppercase; letter-spacing: 0.8px;">#</th>
                    <th style="padding: 10px 14px; color: {TAG_LARANJA}; font-size: 10px; font-weight: 700; text-align: left; text-transform: uppercase; letter-spacing: 0.8px;">Ativo</th>
                    <th style="padding: 10px 14px; color: {TAG_LARANJA}; font-size: 10px; font-weight: 700; text-align: left; text-transform: uppercase; letter-spacing: 0.8px;">Setor</th>
                    <th style="padding: 10px 14px; color: {TAG_LARANJA}; font-size: 10px; font-weight: 700; text-align: right; text-transform: uppercase; letter-spacing: 0.8px;">Valor</th>
                    <th style="padding: 10px 14px; color: {TAG_LARANJA}; font-size: 10px; font-weight: 700; text-align: left; width: 200px; text-transform: uppercase; letter-spacing: 0.8px;">% PL</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
            <tfoot>
                <tr style="background: {DARK_SURFACE_2}; border-top: 1px solid {DARK_BORDER};">
                    <td colspan="4" style="padding: 10px 14px; font-weight: 600; color: {DARK_TEXT_MUTED}; font-size: 12px; text-align: right;">
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
    tab_ativo, tab_setor, tab_pl, tab_comparativo, tab_perf, tab_destaques = st.tabs([
        "Por Ativo", "Por Setor", "Evolucao PL", "Comparativo", "Performance", "Destaques"
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
                textfont=dict(size=11, color=DARK_TEXT),
                colorscale=[
                    [0, DARK_SURFACE_2], [0.25, "#2A3060"],
                    [0.5, "#3f51b5"], [0.75, "#5C85F7"],
                    [1, "#58C6F5"]
                ],
                hovertemplate="<b>%{y}</b> x <b>%{x}</b><br>Sobreposicao: %{text}<extra></extra>",
                showscale=True,
                colorbar=dict(title="% PL", ticksuffix="%", tickfont=dict(color=DARK_TEXT_MUTED)),
            ))
            fig_heat_a.update_layout(
                height=max(420, 70 * n + 140),
                template="plotly_dark",
                xaxis=dict(tickangle=45, side="bottom", tickfont=dict(color=DARK_TEXT_MUTED)),
                yaxis=dict(autorange="reversed", tickfont=dict(color=DARK_TEXT_MUTED)),
                font=dict(family="Inter, sans-serif", size=11, color=DARK_TEXT),
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
                textfont=dict(size=11, color=DARK_TEXT),
                colorscale=[
                    [0, DARK_SURFACE_2], [0.25, "#3D1520"],
                    [0.5, "#7A1E35"], [0.75, "#B44A5E"],
                    [1, TAG_LARANJA]
                ],
                hovertemplate="<b>%{y}</b> x <b>%{x}</b><br>Sobreposicao: %{text}<extra></extra>",
                showscale=True,
                colorbar=dict(title="% PL", ticksuffix="%", tickfont=dict(color=DARK_TEXT_MUTED)),
            ))
            fig_heat_s.update_layout(
                height=max(420, 70 * n + 140),
                template="plotly_dark",
                xaxis=dict(tickangle=45, side="bottom", tickfont=dict(color=DARK_TEXT_MUTED)),
                yaxis=dict(autorange="reversed", tickfont=dict(color=DARK_TEXT_MUTED)),
                font=dict(family="Inter, sans-serif", size=11, color=DARK_TEXT),
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
                    yaxis=dict(title="% do PL", ticksuffix="%", gridcolor="#1E1E2E",
                               tickfont=dict(color=DARK_TEXT_MUTED)),
                    xaxis=dict(tickfont=dict(color=DARK_TEXT_MUTED)),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", color=DARK_TEXT),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                font=dict(size=10, color=DARK_TEXT_MUTED)),
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
                                xaxis=dict(title=dict(text="Downside Capture (%)", font=dict(size=10, color=DARK_TEXT_MUTED)),
                                           ticksuffix="%", tickfont=dict(size=9, color=DARK_TEXT_MUTED), gridcolor="#1E1E2E"),
                                yaxis=dict(title=dict(text="Upside Capture (%)", font=dict(size=10, color=DARK_TEXT_MUTED)),
                                           ticksuffix="%", tickfont=dict(size=9, color=DARK_TEXT_MUTED), gridcolor="#1E1E2E"),
                                font=dict(family="Inter, sans-serif", color=DARK_TEXT),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10, color=DARK_TEXT_MUTED)),
                                margin=dict(l=50, r=16, t=40, b=50),
                                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                hoverlabel=dict(bgcolor=DARK_SURFACE, font_size=12, bordercolor=_hex_to_rgba(TAG_LARANJA, 0.4)),
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
                        # Faixas de referência (dark)
                        fig_te.add_hrect(y0=0, y1=2, fillcolor="rgba(42,42,58,0.5)", line_width=0, layer="below")
                        fig_te.add_hrect(y0=2, y1=8, fillcolor="rgba(92,133,247,0.06)", line_width=0, layer="below")
                        fig_te.add_hline(y=2, line_dash="dot", line_color="#3A3A4A", line_width=1, annotation_text="Closet Indexer", annotation_position="top left", annotation_font_color=DARK_TEXT_MUTED)
                        fig_te.add_hline(y=8, line_dash="dot", line_color="#3A3A4A", line_width=1, annotation_text="Alta Convicção", annotation_position="top left", annotation_font_color=DARK_TEXT_MUTED)

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
                            height=480, template="plotly_dark",
                            xaxis=dict(title=dict(text="Ulcer Index (risco)", font=dict(size=10, color=DARK_TEXT_MUTED)),
                                       zeroline=True, tickfont=dict(size=9, color=DARK_TEXT_MUTED), gridcolor="#1E1E2E"),
                            yaxis=dict(title=dict(text="Retorno Anualizado (%)", font=dict(size=10, color=DARK_TEXT_MUTED)),
                                       ticksuffix="%", tickfont=dict(size=9, color=DARK_TEXT_MUTED), gridcolor="#1E1E2E"),
                            font=dict(family="Inter, sans-serif", color=DARK_TEXT),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10, color=DARK_TEXT_MUTED)),
                            margin=dict(l=50, r=16, t=40, b=50),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            hoverlabel=dict(bgcolor=DARK_SURFACE, font_size=12, bordercolor=_hex_to_rgba(TAG_LARANJA, 0.4)),
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

                        # UPI vs IBOV: (excess return) / ulcer index
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
                            "Max DD": f"{max_dd:.1f}%",
                            "Calmar": f"{calmar:.2f}",
                            "Ulcer": f"{ulcer:.1f}",
                            "UPI vs IBOV": f"{upi_vs_ibov:.2f}" if pd.notna(upi_vs_ibov) else "—",
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

                        fig_upi.add_hline(y=0, line_dash="dot", line_color="#ccc", line_width=1)
                        _chart_layout(fig_upi, "", height=400, y_title="UPI vs IBOV", y_suffix="")
                        st.plotly_chart(fig_upi, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 6: DESTAQUES (Rankings multi-janela — inspirado relatório RV Long Only)
    # ══════════════════════════════════════════════════════════════════════
    with tab_destaques:
        all_cnpjs_destaques = tuple(set(df_fundos["cnpj_norm"].dropna().tolist()))
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
                    st.caption(f"Amostra de {len(df_funds_only)} fundos de acoes. Data ref: {max_date.strftime('%d/%m/%Y')}.")

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

                    # Calcular quartis para highlight
                    quartis = {}
                    for col in janelas_disp:
                        vals = df_funds_only[col].dropna()
                        if len(vals) >= 4:
                            quartis[col] = {
                                "q1": vals.quantile(0.75),
                                "q2": vals.quantile(0.50),
                                "q3": vals.quantile(0.25),
                            }

                    def _quartil_color(val, col):
                        if col not in quartis:
                            return ""
                        q = quartis[col]
                        if val >= q["q1"]:
                            return "background: rgba(107,222,151,0.15); color: #6BDE97;"
                        elif val >= q["q2"]:
                            return "background: rgba(255,187,0,0.1); color: #FFBB00;"
                        elif val >= q["q3"]:
                            return "background: rgba(255,136,83,0.1); color: #FF8853;"
                        else:
                            return "background: rgba(255,60,60,0.1); color: #FF6B6B;"

                    # Build summary table HTML
                    th_cells = "".join(f'<th style="padding:10px 12px; text-align:right; color:{TAG_LARANJA}; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.8px;">{j}</th>' for j in janelas_disp)
                    summary_html = f"""
                    <div style="border-radius:12px; overflow:hidden; border:1px solid {DARK_BORDER}; background:{DARK_SURFACE}; margin:8px 0 24px 0;">
                    <table style="width:100%; border-collapse:collapse; font-family:'Inter',sans-serif;">
                    <thead><tr style="background:{DARK_SURFACE_2}; border-bottom:1px solid {DARK_BORDER};">
                        <th style="padding:10px 14px; text-align:left; color:{TAG_LARANJA}; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; min-width:180px;">—</th>
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
                        ("Mediana", lambda s: s.median(), DARK_TEXT),
                        ("Media", lambda s: s.mean(), DARK_TEXT_MUTED),
                        ("Media Bottom 20", lambda s: s.nsmallest(min(20, len(s))).mean(), "#FF6B6B"),
                    ])

                    for sr_label, sr_fn, sr_color in stat_rows:
                        cells = ""
                        for col in janelas_disp:
                            if sr_fn is not None:
                                vals = df_funds_only[col].dropna()
                                if vals.empty:
                                    cells += f'<td style="padding:8px 12px; text-align:right; color:{DARK_TEXT_MUTED};">—</td>'
                                    continue
                                v = sr_fn(vals)
                            else:
                                # Benchmark: BENCHMARK_CNPJS maps name→cnpj
                                b_cnpj = [cnpj_v for name_k, cnpj_v in BENCHMARK_CNPJS.items() if name_k == sr_label]
                                if b_cnpj and b_cnpj[0] in df_ret_all.index and col in df_ret_all.columns:
                                    v = df_ret_all.loc[b_cnpj[0], col]
                                    if pd.isna(v):
                                        cells += f'<td style="padding:8px 12px; text-align:right; color:{DARK_TEXT_MUTED};">—</td>'
                                        continue
                                else:
                                    cells += f'<td style="padding:8px 12px; text-align:right; color:{DARK_TEXT_MUTED};">—</td>'
                                    continue
                            neg = "color:#FF6B6B;" if v < 0 else ""
                            cells += f'<td style="padding:8px 12px; text-align:right; font-weight:600; font-size:13px; {neg} color:{sr_color};">{v:.1f}%</td>'
                        summary_html += f'<tr style="border-bottom:1px solid {DARK_BORDER}60;"><td style="padding:8px 14px; font-weight:600; font-size:13px; color:{sr_color};">{sr_label}</td>{cells}</tr>'

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

                    # ── 3. Top 20 e Bottom 20 ──
                    col_top, col_bot = st.columns(2)

                    # Helper: render benchmark rows for top/bottom tables
                    def _render_bench_rows(janelas_disp_inner, janela_rank_inner):
                        bench_html = ""
                        for b_name, b_cnpj in BENCHMARK_CNPJS.items():
                            if b_cnpj not in df_ret_all.index:
                                continue
                            bench_html += f'<tr style="background:rgba(88,198,245,0.06);border-bottom:2px solid {DARK_BORDER};">'
                            bench_html += f'<td style="padding:6px 10px;text-align:center;color:#58C6F5;font-size:10px;font-weight:700;">▸</td>'
                            bench_html += f'<td style="padding:6px 10px;font-size:12px;color:#58C6F5;font-weight:700;white-space:nowrap;">{b_name}</td>'
                            for jcol in janelas_disp_inner:
                                v = df_ret_all.loc[b_cnpj, jcol] if jcol in df_ret_all.columns else np.nan
                                if pd.isna(v):
                                    bench_html += f'<td style="padding:6px 8px;text-align:right;color:{DARK_TEXT_MUTED};font-size:11px;">—</td>'
                                else:
                                    neg = "color:#FF6B6B;" if v < 0 else ""
                                    bold = "font-weight:700;" if jcol == janela_rank_inner else ""
                                    bench_html += f'<td style="padding:6px 8px;text-align:right;font-size:11px;color:#58C6F5;{neg}{bold}">{v:.1f}%</td>'
                            bench_html += '</tr>'
                        return bench_html

                    with col_top:
                        st.markdown(f'<div class="tag-section-title" style="color:#6BDE97;">Melhores — {janela_rank}</div>', unsafe_allow_html=True)
                        top20 = df_funds_only.nlargest(20, janela_rank)[[janela_rank, "nome"]].copy()
                        top20 = top20.dropna(subset=[janela_rank])

                        top_html = f'<div style="border-radius:12px; overflow:hidden; border:1px solid {DARK_BORDER}; background:{DARK_SURFACE};">'
                        top_html += f'<table style="width:100%; border-collapse:collapse; font-family:Inter,sans-serif;">'
                        top_html += f'<thead><tr style="background:{DARK_SURFACE_2};border-bottom:1px solid {DARK_BORDER};">'
                        top_html += f'<th style="padding:8px 10px;color:{TAG_LARANJA};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;width:30px;">#</th>'
                        top_html += f'<th style="padding:8px 10px;color:{TAG_LARANJA};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;">Fundo</th>'

                        for jcol in janelas_disp:
                            bold = "font-weight:800;" if jcol == janela_rank else ""
                            top_html += f'<th style="padding:8px 8px;color:{TAG_LARANJA};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;text-align:right;{bold}">{jcol}</th>'
                        top_html += '</tr></thead><tbody>'

                        # Benchmark rows first (reference)
                        top_html += _render_bench_rows(janelas_disp, janela_rank)

                        for rank_i, (cnpj_row, row) in enumerate(top20.iterrows()):
                            is_selected = cnpj_row in sel_cnpjs_set
                            bg = f"background:rgba(107,222,151,0.08);" if is_selected else ""
                            name_style = f"color:{TAG_LARANJA};font-weight:700;" if is_selected else f"color:{DARK_TEXT};"
                            zb = f"background:{DARK_SURFACE_2};" if rank_i % 2 == 1 and not is_selected else ""
                            top_html += f'<tr style="{bg}{zb}border-bottom:1px solid {DARK_BORDER}40;">'
                            top_html += f'<td style="padding:6px 10px;text-align:center;color:{DARK_TEXT_MUTED};font-size:11px;font-weight:600;">{rank_i+1}</td>'
                            nome_short = row["nome"][:35] + "..." if len(row["nome"]) > 35 else row["nome"]
                            top_html += f'<td style="padding:6px 10px;font-size:12px;{name_style}white-space:nowrap;">{nome_short}</td>'

                            for jcol in janelas_disp:
                                v = df_ret_all.loc[cnpj_row, jcol] if cnpj_row in df_ret_all.index and jcol in df_ret_all.columns else np.nan
                                if pd.isna(v):
                                    top_html += f'<td style="padding:6px 8px;text-align:right;color:{DARK_TEXT_MUTED};font-size:11px;">—</td>'
                                else:
                                    qstyle = _quartil_color(v, jcol)
                                    neg = "color:#FF6B6B;" if v < 0 else ""
                                    bold = "font-weight:700;" if jcol == janela_rank else ""
                                    top_html += f'<td style="padding:6px 8px;text-align:right;font-size:11px;{qstyle}{neg}{bold}border-radius:4px;">{v:.1f}%</td>'
                            top_html += '</tr>'
                        top_html += '</tbody></table></div>'
                        st.html(top_html)

                    with col_bot:
                        st.markdown(f'<div class="tag-section-title" style="color:#FF6B6B;">Piores — {janela_rank}</div>', unsafe_allow_html=True)
                        bot20 = df_funds_only.nsmallest(20, janela_rank)[[janela_rank, "nome"]].copy()
                        bot20 = bot20.dropna(subset=[janela_rank])

                        bot_html = f'<div style="border-radius:12px; overflow:hidden; border:1px solid {DARK_BORDER}; background:{DARK_SURFACE};">'
                        bot_html += f'<table style="width:100%; border-collapse:collapse; font-family:Inter,sans-serif;">'
                        bot_html += f'<thead><tr style="background:{DARK_SURFACE_2};border-bottom:1px solid {DARK_BORDER};">'
                        bot_html += f'<th style="padding:8px 10px;color:{TAG_LARANJA};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;width:30px;">#</th>'
                        bot_html += f'<th style="padding:8px 10px;color:{TAG_LARANJA};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;">Fundo</th>'
                        for jcol in janelas_disp:
                            bold = "font-weight:800;" if jcol == janela_rank else ""
                            bot_html += f'<th style="padding:8px 8px;color:{TAG_LARANJA};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;text-align:right;{bold}">{jcol}</th>'
                        bot_html += '</tr></thead><tbody>'

                        # Benchmark rows first (reference)
                        bot_html += _render_bench_rows(janelas_disp, janela_rank)

                        for rank_i, (cnpj_row, row) in enumerate(bot20.iterrows()):
                            is_selected = cnpj_row in sel_cnpjs_set
                            bg = f"background:rgba(255,60,60,0.08);" if is_selected else ""
                            name_style = f"color:{TAG_LARANJA};font-weight:700;" if is_selected else f"color:{DARK_TEXT};"
                            zb = f"background:{DARK_SURFACE_2};" if rank_i % 2 == 1 and not is_selected else ""
                            bot_html += f'<tr style="{bg}{zb}border-bottom:1px solid {DARK_BORDER}40;">'
                            bot_html += f'<td style="padding:6px 10px;text-align:center;color:{DARK_TEXT_MUTED};font-size:11px;font-weight:600;">{rank_i+1}</td>'
                            nome_short = row["nome"][:35] + "..." if len(row["nome"]) > 35 else row["nome"]
                            bot_html += f'<td style="padding:6px 10px;font-size:12px;{name_style}white-space:nowrap;">{nome_short}</td>'

                            for jcol in janelas_disp:
                                v = df_ret_all.loc[cnpj_row, jcol] if cnpj_row in df_ret_all.index and jcol in df_ret_all.columns else np.nan
                                if pd.isna(v):
                                    bot_html += f'<td style="padding:6px 8px;text-align:right;color:{DARK_TEXT_MUTED};font-size:11px;">—</td>'
                                else:
                                    qstyle = _quartil_color(v, jcol)
                                    neg = "color:#FF6B6B;" if v < 0 else ""
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
                                q_color = "#FF6B6B"

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
                                    <div class="value" style="font-size:2rem;">{sr['pos']}<span style="font-size:0.9rem;color:{DARK_TEXT_MUTED};">/{sr['total']}</span></div>
                                    <div style="margin-top:8px;display:flex;justify-content:center;gap:12px;align-items:center;">
                                        <span style="background:{sr['q_color']}20;color:{sr['q_color']};padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;">{sr['q_label']}</span>
                                        <span style="color:{DARK_TEXT_MUTED};font-size:12px;">{ret_str} ({janela_rank})</span>
                                    </div>
                                    <div style="margin-top:8px;">
                                        <div style="background:{DARK_BORDER};border-radius:4px;height:6px;overflow:hidden;">
                                            <div style="width:{sr['pctl']:.0f}%;height:100%;background:linear-gradient(90deg,{sr['q_color']},{TAG_LARANJA});border-radius:4px;"></div>
                                        </div>
                                        <div style="font-size:10px;color:{DARK_TEXT_MUTED};margin-top:3px;">Percentil {sr['pctl']:.0f}%</div>
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
                                                   annotation_font_color=DARK_TEXT, annotation_font_size=10)

                        # Marcar benchmarks
                        for b_name, b_cnpj in BENCHMARK_CNPJS.items():
                            if b_cnpj in df_ret_all.index and janela_rank in df_ret_all.columns:
                                bv = df_ret_all.loc[b_cnpj, janela_rank]
                                if pd.notna(bv):
                                    fig_hist.add_vline(x=bv, line_dash="dot", line_color="#58C6F5", line_width=1.5,
                                                       annotation_text=b_name.split("(")[0].strip()[:10],
                                                       annotation_position="top",
                                                       annotation_font_color=DARK_TEXT_MUTED, annotation_font_size=9)

                        _chart_layout(fig_hist, "", height=350, y_title="Qtd. Fundos", y_suffix="")
                        st.plotly_chart(fig_hist, use_container_width=True)


if __name__ == "__main__":
    main()
