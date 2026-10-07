"""Configuração central do pipeline: caminhos, CIDs, espécies e tabelas de apoio."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
RAW = DATA / "raw"
CLEAN = DATA / "clean"
SAIDA = RAIZ / "site" / "public" / "data"

# --- Fontes -----------------------------------------------------------------
# Portal CKAN do INSS. O pacote de "benefícios concedidos" tem um arquivo por mês.
INSS_CKAN = "https://dadosabertos.inss.gov.br/api/3/action/package_show"
INSS_PACOTE = "beneficios-concedidos-plano-de-dados-abertos-jun-2023-a-jun-2025"

# FTP do PDET (MTE). Novo CAGED: um .7z por mês; RAIS: um .7z por UF/região por ano.
PDET_FTP = "ftp://ftp.mtps.gov.br/pdet/microdados"
CAGED_URL = PDET_FTP + "/NOVO%20CAGED/{ano}/{ano}{mes:02d}/CAGEDMOV{ano}{mes:02d}.7z"
RAIS_DIR = PDET_FTP + "/RAIS/{ano}/"

# --- Espécies de benefício do INSS ------------------------------------------
ESPECIES = {
    31: "Auxílio por incapacidade temporária (comum)",
    91: "Auxílio por incapacidade temporária (acidentário)",
    32: "Aposentadoria por incapacidade permanente (comum)",
    92: "Aposentadoria por incapacidade permanente (acidentária)",
    87: "BPC – pessoa com deficiência",
}
AFASTAMENTO = (31, 91)   # o que o site chama de "afastamento"
PERMANENTE = (32, 92)
BPC_PCD = (87,)

# --- Grupos de CID-10 ---------------------------------------------------------
# Ordem importa: o primeiro prefixo que casar define o grupo.
GRUPOS_CID = [
    ("depressao", "Depressão", ("F32", "F33")),
    ("ansiedade", "Ansiedade", ("F41",)),
    ("estresse_burnout", "Estresse e burnout", ("F43", "Z73")),
    ("autismo", "Autismo (TEA)", ("F84",)),
    ("outros_mentais", "Outros transtornos mentais", ("F",)),
]

# --- Novo CAGED: códigos de "tipomovimentação" ------------------------------
# Conferir no dicionário do layout do Novo CAGED (PDET) a cada atualização.
CAGED_SEM_JUSTA_CAUSA = (31,)
CAGED_A_PEDIDO = (40,)

UFS = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA",
    31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF",
}
UF_NOMES = {
    "RONDONIA": "RO", "ACRE": "AC", "AMAZONAS": "AM", "RORAIMA": "RR", "PARA": "PA",
    "AMAPA": "AP", "TOCANTINS": "TO", "MARANHAO": "MA", "PIAUI": "PI", "CEARA": "CE",
    "RIO GRANDE DO NORTE": "RN", "PARAIBA": "PB", "PERNAMBUCO": "PE", "ALAGOAS": "AL",
    "SERGIPE": "SE", "BAHIA": "BA", "MINAS GERAIS": "MG", "ESPIRITO SANTO": "ES",
    "RIO DE JANEIRO": "RJ", "SAO PAULO": "SP", "PARANA": "PR", "SANTA CATARINA": "SC",
    "RIO GRANDE DO SUL": "RS", "MATO GROSSO DO SUL": "MS", "MATO GROSSO": "MT",
    "GOIAS": "GO", "DISTRITO FEDERAL": "DF",
}

# Divisão CNAE 2.0 (2 dígitos) -> seção (letra)
def secao_cnae(divisao: int) -> str:
    faixas = [
        (1, 3, "A"), (5, 9, "B"), (10, 33, "C"), (35, 35, "D"), (36, 39, "E"),
        (41, 43, "F"), (45, 47, "G"), (49, 53, "H"), (55, 56, "I"), (58, 63, "J"),
        (64, 66, "K"), (68, 68, "L"), (69, 75, "M"), (77, 82, "N"), (84, 84, "O"),
        (85, 85, "P"), (86, 88, "Q"), (90, 93, "R"), (94, 96, "S"), (97, 97, "T"),
        (99, 99, "U"),
    ]
    for ini, fim, s in faixas:
        if ini <= divisao <= fim:
            return s
    return "Z"

# O INSS informa "ramo de atividade", não CNAE. Correspondência aproximada
# entre seções CNAE e ramos, usada só na página de setores (marcada como aproximada).
SETORES = {
    "agro": ("Agropecuária", ("A",), ("RURAL",)),
    "industria": ("Indústria e construção", ("B", "C", "D", "E", "F"), ("INDUSTRI",)),
    "comercio": ("Comércio", ("G",), ("COMERCI",)),
    "transporte": ("Transportes", ("H",), ("TRANSPORT", "FERROVI", "PORTUARI", "MARITIM", "AERONAUT")),
    "financeiro": ("Serviços financeiros", ("K",), ("BANCARI", "ECONOMIARI")),
}
