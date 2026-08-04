"""Throttled, cached HTTP helpers shared by the dictionary clients."""
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import settings

MAX_ATTEMPTS = 4
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

use_cache = True

_last_request_at: dict[str, float] = {}


def read_cache(namespace: str, key: str):
    """Return the cached value for `key`, or None when it is not cached."""
    if not use_cache:
        return None

    path = _build_cache_path(namespace, key)
    if not os.path.exists(path):
        return None

    with open(path, encoding='utf-8') as cache_file:
        return json.load(cache_file)['value']


def write_cache(namespace: str, key: str, value):
    """Store `value` under `key` so later runs do not repeat the request."""
    path = _build_cache_path(namespace, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode='w', encoding='utf-8') as cache_file:
        json.dump({'key': key, 'value': value}, cache_file, ensure_ascii=False)


def get_json(url: str, params: dict[str, str] | None = None) -> dict | None:
    """Fetch a JSON document, returning None if it is missing or keeps failing."""
    if params:
        url = f'{url}?{urllib.parse.urlencode(params)}'

    request = urllib.request.Request(url, headers={'User-Agent': settings.USER_AGENT})
    host = urllib.parse.urlsplit(url).netloc
    for attempt in range(1, MAX_ATTEMPTS + 1):
        _throttle(host)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if error.code not in RETRY_STATUS_CODES or attempt == MAX_ATTEMPTS:
                print(f'  ! {url} failed: HTTP {error.code}')
                return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            if attempt == MAX_ATTEMPTS:
                print(f'  ! {url} failed: {error}')
                return None

        time.sleep(2 ** attempt)

    return None


def _throttle(host: str):
    previous = _last_request_at.get(host)
    if previous is not None:
        wait = settings.DICTIONARY_REQUEST_INTERVAL - (time.monotonic() - previous)
        if wait > 0:
            time.sleep(wait)

    _last_request_at[host] = time.monotonic()


def _build_cache_path(namespace: str, key: str) -> str:
    digest = hashlib.sha1(key.encode('utf-8')).hexdigest()
    return os.path.join(settings.DICTIONARY_CACHE_DIR, namespace, f'{digest}.json')
