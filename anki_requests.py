import requests
from requests import Response

from settings import ANKI_CONNECT_URL


def make_anki_request(action: str, *, params: dict | None = None) -> Response:
    """Send a request to AnkiConnect."""
    payload = {
        'action': action,
        'version': 6,
        'params': params or {}
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload)
    json_response = response.json()
    if error := json_response.get('error'):
        raise Exception(f'AnkiConnect Error: {error}')

    return json_response