from anki_requests import make_anki_request


def create_deck(deck_name):
    response = make_anki_request('createDeck', params={'deck': deck_name})
    return response['result']


if __name__ == '__main__':
    deck_name = 'My New Deck'
    result = create_deck(deck_name)
    print(result)