import sys

import requests


def get_deck_id(deck_name):
    payload = {
        'action': 'deckNamesAndIds',
        'version': 6
    }
    response = requests.post('http://localhost:8765', json=payload).json()
    return response['result'].get(deck_name)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python get-deck-id.py <deck_name>')
        sys.exit(1)

    deck_name = sys.argv[1]
    deck_id = get_deck_id(deck_name)
    print(deck_id)