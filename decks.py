from get_deck_id import get_deck_id
from get_model_id import get_model_id

DECKS = {
    'Words learned - GER.csv': {
        'field_names': ['Origin', 'Article', 'Usage', 'English'],
        'unique_field': 'Origin',
        'model_name': 'German',
    },
    'Words learned - ITA.csv': {
        'field_names': ['Origin', 'Gender', 'English', 'Usage'],
        'unique_field': 'Origin',
        'model_name': 'Italian',
    },
}

for deck_filename, deck_data in DECKS.items():
    # The deck name is the same as the filename without the extension.
    deck_name = deck_filename.split('.')[0]
    deck_data.update({
        'deck_name': deck_name,
        'deck_id': get_deck_id(deck_name),
        'model_id': get_model_id(deck_data['model_name']),
    })