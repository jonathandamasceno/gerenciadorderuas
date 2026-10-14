import time
import requests
import json
import sys
import os
import logging

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

if __name__ == "__main__":
    while True:
        logging.info("\n-- Iniciando Atualização --")
        # ============================================================
        # CONFIGURAÇÕES
        # ============================================================

        SPX_UID = os.getenv("SPX_UID", "")
        SPX_UK = os.getenv("SPX_UK", "")
        SPX_CSRFTOKEN = os.getenv("SPX_CSRFTOKEN", "")
        SPX_CID = os.getenv("SPX_CID", "BR")
        SPX_ST = os.getenv("SPX_ST", "1")
        SPX_SP_ST = os.getenv("SPX_SP_ST", "1")

        for nome, valor in {
            "SPX_UID": SPX_UID,
            "SPX_UK": SPX_UK,
            "SPX_CSRFTOKEN": SPX_CSRFTOKEN,
        }.items():
            if not valor:
                raise RuntimeError(f"Secret obrigatório não configurado: {nome}")


        SPREADSHEET_ID = os.getenv(
            "SPREADSHEET_ID",
            "1ZZroqMh9XgVv0yrDu1ZzFurREn4zUvCq_0QvHM8h1Io"
        )

        GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")


        # ============================================================
        # SESSÃO SPX
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
            "x-csrftoken": SPX_CSRFTOKEN,
        }

        session = requests.Session()
        session.headers.update(HEADERS)


        def adicionar_cookie(nome, valor):
            if valor:
                session.cookies.set(nome, valor, domain="spx.shopee.com.br", path="/")
                session.cookies.set(nome, valor, domain=".spx.shopee.com.br", path="/")


        for nome, valor in [
            ("spx_uid", SPX_UID),
            ("spx_uk", SPX_UK),
            ("spx_cid", SPX_CID),
            ("csrftoken", SPX_CSRFTOKEN),
            ("spx_st", SPX_ST),
            ("spx_sp_st", SPX_SP_ST),
        ]:
            adicionar_cookie(nome, valor)


        # ============================================================
        # CONFIGURAÇÕES DAS DUAS PÁGINAS
        # ============================================================

        PAGINAS = [
            {
                "nome": "MAIN - Outbound",
                "sheet": "Sheet1",
                "url": "https://spx.shopee.com.br/api/in-station/outbound/outbound_staging_area/config/search",
                "referer": "https://spx.shopee.com.br/#/staging-area-management/list/outbound",
                "campos": {
                    "Staging Area Name": "staging_area_name",
                    "Priority": "priority",
                    "TO Destination": "to_destination",
                    "Sorting Plan Group": "sorting_plan_group_list",
                    "Capacity": "capacity",
                    "No. of Cages": "cage_quantity",
                    "No.of TOs": "transport_order_quantity",
                    "No.of Loose Orders": "loose_order_quantity",
                    "Total Orders": "total_order_quantity",
                    "Occupancy Percentage": "occupancy_percentage",
                    "Staged Duration": "staging_duration_time",
                    "Link Camera": "linked_camera",
                    "Status": "staging_area_status",
                    "Editor": "operator",
                    "Update Time": "mtime",
                },
            },
            {
                "nome": "INBOUND",
                "sheet": "inbound",
                "url": "https://spx.shopee.com.br/api/in-station/inbound_staging_area/list",
                "referer": "https://spx.shopee.com.br/api/in-station/inbound_staging_area/list",
                "campos": {
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
                },
            }
        ]


        def converter_valor(valor):
            if valor is None:
                return ""
            if isinstance(valor, (list, dict)):
                return json.dumps(valor, ensure_ascii=False)
            return valor


        def consultar_pagina(config, pagina):
            session.headers.update({"Referer": config["referer"]})

            response = session.post(
                config["url"],
                json={"pageno": pagina, "count": 100},
                timeout=60,
            )

            if response.status_code != 200:
                logging.info(f"Erro HTTP {response.status_code} em {config['nome']}")
                return None

            dados = response.json()

            if dados.get("retcode") != 0:
                logging.info(f"Erro API em {config['nome']}")
                logging.info(json.dumps(dados, indent=2, ensure_ascii=False))
                return None

            return dados


        def coletar(config):
            registros = []
            pagina = 1
            total = None

            logging.info(f"\n===== Atualizando {config['nome']} =====")

            while True:
                resposta = consultar_pagina(config, pagina)

                if resposta is None:
                    sys.exit(1)

                data = resposta.get("data", {})
                lista = data.get("list", [])

                if total is None:
                    total = data.get("total", 0)

                if not lista:
                    break

                registros.extend(lista)

                logging.info(f"{config['nome']}: {len(registros)}/{total}")

                if len(registros) >= total:
                    break

                pagina += 1

            dados = []
            for item in registros:
                linha = {}
                for titulo, campo in config["campos"].items():
                    linha[titulo] = converter_valor(item.get(campo, ""))
                dados.append(linha)

            return dados


        def enviar_sheet(nome_aba, campos, dados):
            if not GOOGLE_CREDENTIALS_JSON:
                raise RuntimeError("GOOGLE_CREDENTIALS_JSON não configurado")

            cred = Credentials.from_service_account_info(
                json.loads(GOOGLE_CREDENTIALS_JSON),
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )

            service = build("sheets", "v4", credentials=cred)

            valores = [list(campos.keys())]

            for linha in dados:
                valores.append([linha[x] for x in campos.keys()])

            service.spreadsheets().values().clear(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{nome_aba}!A:O",
                body={}
            ).execute()

            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{nome_aba}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": valores}
            ).execute()

            logging.info(f"{nome_aba} atualizado com {len(dados)} registros")


        # ============================================================
        # EXECUÇÃO
        # ORDEM: MAIN PRIMEIRO -> INBOUND DEPOIS
        # ============================================================

        for pagina in PAGINAS:
            dados = coletar(pagina)
            enviar_sheet(
                pagina["sheet"],
                pagina["campos"],
                dados
            )

        logging.info("\nPROCESSO FINALIZADO")

        logging.info("\n15min até a próxima Atualização")
        time.sleep(900)

