import os

ANKI_CONNECT_URL = os.environ.get('ANKI_CONNECT_URL', 'http://localhost:8765')
ANKI_CONNECT_TIMEOUT = int(os.environ.get('ANKI_CONNECT_TIMEOUT', '30'))
LATEST_FRENCH_DECK = os.environ.get('LATEST_FRENCH_DECK', '')
SERVICE_ACCOUNT_FILE = os.environ.get(
    'SERVICE_ACCOUNT_FILE', 'secrets/quickstart-304216-ac21bea24af6.json'
)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
WRITE_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1t-rfHgosuCshh-ifwU5T5b-mSdLPc5auH36iN5pV39M'

SPREADSHEETS = {
    'Mixed': '1t-rfHgosuCshh-ifwU5T5b-mSdLPc5auH36iN5pV39M',
    'FRA': '198AhauZNmATOQCXsXHsBxu7KEcTp7NjEEeSMOuphX-k',
    'ESP': '1wzzppztmZjP9rtsLIE-0OTVOB4ojdxaUM05-UiayA9k',
    'ITA': '1GiQAQM6SP-yD1Yf1qBUWQiopa9O5xEcqkARiUnmkJvk',
    'SWE': '1ZMt_-XL3wQn52VyOavFGkjWkaqKBiHA-vAxWN4qv5fE',
}

USER_AGENT = 'anki-import/1.0 (personal Anki deck builder)'
SVENSK_ORDBOK_API_URL = 'https://svenska.se/api'
WIKTIONARY_API_URL = 'https://en.wiktionary.org/w/api.php'
DICTIONARY_CACHE_DIR = '.cache'
DICTIONARY_REQUEST_INTERVAL = 0.5