import subprocess
import sys
import time
from urllib.parse import urlparse

import requests

import settings

LOCAL_HOSTNAMES = frozenset({'localhost', '127.0.0.1', '::1'})


def make_anki_request(action: str, *, params: dict | None = None) -> dict:
    """Send a request to AnkiConnect."""
    payload = {
        'action': action,
        'version': 6,
        'params': params or {}
    }
    response = requests.post(settings.ANKI_CONNECT_URL, json=payload)
    json_response = response.json()
    if error := json_response.get('error'):
        raise Exception(f'AnkiConnect Error: {error} - {payload}')

    return json_response


def wait_for_ankiconnect(timeout: int | None = None, delay: float = 1) -> bool:
    """Wait until AnkiConnect responds, opening Anki first if it runs locally."""
    timeout = settings.ANKI_CONNECT_TIMEOUT if timeout is None else timeout
    start_time = time.time()
    anki_started = False
    while True:
        try:
            version_data = make_anki_request('version')
            print(f'Anki connect is ready. Version: {version_data["result"]}.')
            return True
        except Exception:
            print('AnkiConnect is not running yet.')
            if not anki_started and _can_open_anki():
                _open_anki()
                anki_started = True

            if time.time() - start_time > timeout:
                return False

            time.sleep(delay)


def _can_open_anki() -> bool:
    hostname = urlparse(settings.ANKI_CONNECT_URL).hostname
    return sys.platform == 'darwin' and hostname in LOCAL_HOSTNAMES


def _open_anki():
    print('Opening Anki...')
    try:
        subprocess.Popen(['open', '-a', 'Anki'])
    except OSError as error:
        print(f'Could not open Anki: {error}')
