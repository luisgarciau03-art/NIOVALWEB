import gspread
from google.oauth2.service_account import Credentials

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDS_JSON = r'C:\Users\PC 1\niovalclientes-a38cae49d183.json'
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1Nb5pHtZlDth1w-5Zytjp368qd8j8-3oXacIGYdujd2E/edit#gid=1412889813'
SHEET_NAME = 'CONTACTOS UNIFICADOS'

creds = Credentials.from_service_account_file(CREDS_JSON, scopes=SCOPES)
gc = gspread.authorize(creds)
sh = gc.open_by_url(SHEET_URL)
ws = sh.worksheet(SHEET_NAME)
print(ws.row_values(1))  # Cabecera
print(ws.col_values(2)[1:5])  # Primeros 4 URLs de columna B