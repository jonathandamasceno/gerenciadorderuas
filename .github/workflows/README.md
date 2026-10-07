# Workflow SPX — Staging Areas

## O que faz
Executa `main.py` e `inbound.py` diariamente às 09:00 no horário de Brasília (12:00 UTC), e também pode ser iniciado manualmente pela aba **Actions** do GitHub.

## Configurar no GitHub

No repositório, abra **Settings → Secrets and variables → Actions**.

### Repository secrets
Crie estes secrets (os valores não devem ser colocados no código):

- `SPX_UID`
- `SPX_UK`
- `SPX_CSRFTOKEN`
- `SPX_CID` (por exemplo, `BR`, se aplicável à sua conta)
- `SPX_ST` (por exemplo, `1`, se aplicável à sua conta)
- `SPX_SP_ST` (por exemplo, `1`, se aplicável à sua conta)
- `GOOGLE_CREDENTIALS_JSON`: cole o conteúdo completo do JSON da conta de serviço Google, incluindo `{` e `}`.

### Repository variables
Em **Variables**, configure:
- `SPREADSHEET_ID`: ID da planilha de destino.
- `SHEET_NAME`: nome da aba, por exemplo `Sheet1`.
- `SHEET_NAME2`: nome da aba secundária, por exemplo `Sheet1`.

Se não definir as duas variables da planilha, o script usa os valores padrão que estão em `main.py` e em `inbound.py`.

## Permissões do Google Sheets
Compartilhe a planilha com o e-mail `client_email` presente no JSON da conta de serviço e conceda permissão de edição. Ative a Google Sheets API no projeto Google Cloud dessa conta.

## Segurança importante
- O arquivo JSON da conta de serviço não precisa estar no repositório. O workflow o lê diretamente do secret em memória.
- Não faça `echo` dos secrets nem os imprima nos logs.
- Os cookies SPX incluídos anteriormente no código foram expostos no arquivo enviado. Revogue/renove `SPX_UK` e `SPX_CSRFTOKEN` (e qualquer outro valor que funcione como sessão) antes de usar estes secrets novos.
- Se `SPX_UK`/`SPX_CSRFTOKEN` expirarem, o workflow pode falhar até os valores serem atualizados.
- O cron do GitHub Actions usa UTC e pode começar alguns minutos depois do horário programado.
