import requests
import json
import csv
import sys
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


# ============================================================
# CONFIGURAÇÕES SPX
# ============================================================

SPX_UID = os.getenv("SPX_UID", "")
SPX_UK = os.getenv("SPX_UK", "")
SPX_CSRFTOKEN = os.getenv("SPX_CSRFTOKEN", "")
SPX_CID = os.getenv("SPX_CID", "BR")
SPX_ST = os.getenv("SPX_ST", "1")
SPX_SP_ST = os.getenv("SPX_SP_ST", "1")

# Falha cedo se os cookies essenciais não estiverem configurados no GitHub.
for nome, valor in {
    "SPX_UID": SPX_UID,
    "SPX_UK": SPX_UK,
    "SPX_CSRFTOKEN": SPX_CSRFTOKEN,
}.items():
    if not valor:
        raise RuntimeError(f"Secret obrigatório não configurado: {nome}")


# ============================================================
# CONFIGURAÇÕES GOOGLE SHEETS
# ============================================================

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1ZZroqMh9XgVv0yrDu1ZzFurREn4zUvCq_0QvHM8h1Io")
SHEET_NAME = os.getenv("SHEET_NAME", "inbound")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")


# ============================================================
# CONFIGURAÇÕES DA API SPX
# ============================================================

API_URL = (
    "https://spx.shopee.com.br/"
    "api/in-station/"
    "inbound_staging_area/list"
)

PAGE_SIZE = 100

# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),

    "Accept": "application/json, text/plain, */*",

    "Content-Type": "application/json",

    "Origin": "https://spx.shopee.com.br",

    "Referer": (
        "https://spx.shopee.com.br/api/in-station/inbound_staging_area/list"
    ),

    "x-csrftoken": SPX_CSRFTOKEN,
}


# ============================================================
# CRIA SESSION
# ============================================================

session = requests.Session()

session.headers.update(HEADERS)


# ============================================================
# ADICIONAR COOKIES
# ============================================================

def adicionar_cookie(nome, valor):

    if not valor:
        return

    session.cookies.set(
        nome,
        valor,
        domain="spx.shopee.com.br",
        path="/"
    )

    session.cookies.set(
        nome,
        valor,
        domain=".spx.shopee.com.br",
        path="/"
    )


adicionar_cookie(
    "spx_uid",
    SPX_UID
)

adicionar_cookie(
    "spx_uk",
    SPX_UK
)

adicionar_cookie(
    "spx_cid",
    SPX_CID
)

adicionar_cookie(
    "csrftoken",
    SPX_CSRFTOKEN
)

adicionar_cookie(
    "spx_st",
    SPX_ST
)

adicionar_cookie(
    "spx_sp_st",
    SPX_SP_ST
)


# ============================================================
# CAMPOS QUE SERÃO ENVIADOS PARA A SHEETS
# ============================================================


CAMPOS = {
    "Staging Area Name": "area_name",
    "Priority": "priority",
    "TO Destination": "to_destination",
    "Sorting Plan Group": "staging_group_name",
    "Capacity": "capacity",
    "No. of Cages": "cage_quantity",
    "No. of TOs": "to_quantity",
    "No. of Loose Orders": "loose_order_quantity",
    "Total Orders": "total_order_quantity",
    "Occupancy Percentage": "occupy_percentage",
    "Staged Duration": "staging_duration_time",
    "Link Camera": "linked_camera",
    "Status": "status",
    "Editor": "operator",
    "Update Time": "update_time",
}


# ============================================================
# CONVERTER VALORES
# ============================================================

def converter_valor(valor):

    if valor is None:
        return ""

    if isinstance(valor, (list, dict)):

        return json.dumps(
            valor,
            ensure_ascii=False
        )

    return valor


# ============================================================
# CONSULTAR UMA PÁGINA DA API
# ============================================================

def consultar_pagina(pagina):

    payload = {
        "pageno": pagina,
        "count": PAGE_SIZE
    }

    print(
        f"\nConsultando página {pagina}..."
    )

    try:

        response = session.post(
            API_URL,
            json=payload,
            timeout=60
        )

    except requests.exceptions.RequestException as erro:

        print(
            "\nErro de conexão com a API:"
        )

        print(erro)

        return None


    print(
        f"HTTP: {response.status_code}"
    )


    # --------------------------------------------------------
    # VERIFICAR HTTP
    # --------------------------------------------------------

    if response.status_code != 200:

        print("\nA API retornou HTTP diferente de 200; corpo da resposta omitido por segurança.")

        return None


    # --------------------------------------------------------
    # CONVERTER PARA JSON
    # --------------------------------------------------------

    try:

        dados = response.json()

    except Exception:

        print("\nA API retornou uma resposta que não é JSON; corpo omitido por segurança.")

        return None


    # --------------------------------------------------------
    # VERIFICAR RETCODE
    # --------------------------------------------------------

    if dados.get("retcode") != 0:

        print(
            "\nAPI retornou erro:"
        )

        print(
            json.dumps(
                dados,
                ensure_ascii=False,
                indent=2
            )
        )

        return None


    return dados


# ============================================================
# BUSCAR TODAS AS PÁGINAS
# ============================================================

todos_registros = []

pagina = 1

total = None


while True:

    resposta = consultar_pagina(
        pagina
    )


    if resposta is None:

        print(
            "\nFalha na consulta."
        )

        sys.exit(1)


    data = resposta.get(
        "data",
        {}
    )


    registros = data.get(
        "list",
        []
    )


    # --------------------------------------------------------
    # PEGAR TOTAL
    # --------------------------------------------------------

    if total is None:

        total = data.get(
            "total",
            0
        )

        print(
            f"Total de registros na API: {total}"
        )


    # --------------------------------------------------------
    # SE NÃO EXISTIREM MAIS REGISTROS
    # --------------------------------------------------------

    if not registros:

        break


    # --------------------------------------------------------
    # ADICIONAR REGISTROS
    # --------------------------------------------------------

    todos_registros.extend(
        registros
    )


    print(
        f"Recebidos nesta página: {len(registros)}"
    )

    print(
        f"Total acumulado: "
        f"{len(todos_registros)} / {total}"
    )


    # --------------------------------------------------------
    # VERIFICAR SE TERMINOU
    # --------------------------------------------------------

    if len(todos_registros) >= total:

        break


    pagina += 1


# ============================================================
# FILTRAR SOMENTE OS CAMPOS NECESSÁRIOS
# ============================================================

dados_filtrados = []


for registro in todos_registros:

    linha = {}


    for header, campo_api in CAMPOS.items():

        valor = registro.get(
            campo_api,
            ""
        )


        linha[header] = converter_valor(
            valor
        )


    dados_filtrados.append(
        linha
    )




# ============================================================
# CONECTAR AO GOOGLE SHEETS
# ============================================================

print(
    "\nConectando ao Google Sheets..."
)


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]


if not GOOGLE_CREDENTIALS_JSON:
    raise RuntimeError("Secret obrigatório não configurado: GOOGLE_CREDENTIALS_JSON")

try:
    google_info = json.loads(GOOGLE_CREDENTIALS_JSON)
except json.JSONDecodeError as erro:
    raise RuntimeError("O secret GOOGLE_CREDENTIALS_JSON não contém um JSON válido.") from erro

credentials = Credentials.from_service_account_info(
    google_info,
    scopes=SCOPES
)


service = build(
    "sheets",
    "v4",
    credentials=credentials
)


print(
    "Google Sheets conectado!"
)


# ============================================================
# LIMPAR DADOS ANTIGOS
# ============================================================

print(
    "\nLimpando dados antigos da planilha..."
)


service.spreadsheets().values().clear(
    spreadsheetId=SPREADSHEET_ID,

    range=f"{SHEET_NAME}!A:O",

    body={}
).execute()


print(
    "Dados antigos removidos."
)


# ============================================================
# PREPARAR DADOS PARA A SHEETS
# ============================================================

valores_sheets = []


# ------------------------------------------------------------
# CABEÇALHOS
# ------------------------------------------------------------

valores_sheets.append(
    list(CAMPOS.keys())
)


# ------------------------------------------------------------
# DADOS
# ------------------------------------------------------------

for registro in dados_filtrados:

    linha = []

    for header in CAMPOS.keys():

        linha.append(
            registro[header]
        )

    valores_sheets.append(
        linha
    )


# ============================================================
# ENVIAR DADOS PARA A GOOGLE SHEETS
# ============================================================

print(
    "\nEnviando dados para a Google Sheets..."
)


service.spreadsheets().values().update(

    spreadsheetId=SPREADSHEET_ID,

    range=f"{SHEET_NAME}!A1",

    valueInputOption="USER_ENTERED",

    body={
        "values": valores_sheets
    }

).execute()


# ============================================================
# FINAL
# ============================================================

print(
    "\n========================================"
)

print(
    "          PROCESSO CONCLUÍDO"
)

print(
    "========================================"
)

print(
    f"Total de registros: "
    f"{len(dados_filtrados)}"
)

print(
    f"Planilha: {SPREADSHEET_ID}"
)

print(
    f"Aba: {SHEET_NAME}"
)



print(
    "========================================"
)