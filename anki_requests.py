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
    error = json_response.get('error')
    if (
        error is not None
        and action == 'addNotes'
        and 'cannot create note because it is a duplicate' in error
    ):
        print('Could not create notes because of duplicates, trying one by one...')

        payload['action'] = 'addNote'
        errors = []
        for note in params['notes']:
            payload['params'] = {'note': note}
            response = requests.post(ANKI_CONNECT_URL, json=payload)
            json_response = response.json()
            if error := json_response.get('error'):
                new_error = f'{error} - {note['fields']}'
                errors.append(new_error)

        if errors:
            raise Exception(f'AnkiConnect Error: {errors}')
    elif error:
        raise Exception(f'AnkiConnect Error: {error} - {payload}')

    return json_response
