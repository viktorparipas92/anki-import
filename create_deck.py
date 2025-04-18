from anki_requests import make_anki_request


def create_deck(deck_data):
    response = make_anki_request('createDeck', params={'deck': deck_data})
    return response['result']