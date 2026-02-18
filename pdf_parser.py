"""
Parser dos PDFs de posição do BTG Pactual.
Extrai a seção "Portfólio Investido" dos RelResumoCarteira_*.pdf
"""

import os
import re
import pandas as pd

# Caminho base dos PDFs
PDF_BASE_DIR = r"G:\Drives compartilhados\SisIntegra\AMBIENTE_PRODUCAO\Posicao_PDF\BTG_Pactual"


def _pdf_dir_exists() -> bool:
    return os.path.isdir(PDF_BASE_DIR)


def listar_datas_disponiveis() -> list[str]:
    """Retorna lista de datas (YYYYMMDD) disponíveis, ordenadas decrescente."""
    if not _pdf_dir_exists():
        return []
    datas = [
        d for d in os.listdir(PDF_BASE_DIR)
        if os.path.isdir(os.path.join(PDF_BASE_DIR, d)) and re.match(r"^\d{8}$", d)
    ]
    return sorted(datas, reverse=True)


def listar_fundos_pdf(data: str) -> list[str]:
    """Retorna lista de nomes de fundos disponíveis para uma data."""
    pasta = os.path.join(PDF_BASE_DIR, data)
    if not os.path.isdir(pasta):
        return []
    fundos = []
    for f in sorted(os.listdir(pasta)):
        if f.startswith("RelResumoCarteira_") and f.endswith(".pdf"):
            nome = f.replace("RelResumoCarteira_", "").replace(".pdf", "")
            # Converter underscores em espaços
            nome_display = nome.replace("_", " ")
            fundos.append(nome_display)
    return fundos


def _get_pdf_path(data: str, nome_fundo: str) -> str:
    """Converte nome do fundo de volta para caminho do PDF."""
    nome_arquivo = nome_fundo.replace(" ", "_")
    return os.path.join(PDF_BASE_DIR, data, f"RelResumoCarteira_{nome_arquivo}.pdf")


def _normalizar_cnpj(cnpj: str) -> str:
    """Remove pontos, traços e barras do CNPJ, mantendo apenas dígitos."""
    return re.sub(r"\D", "", cnpj)


def _parse_valor(s: str) -> float:
    """Converte string de valor monetário para float."""
    if not s:
        return 0.0
    s = s.strip().replace("$", "").replace(",", "")
    # Valores entre parênteses são negativos
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return 0.0


def extrair_portfolio_investido(data: str, nome_fundo: str) -> pd.DataFrame:
    """
    Extrai a seção 'Portfólio Investido' do PDF.
    Retorna DataFrame com: cnpj, nome_portfolio, quantidade, quota, financeiro, pct_pl, ganho_diario
    """
    try:
        import pdfplumber
    except ImportError:
        return pd.DataFrame()

    pdf_path = _get_pdf_path(data, nome_fundo)
    if not os.path.exists(pdf_path):
        return pd.DataFrame()

    registros = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # O portfólio investido geralmente está na página 2 (ou última)
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines = text.split("\n")

                in_portfolio = False
                past_header = False

                for line in lines:
                    # Detectar início da seção
                    if re.search(r"Portf.lio\s+Investido", line):
                        in_portfolio = True
                        continue

                    if not in_portfolio:
                        continue

                    # Pular linha de cabeçalho
                    if re.search(r"Cnpj\s+Portf.lio", line):
                        past_header = True
                        continue

                    if not past_header:
                        continue

                    # Linha de total (fim da seção)
                    if line.strip().startswith("$") and not re.search(r"[A-Za-z]", line.replace("$", "")):
                        in_portfolio = False
                        break

                    # Detectar seção seguinte
                    if re.search(r"^Despesas$", line.strip()):
                        in_portfolio = False
                        break

                    # Parsear linha de holding
                    registro = _parse_portfolio_line(line)
                    if registro:
                        registros.append(registro)

    except Exception:
        return pd.DataFrame()

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)
    return df


def _parse_portfolio_line(line: str) -> dict | None:
    """
    Parseia uma linha da seção Portfólio Investido.
    Formato com CNPJ: '40011451000149 FIP SPX RE CLA MULT 3,612,254.388762 1.334022 $4,818,826.46 6.84 -179.89'
    Formato sem CNPJ: 'VOLPE SP I LP 145,265.000000 5.206000 $756,249.59 1.07 3,210.36'
    """
    line = line.strip()
    if not line:
        return None

    cnpj = ""

    # Verificar se começa com CNPJ (14 dígitos)
    m_cnpj = re.match(r"^(\d{14})\s+", line)
    if m_cnpj:
        cnpj = m_cnpj.group(1)
        line = line[m_cnpj.end():]

    # Agora line = "NOME DO FUNDO quantidade quota $financeiro %pl ganho"
    # Precisamos separar o nome (texto) dos números
    # Estratégia: encontrar o primeiro número grande (quantidade) da direita pra esquerda

    # Regex para capturar os campos numéricos no final da linha
    # Formato: NOME   QUANTIDADE   QUOTA   $FINANCEIRO   %PL   GANHO
    pattern = re.compile(
        r"^(.+?)\s+"                              # nome (non-greedy)
        r"([\d,]+\.\d{2,})\s+"                    # quantidade (tem muitas decimais)
        r"([\d,]+\.\d+)\s+"                       # quota
        r"\$([\d,]+\.\d{2})\s+"                   # financeiro (com $)
        r"([\d.]+)\s+"                             # %PL
        r"(-?[\d,]+\.\d{2})$"                     # ganho diário
    )

    m = pattern.match(line)
    if not m:
        return None

    nome = m.group(1).strip()
    quantidade = _parse_valor(m.group(2))
    quota = _parse_valor(m.group(3))
    financeiro = _parse_valor(m.group(4))
    pct_pl = _parse_valor(m.group(5))
    ganho = _parse_valor(m.group(6))

    return {
        "cnpj": cnpj,
        "nome_portfolio": nome,
        "quantidade": quantidade,
        "quota": quota,
        "financeiro": financeiro,
        "pct_pl": pct_pl,
        "ganho_diario": ganho,
    }


def extrair_resumo(data: str, nome_fundo: str) -> dict:
    """
    Extrai metadados do resumo da carteira (página 1).
    Retorna dict com: nome_fundo, data_posicao, patrimonio, portfolio_investido_pct
    """
    try:
        import pdfplumber
    except ImportError:
        return {}

    pdf_path = _get_pdf_path(data, nome_fundo)
    if not os.path.exists(pdf_path):
        return {}

    resultado = {
        "nome_fundo": nome_fundo,
        "data_posicao": data,
        "patrimonio": 0.0,
        "portfolio_investido_pct": 0.0,
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page1 = pdf.pages[0]
            text = page1.extract_text() or ""

            for line in text.split("\n"):
                line_clean = line.strip()

                # Patrimônio
                m = re.match(r"PATRIM.NIO\s+([\d,]+\.\d+)", line_clean)
                if m:
                    resultado["patrimonio"] = _parse_valor(m.group(1))

                # Portfolio Investido %PL
                m = re.match(r"PORTFOLIO INVESTIDO\s+[\d,]+\.\d+\s+[\d,().+-]+\s+([\d.]+)", line_clean)
                if m:
                    resultado["portfolio_investido_pct"] = _parse_valor(m.group(1))

                # Data posição
                m = re.search(r"Posi..o[:\s]*(\d{2}/\d{2}/\d{4})", line_clean)
                if m:
                    resultado["data_posicao"] = m.group(1)

    except Exception:
        pass

    return resultado


# ── Teste rápido ──
if __name__ == "__main__":
    datas = listar_datas_disponiveis()
    print(f"Datas disponíveis: {len(datas)} (mais recente: {datas[0] if datas else 'N/A'})")

    if datas:
        data = datas[0]
        fundos = listar_fundos_pdf(data)
        print(f"\nFundos em {data}: {len(fundos)}")
        for f in fundos[:10]:
            print(f"  - {f}")

        # Testar com TAG NOVOS G FIC FIM
        nome_teste = "TAG NOVOS G FIC FIM"
        if nome_teste in fundos:
            print(f"\n=== Resumo: {nome_teste} ===")
            resumo = extrair_resumo(data, nome_teste)
            for k, v in resumo.items():
                print(f"  {k}: {v}")

            print(f"\n=== Portfólio Investido ===")
            df = extrair_portfolio_investido(data, nome_teste)
            print(df.to_string())
