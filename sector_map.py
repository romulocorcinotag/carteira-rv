"""Mapeamento de tickers B3 para setores."""

SETOR_MAP = {
    # Financeiro
    'ITUB4': 'Financeiro', 'ITUB3': 'Financeiro', 'BBDC4': 'Financeiro', 'BBDC3': 'Financeiro',
    'BBAS3': 'Financeiro', 'SANB11': 'Financeiro', 'B3SA3': 'Financeiro', 'BPAC11': 'Financeiro',
    'CIEL3': 'Financeiro', 'PSSA3': 'Financeiro', 'BBSE3': 'Financeiro', 'IRBR3': 'Financeiro',
    'SULA11': 'Financeiro', 'BRSR6': 'Financeiro', 'FIQE3': 'Financeiro', 'INBR32': 'Financeiro',
    'CXSE3': 'Financeiro', 'BMGB4': 'Financeiro', 'ABCB4': 'Financeiro', 'BPAN4': 'Financeiro',
    'MODL11': 'Financeiro', 'CRIV3': 'Financeiro', 'CRIV4': 'Financeiro',
    # Petróleo e Gás
    'PETR4': 'Petróleo e Gás', 'PETR3': 'Petróleo e Gás', 'PRIO3': 'Petróleo e Gás',
    'RECV3': 'Petróleo e Gás', 'RRRP3': 'Petróleo e Gás', 'UGPA3': 'Petróleo e Gás',
    'CSAN3': 'Petróleo e Gás', 'VBBR3': 'Petróleo e Gás', 'ENAT3': 'Petróleo e Gás',
    # Mineração e Siderurgia
    'VALE3': 'Mineração e Siderurgia', 'CSNA3': 'Mineração e Siderurgia',
    'GGBR4': 'Mineração e Siderurgia', 'USIM5': 'Mineração e Siderurgia',
    'GOAU4': 'Mineração e Siderurgia', 'CMIN3': 'Mineração e Siderurgia',
    'GGBR3': 'Mineração e Siderurgia', 'USIM3': 'Mineração e Siderurgia',
    'FESA4': 'Mineração e Siderurgia', 'CBAV3': 'Mineração e Siderurgia',
    # Energia Elétrica
    'ELET3': 'Energia Elétrica', 'ELET6': 'Energia Elétrica', 'EGIE3': 'Energia Elétrica',
    'EQTL3': 'Energia Elétrica', 'CMIG4': 'Energia Elétrica', 'CPFE3': 'Energia Elétrica',
    'TAEE11': 'Energia Elétrica', 'ENGI11': 'Energia Elétrica', 'AURE3': 'Energia Elétrica',
    'NEOE3': 'Energia Elétrica', 'CPLE6': 'Energia Elétrica', 'ENEV3': 'Energia Elétrica',
    'CMIG3': 'Energia Elétrica', 'CPLE3': 'Energia Elétrica', 'AESB3': 'Energia Elétrica',
    'TRPL4': 'Energia Elétrica', 'TAEE3': 'Energia Elétrica', 'TAEE4': 'Energia Elétrica',
    'MEGA3': 'Energia Elétrica', 'CLSC4': 'Energia Elétrica',
    # Saneamento
    'SBSP3': 'Saneamento', 'SAPR11': 'Saneamento', 'CSMG3': 'Saneamento',
    'SAPR3': 'Saneamento', 'SAPR4': 'Saneamento',
    # Saúde
    'HAPV3': 'Saúde', 'RDOR3': 'Saúde', 'RADL3': 'Saúde', 'FLRY3': 'Saúde',
    'HYPE3': 'Saúde', 'ONCO3': 'Saúde', 'QUAL3': 'Saúde', 'DASA3': 'Saúde',
    'ELMD3': 'Saúde', 'MATD3': 'Saúde', 'PNVL3': 'Saúde', 'ODPV3': 'Saúde',
    # Varejo e Consumo
    'MGLU3': 'Varejo e Consumo', 'VIVA3': 'Varejo e Consumo', 'ARZZ3': 'Varejo e Consumo',
    'LREN3': 'Varejo e Consumo', 'PETZ3': 'Varejo e Consumo', 'SOMA3': 'Varejo e Consumo',
    'GMAT3': 'Varejo e Consumo', 'CEAB3': 'Varejo e Consumo', 'GRND3': 'Varejo e Consumo',
    'TFCO4': 'Varejo e Consumo', 'VULC3': 'Varejo e Consumo', 'SBFG3': 'Varejo e Consumo',
    'ALPA4': 'Varejo e Consumo', 'POMO4': 'Varejo e Consumo', 'MILS3': 'Varejo e Consumo',
    'GMAT1': 'Varejo e Consumo', 'AZZA3': 'Varejo e Consumo', 'NTCO3': 'Varejo e Consumo',
    'BHIA3': 'Varejo e Consumo', 'AMAR3': 'Varejo e Consumo', 'LJQQ3': 'Varejo e Consumo',
    'PCAR3': 'Varejo e Consumo', 'ASAI3': 'Varejo e Consumo', 'CRFB3': 'Varejo e Consumo',
    'VIIA3': 'Varejo e Consumo', 'MLAS3': 'Varejo e Consumo',
    # Tecnologia
    'TOTS3': 'Tecnologia', 'LWSA3': 'Tecnologia', 'SMFT3': 'Tecnologia', 'SMFT9': 'Tecnologia',
    'CASH3': 'Tecnologia', 'INTB3': 'Tecnologia', 'PAGS3': 'Tecnologia', 'SMFT1': 'Tecnologia',
    'LINX3': 'Tecnologia', 'MOSI3': 'Tecnologia', 'SQIA3': 'Tecnologia',
    # Alimentos e Bebidas
    'ABEV3': 'Alimentos e Bebidas', 'JBSS3': 'Alimentos e Bebidas',
    'MRFG3': 'Alimentos e Bebidas', 'BEEF3': 'Alimentos e Bebidas',
    'BRFS3': 'Alimentos e Bebidas', 'MDIA3': 'Alimentos e Bebidas',
    'SMTO3': 'Alimentos e Bebidas', 'CAML3': 'Alimentos e Bebidas',
    'HBSA3': 'Alimentos e Bebidas', 'SLCE3': 'Alimentos e Bebidas',
    'AGRO3': 'Alimentos e Bebidas', 'MNPR3': 'Alimentos e Bebidas',
    'BAUH3': 'Alimentos e Bebidas', 'BAUH4': 'Alimentos e Bebidas',
    # Construção e Imobiliário
    'CYRE3': 'Construção e Imob.', 'EZTC3': 'Construção e Imob.',
    'MRVE3': 'Construção e Imob.', 'EVEN3': 'Construção e Imob.',
    'DIRR3': 'Construção e Imob.', 'TEND3': 'Construção e Imob.',
    'LAVV3': 'Construção e Imob.', 'PLPL3': 'Construção e Imob.',
    'CURY3': 'Construção e Imob.', 'MDNE3': 'Construção e Imob.',
    'TRIS3': 'Construção e Imob.', 'JHSF3': 'Construção e Imob.',
    # Transporte e Logística
    'RENT3': 'Transporte e Logística', 'RENT4': 'Transporte e Logística',
    'ECOR3': 'Transporte e Logística', 'CCRO3': 'Transporte e Logística',
    'AZUL4': 'Transporte e Logística', 'GOLL4': 'Transporte e Logística',
    'RAIL3': 'Transporte e Logística', 'STBP3': 'Transporte e Logística',
    'MOVI3': 'Transporte e Logística', 'VAMO3': 'Transporte e Logística',
    'RENT9': 'Transporte e Logística', 'RENT1': 'Transporte e Logística',
    'VVEO3': 'Transporte e Logística', 'LOGN3': 'Transporte e Logística',
    # Concessões e Infraestrutura
    'GGPS3': 'Concessões e Infra.', 'SIMH3': 'Concessões e Infra.',
    # Telecomunicações
    'VIVT3': 'Telecomunicações', 'TIMS3': 'Telecomunicações',
    # Industrial
    'WEGE3': 'Industrial', 'EMBR3': 'Industrial', 'TUPY3': 'Industrial',
    'RAIZ4': 'Industrial', 'FRAS3': 'Industrial', 'KEPL3': 'Industrial',
    'RAPT4': 'Industrial', 'RANI3': 'Industrial', 'LEVE3': 'Industrial',
    'PTBL3': 'Industrial', 'TASA4': 'Industrial',
    # Papel e Celulose
    'SUZB3': 'Papel e Celulose', 'KLBN11': 'Papel e Celulose',
    'KLBN4': 'Papel e Celulose', 'KLBN3': 'Papel e Celulose',
    # Holdings
    'AXIA3': 'Holdings', 'AXIA7': 'Holdings',
    # Educação
    'YDUQ3': 'Educação', 'COGN3': 'Educação', 'SEER3': 'Educação',
    # Shoppings
    'MULT3': 'Shoppings', 'IGTI11': 'Shoppings', 'ALSO3': 'Shoppings',
    'ALOS3': 'Shoppings', 'SCAR3': 'Shoppings',
    # Serviços Ambientais
    'AMOB3': 'Serviços Ambientais',
    # Consumo e Varejo (pet)
    'AUAU3': 'Consumo e Varejo',
}


def classificar_setor(ticker: str) -> str:
    """Retorna o setor de um ticker. Fallback: 'Outros'."""
    t = ticker.strip().upper()
    if t in SETOR_MAP:
        return SETOR_MAP[t]
    if t.startswith("FUNDO "):
        return "Cotas de Fundos"
    if t.startswith("TITPUB "):
        return "Renda Fixa"
    if t.startswith("DEP ") or t.startswith("DEB ") or t.startswith("RF "):
        return "Renda Fixa"
    if t.startswith("DERIV "):
        return "Derivativos"
    if t.startswith("[SEM DADOS]"):
        return "Sem Dados CVM"
    if t == "CAIXA" or t == "OUTROS RF/CAIXA":
        return "Caixa"
    return "Outros"
