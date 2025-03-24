import sys

import requests

from import_csv_to_anki import ANKI_CONNECT_URL


def get_model_id(model_name):
    payload = {
        'action': 'modelNamesAndIds',
        'version': 6
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload).json()
    return response['result'].get(model_name)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python get_model_id.py <model_name>')
        sys.exit(1)

    model_name = sys.argv[1]
    deck_id = get_model_id(model_name)
    print(deck_id)
