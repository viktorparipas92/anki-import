import sys

import requests


def get_model_id(model_name):
    payload = {
        'action': 'modelNamesAndIds',
        'version': 6
    }
    response = requests.post('http://localhost:8765', json=payload).json()
    return response['result'].get(model_name)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python get-model-id.py <model_name>')
        sys.exit(1)

    model_name = sys.argv[1]
    deck_id = get_model_id(model_name)
    print(deck_id)
