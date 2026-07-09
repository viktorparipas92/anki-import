import subprocess
import time

import requests

from settings import ANKI_CONNECT_URL


def make_anki_request(action: str, *, params: dict | None = None) -> dict:
    """Send a request to AnkiConnect."""
    payload = {
        'action': action,
        'version': 6,
        'params': params or {}
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload)
    json_response = response.json()
    if error := json_response.get('error'):
        raise Exception(f'AnkiConnect Error: {error} - {payload}')

    return json_response


def wait_for_ankiconnect(timeout: int = 30, delay: float = 1) -> bool:
    """Open Anki if it is not running and wait until AnkiConnect responds."""
    start_time = time.time()
    anki_started = False
    while True:
        try:
            version_data = make_anki_request('version')
            print(f'Anki connect is ready. Version: {version_data["result"]}.')
            return True
        except Exception:
            print('AnkiConnect is not running yet.')
            if not anki_started:
                print('Opening Anki...')
                subprocess.Popen(['open', '-a', 'Anki'])
                anki_started = True

            if time.time() - start_time > timeout:
                return False

            time.sleep(delay)
