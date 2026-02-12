import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.figure_factory as ff
import os
import base64

from data_loader import carregar_todos_dados, carregar_fundos_rv

# ──────────────────────────────────────────────────────────────────────────────
# Paleta TAG Investimentos
# ──────────────────────────────────────────────────────────────────────────────
TAG_VERMELHO = "#630D24"
TAG_OFFWHITE = "#E6E4DB"
TAG_LARANJA = "#FF8853"
TAG_BRANCO = "#FFFFFF"
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
# Logo: tentar local primeiro, depois fallback para assets/
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
            font-size: 14px !important; font-weight: 700 !important;
            padding: 10px 14px !important;
            background: {TAG_VERMELHO} !important; color: {TAG_BRANCO} !important;
        }}
        .stDataFrame td {{ padding: 8px 14px !important; }}
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
        .tag-metric-card {{
            background: {TAG_BRANCO}; border-radius: 12px;
            padding: 24px 18px; text-align: center;
            border-left: 5px solid {TAG_VERMELHO};
            box-shadow: 0 2px 12px rgba(0,0,0,0.07);
        }}
        .tag-metric-card .value {{
            font-size: 2.4rem; font-weight: 700;
            color: {TAG_VERMELHO}; line-height: 1;
        }}
        .tag-metric-card .label {{
            font-size: 0.95rem; color: #777; margin-top: 8px; font-weight: 500;
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
def metric_card(label, value, extra_class=""):
    return f"""
    <div class="tag-metric-card {extra_class}">
        <div class="value">{value}</div>
        <div class="label">{label}</div>
    </div>
    """


# ──────────────────────────────────────────────────────────────────────────────
# Gráficos
# ──────────────────────────────────────────────────────────────────────────────
def _hex_to_rgba(hex_color, alpha=0.8):
    """Converte hex (#RRGGBB) para rgba() string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def grafico_stacked_area(df_pivot, titulo, top_n=15):
    """Stacked area chart Plotly."""
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
            hovertemplate=f"<b>{col}</b><br>%{{y:.1f}}%<extra></extra>",
        ))

    if outros:
        df_outros = df_pivot[outros].sum(axis=1)
        fig.add_trace(go.Scatter(
            x=df_pivot.index, y=df_outros,
            name="Outros", stackgroup="one",
            line=dict(width=0.5, color="#CCCCCC"),
            fillcolor="rgba(204,204,204,0.6)",
        ))

    fig.update_layout(
        title=dict(text=titulo, font=dict(size=18, color=TAG_VERMELHO)),
        height=500, template="plotly_white",
        yaxis=dict(title="% do PL", ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11)),
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=60, b=40),
        font=dict(family="Tahoma, sans-serif"),
    )
    return fig


def grafico_linhas(df_pivot, titulo, top_n=15):
    """Line chart individual por coluna."""
    media = df_pivot.mean().sort_values(ascending=False)
    top_cols = media.head(top_n).index.tolist()

    fig = go.Figure()
    for i, col in enumerate(top_cols):
        fig.add_trace(go.Scatter(
            x=df_pivot.index, y=df_pivot[col],
            name=col, mode="lines+markers",
            line=dict(width=2, color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)]),
            marker=dict(size=4),
            hovertemplate=f"<b>{col}</b><br>%{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text=titulo, font=dict(size=18, color=TAG_VERMELHO)),
        height=500, template="plotly_white",
        yaxis=dict(title="% do PL", ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11)),
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=60, b=40),
        font=dict(family="Tahoma, sans-serif"),
    )
    return fig


def grafico_pl(df_pl, titulo):
    """Line chart de PL ao longo do tempo."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_pl["data"], y=df_pl["pl"] / 1e6,
        mode="lines+markers",
        line=dict(width=2.5, color=TAG_VERMELHO),
        marker=dict(size=5),
        fill="tozeroy", fillcolor=_hex_to_rgba(TAG_VERMELHO, 0.1),
        hovertemplate="<b>%{x|%b/%Y}</b><br>R$ %{y:.1f}M<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=18, color=TAG_VERMELHO)),
        height=400, template="plotly_white",
        yaxis=dict(title="PL (R$ milhoes)"),
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=60, b=40),
        font=dict(family="Tahoma, sans-serif"),
    )
    return fig


def grafico_n_ativos(df_n, titulo):
    """Bar chart de numero de ativos."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_n["data"], y=df_n["n_ativos"],
        marker_color=TAG_LARANJA,
        hovertemplate="<b>%{x|%b/%Y}</b><br>%{y} ativos<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=18, color=TAG_VERMELHO)),
        height=400, template="plotly_white",
        yaxis=dict(title="Qtd. Ativos"),
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=60, b=40),
        font=dict(family="Tahoma, sans-serif"),
    )
    return fig


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
    """Retorna tabela da carteira mais recente."""
    d = df[df["cnpj_fundo"] == cnpj].copy()
    if d.empty:
        return pd.DataFrame()
    ultima_data = d["data"].max()
    d = d[d["data"] == ultima_data].copy()
    d = d.sort_values("pct_pl", ascending=False)
    d["pct_pl_fmt"] = d["pct_pl"].map(lambda x: f"{x:.2f}%")
    d["valor_fmt"] = d["valor"].map(lambda x: f"R$ {x:,.0f}".replace(",", "."))
    return d[["ativo", "setor", "valor_fmt", "pct_pl_fmt"]].rename(columns={
        "ativo": "Ativo", "setor": "Setor", "valor_fmt": "Valor", "pct_pl_fmt": "% PL"
    }).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    inject_css()
    render_header()

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

    # Filtrar fundos disponíveis
    df_fundos_filtrado = df_fundos.copy()
    if cat_sel:
        df_fundos_filtrado = df_fundos_filtrado[df_fundos_filtrado["categoria"].isin(cat_sel)]
    if tier_sel:
        df_fundos_filtrado = df_fundos_filtrado[df_fundos_filtrado["tier"].isin(tier_sel)]

    # Apenas fundos que possuem dados
    cnpjs_com_dados = set(df_posicoes["cnpj_fundo"].unique())
    df_fundos_filtrado = df_fundos_filtrado[df_fundos_filtrado["cnpj_norm"].isin(cnpjs_com_dados)]

    # Mapa nome -> cnpj
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

    # Filtrar posições
    df_pos = df_posicoes[df_posicoes["cnpj_fundo"].isin(cnpjs_sel)].copy()

    # ── Tabs ──
    tab_ativo, tab_setor, tab_pl, tab_comparativo = st.tabs([
        "Por Ativo", "Por Setor", "Evolucao PL", "Comparativo"
    ])

    # ══════════════════════════════════════════════════════════════════════
    # TAB 1: POR ATIVO
    # ══════════════════════════════════════════════════════════════════════
    with tab_ativo:
        for nome_fundo in fundos_sel:
            cnpj = nome_cnpj_map[nome_fundo]
            df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]

            if df_f.empty:
                st.warning(f"Sem dados para {nome_fundo}")
                continue

            st.markdown(f"### {nome_fundo}")

            # Métricas
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
                    st.markdown(metric_card("Top Holding", f"{top_ativo['ativo']} ({top_ativo['pct_pl']:.1f}%)"), unsafe_allow_html=True)
            with c4:
                st.markdown(metric_card("Fonte / Data", f"{fonte} {dt_ref}"), unsafe_allow_html=True)

            st.markdown("")

            # Tabela atual
            tbl = tabela_carteira_atual(df_pos, cnpj)
            if not tbl.empty:
                with st.expander("Carteira Atual (detalhada)", expanded=False):
                    st.dataframe(tbl, width="stretch", hide_index=True)

            # Stacked area
            pivot = preparar_pivot_ativo(df_pos, cnpj)
            if not pivot.empty:
                st.plotly_chart(
                    grafico_stacked_area(pivot, f"{nome_fundo} - Composicao por Ativo"),
                    width="stretch",
                )
                st.plotly_chart(
                    grafico_linhas(pivot, f"{nome_fundo} - Evolucao por Ativo"),
                    width="stretch",
                )

            st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════
    # TAB 2: POR SETOR
    # ══════════════════════════════════════════════════════════════════════
    with tab_setor:
        for nome_fundo in fundos_sel:
            cnpj = nome_cnpj_map[nome_fundo]
            df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]

            if df_f.empty:
                st.warning(f"Sem dados para {nome_fundo}")
                continue

            st.markdown(f"### {nome_fundo}")

            # Tabela setorial atual
            ultima_data = df_f["data"].max()
            setor_atual = df_f[df_f["data"] == ultima_data].groupby("setor")["pct_pl"].sum().sort_values(ascending=False)
            setor_df = setor_atual.reset_index()
            setor_df.columns = ["Setor", "% PL"]
            setor_df["% PL"] = setor_df["% PL"].map(lambda x: f"{x:.1f}%")
            with st.expander("Alocacao Setorial Atual", expanded=False):
                st.dataframe(setor_df, width="stretch", hide_index=True)

            # Charts
            pivot_s = preparar_pivot_setor(df_pos, cnpj)
            if not pivot_s.empty:
                st.plotly_chart(
                    grafico_stacked_area(pivot_s, f"{nome_fundo} - Composicao por Setor", top_n=20),
                    width="stretch",
                )
                st.plotly_chart(
                    grafico_linhas(pivot_s, f"{nome_fundo} - Evolucao por Setor", top_n=20),
                    width="stretch",
                )

            st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════
    # TAB 3: EVOLUÇÃO PL
    # ══════════════════════════════════════════════════════════════════════
    with tab_pl:
        for nome_fundo in fundos_sel:
            cnpj = nome_cnpj_map[nome_fundo]
            df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]

            if df_f.empty:
                continue

            st.markdown(f"### {nome_fundo}")

            pl_mensal = df_f.groupby("data")["pl"].first().reset_index()
            st.plotly_chart(
                grafico_pl(pl_mensal, f"{nome_fundo} - Patrimonio Liquido"),
                width="stretch",
            )

            # Numero de ativos
            n_ativos = df_f.groupby("data")["ativo"].nunique().reset_index()
            n_ativos.columns = ["data", "n_ativos"]
            st.plotly_chart(
                grafico_n_ativos(n_ativos, f"{nome_fundo} - Numero de Ativos"),
                width="stretch",
            )

            st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════
    # TAB 4: COMPARATIVO
    # ══════════════════════════════════════════════════════════════════════
    with tab_comparativo:
        if len(fundos_sel) < 2:
            st.info("Selecione 2 ou mais fundos para ver o comparativo.")
        else:
            # ── Preparar dados da carteira mais recente de cada fundo ──
            carteiras = {}   # nome_curto -> {ativo: pct_pl}
            setores_map = {} # nome_curto -> {setor: pct_pl}
            nomes_curtos = []
            for nome_fundo in fundos_sel:
                cnpj = nome_cnpj_map[nome_fundo]
                df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]
                if df_f.empty:
                    continue
                ultima = df_f["data"].max()
                df_ult = df_f[df_f["data"] == ultima]
                short = nome_fundo  # nome completo para clareza
                nomes_curtos.append(short)
                carteiras[short] = dict(zip(df_ult["ativo"], df_ult["pct_pl"]))
                setores_map[short] = df_ult.groupby("setor")["pct_pl"].sum().to_dict()

            if len(nomes_curtos) >= 2:
                # ─── HEATMAP: Sobreposicao por Ativos ───
                st.markdown("### Sobreposicao de Participacao por Ativo (%)")
                st.caption("Cada celula mostra a soma dos % do PL dos ativos que os dois fundos tem em comum.")

                n = len(nomes_curtos)
                overlap_ativos = np.zeros((n, n))
                for i in range(n):
                    for j in range(n):
                        common_tickers = set(carteiras[nomes_curtos[i]].keys()) & set(carteiras[nomes_curtos[j]].keys())
                        if i == j:
                            # Diagonal: soma total do fundo em ativos
                            overlap_ativos[i][j] = 0.0
                        else:
                            # Soma do min(%) entre os dois fundos para cada ativo em comum
                            total = 0.0
                            for tk in common_tickers:
                                total += min(carteiras[nomes_curtos[i]][tk], carteiras[nomes_curtos[j]][tk])
                            overlap_ativos[i][j] = round(total, 1)

                # Criar texto das anotacoes
                text_ativos = [[f"{v:.1f}" for v in row] for row in overlap_ativos]

                fig_heat_ativo = go.Figure(data=go.Heatmap(
                    z=overlap_ativos,
                    x=nomes_curtos,
                    y=nomes_curtos,
                    text=text_ativos,
                    texttemplate="%{text}",
                    textfont=dict(size=12, color="black"),
                    colorscale=[[0, "#f7fbff"], [0.25, "#c6dbef"], [0.5, "#6baed6"], [0.75, "#2171b5"], [1, "#08306b"]],
                    hovertemplate="<b>%{y}</b> x <b>%{x}</b><br>Sobreposicao: %{z:.1f}%<extra></extra>",
                    showscale=True,
                    colorbar=dict(title="%"),
                ))
                fig_heat_ativo.update_layout(
                    title=dict(text="Sobreposicao por Ativo (% PL sobreposto)", font=dict(size=18, color=TAG_VERMELHO)),
                    height=max(400, 80 * n + 120),
                    template="plotly_white",
                    xaxis=dict(title="Fundos", tickangle=45),
                    yaxis=dict(title="Fundos", autorange="reversed"),
                    font=dict(family="Tahoma, sans-serif"),
                    margin=dict(l=20, r=20, t=60, b=120),
                )
                st.plotly_chart(fig_heat_ativo, width="stretch")

                # ─── HEATMAP: Sobreposicao por Setor ───
                st.markdown("### Sobreposicao de Participacao por Setor (%)")
                st.caption("Cada celula mostra a soma dos % do PL dos setores que os dois fundos tem em comum.")

                overlap_setores = np.zeros((n, n))
                for i in range(n):
                    for j in range(n):
                        common_sectors = set(setores_map[nomes_curtos[i]].keys()) & set(setores_map[nomes_curtos[j]].keys())
                        if i == j:
                            overlap_setores[i][j] = 0.0
                        else:
                            total = 0.0
                            for s in common_sectors:
                                total += min(setores_map[nomes_curtos[i]][s], setores_map[nomes_curtos[j]][s])
                            overlap_setores[i][j] = round(total, 1)

                text_setores = [[f"{v:.1f}" for v in row] for row in overlap_setores]

                fig_heat_setor = go.Figure(data=go.Heatmap(
                    z=overlap_setores,
                    x=nomes_curtos,
                    y=nomes_curtos,
                    text=text_setores,
                    texttemplate="%{text}",
                    textfont=dict(size=12, color="black"),
                    colorscale=[[0, "#fff5f0"], [0.25, "#fcbba1"], [0.5, "#fb6a4a"], [0.75, "#cb181d"], [1, "#67000d"]],
                    hovertemplate="<b>%{y}</b> x <b>%{x}</b><br>Sobreposicao: %{z:.1f}%<extra></extra>",
                    showscale=True,
                    colorbar=dict(title="%"),
                ))
                fig_heat_setor.update_layout(
                    title=dict(text="Sobreposicao por Setor (% PL sobreposto)", font=dict(size=18, color=TAG_VERMELHO)),
                    height=max(400, 80 * n + 120),
                    template="plotly_white",
                    xaxis=dict(title="Fundos", tickangle=45),
                    yaxis=dict(title="Fundos", autorange="reversed"),
                    font=dict(family="Tahoma, sans-serif"),
                    margin=dict(l=20, r=20, t=60, b=120),
                )
                st.plotly_chart(fig_heat_setor, width="stretch")

                # ─── BAR: Comparacao Setorial ───
                st.markdown("### Alocacao Setorial Comparada")

                setores_comp = []
                for nome_fundo in fundos_sel:
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

                    fig = go.Figure()
                    for i, col in enumerate(df_comp.columns):
                        fig.add_trace(go.Bar(
                            name=col,
                            x=df_comp.index,
                            y=df_comp[col],
                            marker_color=TAG_CHART_COLORS[i % len(TAG_CHART_COLORS)],
                            hovertemplate=f"<b>{col}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
                        ))

                    fig.update_layout(
                        barmode="group",
                        title=dict(text="Alocacao Setorial", font=dict(size=18, color=TAG_VERMELHO)),
                        height=500, template="plotly_white",
                        yaxis=dict(title="% do PL", ticksuffix="%"),
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Tahoma, sans-serif"),
                    )
                    st.plotly_chart(fig, width="stretch")

                # ─── SOBREPOSICAO HISTORICA ───
                st.markdown("### Sobreposicao Historica entre Fundos")
                st.caption("Evolucao da sobreposicao (% PL sobreposto por ativos em comum) ao longo do tempo para cada par de fundos.")

                # Para cada par de fundos, calcular sobreposicao em cada data
                pares = []
                for i in range(len(nomes_curtos)):
                    for j in range(i + 1, len(nomes_curtos)):
                        pares.append((nomes_curtos[i], nomes_curtos[j]))

                if pares:
                    # Coletar todas as datas disponíveis
                    fig_hist = go.Figure()
                    color_idx = 0

                    for nome_a, nome_b in pares:
                        cnpj_a = nome_cnpj_map[nome_a]
                        cnpj_b = nome_cnpj_map[nome_b]

                        df_a = df_pos[df_pos["cnpj_fundo"] == cnpj_a]
                        df_b = df_pos[df_pos["cnpj_fundo"] == cnpj_b]

                        # Datas em comum
                        dates_a = set(df_a["data"].unique())
                        dates_b = set(df_b["data"].unique())
                        common_dates = sorted(dates_a & dates_b)

                        if not common_dates:
                            continue

                        overlap_series = []
                        for dt in common_dates:
                            cart_a = dict(zip(
                                df_a[df_a["data"] == dt]["ativo"],
                                df_a[df_a["data"] == dt]["pct_pl"]
                            ))
                            cart_b = dict(zip(
                                df_b[df_b["data"] == dt]["ativo"],
                                df_b[df_b["data"] == dt]["pct_pl"]
                            ))
                            common_tk = set(cart_a.keys()) & set(cart_b.keys())
                            overlap = sum(min(cart_a[tk], cart_b[tk]) for tk in common_tk)
                            overlap_series.append(overlap)

                        # Truncar nomes para legenda
                        label_a = nome_a[:20] if len(nome_a) > 20 else nome_a
                        label_b = nome_b[:20] if len(nome_b) > 20 else nome_b
                        pair_label = f"{label_a} x {label_b}"

                        fig_hist.add_trace(go.Scatter(
                            x=common_dates,
                            y=overlap_series,
                            mode="lines+markers",
                            name=pair_label,
                            line=dict(width=2, color=TAG_CHART_COLORS[color_idx % len(TAG_CHART_COLORS)]),
                            marker=dict(size=4),
                            hovertemplate=f"<b>{pair_label}</b><br>%{{x|%b/%Y}}: %{{y:.1f}}%<extra></extra>",
                        ))
                        color_idx += 1

                    fig_hist.update_layout(
                        title=dict(text="Sobreposicao Historica por Ativos", font=dict(size=18, color=TAG_VERMELHO)),
                        height=500, template="plotly_white",
                        yaxis=dict(title="% PL Sobreposto", ticksuffix="%"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
                        plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=40, r=20, t=60, b=40),
                        font=dict(family="Tahoma, sans-serif"),
                    )
                    st.plotly_chart(fig_hist, width="stretch")

                    # ── Sobreposicao historica por SETOR ──
                    fig_hist_setor = go.Figure()
                    color_idx = 0

                    for nome_a, nome_b in pares:
                        cnpj_a = nome_cnpj_map[nome_a]
                        cnpj_b = nome_cnpj_map[nome_b]

                        df_a = df_pos[df_pos["cnpj_fundo"] == cnpj_a]
                        df_b = df_pos[df_pos["cnpj_fundo"] == cnpj_b]

                        dates_a = set(df_a["data"].unique())
                        dates_b = set(df_b["data"].unique())
                        common_dates = sorted(dates_a & dates_b)

                        if not common_dates:
                            continue

                        overlap_series = []
                        for dt in common_dates:
                            setor_a = df_a[df_a["data"] == dt].groupby("setor")["pct_pl"].sum().to_dict()
                            setor_b = df_b[df_b["data"] == dt].groupby("setor")["pct_pl"].sum().to_dict()
                            common_s = set(setor_a.keys()) & set(setor_b.keys())
                            overlap = sum(min(setor_a[s], setor_b[s]) for s in common_s)
                            overlap_series.append(overlap)

                        label_a = nome_a[:20] if len(nome_a) > 20 else nome_a
                        label_b = nome_b[:20] if len(nome_b) > 20 else nome_b
                        pair_label = f"{label_a} x {label_b}"

                        fig_hist_setor.add_trace(go.Scatter(
                            x=common_dates,
                            y=overlap_series,
                            mode="lines+markers",
                            name=pair_label,
                            line=dict(width=2, color=TAG_CHART_COLORS[color_idx % len(TAG_CHART_COLORS)]),
                            marker=dict(size=4),
                            hovertemplate=f"<b>{pair_label}</b><br>%{{x|%b/%Y}}: %{{y:.1f}}%<extra></extra>",
                        ))
                        color_idx += 1

                    fig_hist_setor.update_layout(
                        title=dict(text="Sobreposicao Historica por Setor", font=dict(size=18, color=TAG_VERMELHO)),
                        height=500, template="plotly_white",
                        yaxis=dict(title="% PL Sobreposto", ticksuffix="%"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
                        plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=40, r=20, t=60, b=40),
                        font=dict(family="Tahoma, sans-serif"),
                    )
                    st.plotly_chart(fig_hist_setor, width="stretch")

                # ─── TABELA: Top Holdings em Comum ───
                st.markdown("### Top Holdings em Comum")
                holdings_sets = {}
                for nome_fundo in fundos_sel:
                    cnpj = nome_cnpj_map[nome_fundo]
                    df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]
                    if df_f.empty:
                        continue
                    ultima = df_f["data"].max()
                    top = df_f[df_f["data"] == ultima].nlargest(15, "pct_pl")["ativo"].tolist()
                    holdings_sets[nome_fundo] = set(top)

                if len(holdings_sets) >= 2:
                    names = list(holdings_sets.keys())
                    common = holdings_sets[names[0]]
                    for nm in names[1:]:
                        common = common & holdings_sets[nm]

                    if common:
                        rows = []
                        for ativo in sorted(common):
                            row_data = {"Ativo": ativo}
                            for nome_fundo in fundos_sel:
                                cnpj = nome_cnpj_map[nome_fundo]
                                df_f = df_pos[df_pos["cnpj_fundo"] == cnpj]
                                ultima = df_f["data"].max()
                                pct = df_f[(df_f["data"] == ultima) & (df_f["ativo"] == ativo)]["pct_pl"].sum()
                                row_data[nome_fundo] = f"{pct:.1f}%"
                            rows.append(row_data)
                        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
                    else:
                        st.info("Nenhum ativo em comum entre os top-15 holdings dos fundos selecionados.")


if __name__ == "__main__":
    main()
