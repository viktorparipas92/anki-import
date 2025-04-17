import sys

from anki_requests import make_anki_request


def get_deck_id(deck_name):
    response = make_anki_request('deckNamesAndIds')
    return response['result'].get(deck_name)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python get_deck_id.py <deck_name>')
        sys.exit(1)

    deck_name = sys.argv[1]
    deck_id = get_deck_id(deck_name)
    print(deck_id)