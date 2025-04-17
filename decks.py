from get_deck_id import get_deck_id
from get_model_id import get_model_id

GERMAN_FIELDS = ['Origin', 'Article', 'Usage', 'English']
SWEDISH_FIELDS = FRENCH_FIELDS = GERMAN_FIELDS
ITALIAN_FIELDS = ['Origin', 'Gender', 'English', 'Usage']

FRENCH_VOCAB_FIELDS = [
    'French',
    'Preposition',
    'Word type',
    'Familiarity',
    'Word subtype',
    'English',
    'Pronunciation',
]

DECKS = {
    'Words learned - GER.csv': {
        'field_names': GERMAN_FIELDS,
        'unique_field': 'Origin',
        'model_name': 'German',
    },
    'Words learned - ITA.csv': {
        'field_names': ITALIAN_FIELDS,
        'unique_field': 'Origin',
        'model_name': 'Italian',
    },
    'Words learned - SWE.csv': {
        'field_names': SWEDISH_FIELDS,
        'unique_field': 'Origin',
        'model_name': 'Swedish',
    },
    'Words learned - FRA.csv': {
        'field_names': FRENCH_FIELDS,
        'unique_field': 'Origin',
        'model_name': 'French',
    },
    'French vocabulary - Export.csv': {
        'field_names': FRENCH_VOCAB_FIELDS,
        'unique_field': 'French',
        'model_name': 'French vocab',
    },
    'Spanish grammar & vocab': {
        'Nouns - Translation.csv': {
            'field_names': ['Source', 'Article', 'English'],
            'unique_field': 'Source',
            'model_name': 'Noun - Translation with gender',
        }
    }
}

for deck_filename, deck_data in list(DECKS.items()):
    # The deck name is the same as the filename without the extension.
    deck_name = deck_filename.split('.')[0]
    if deck_name.endswith('Export'):
        # Remove the ' - Export' suffix
        deck_name = deck_name[:-9]

    if 'model_name' not in deck_data:
        for sheet_name, inner_deck_data in list(deck_data.items()):
            inner_deck_name = sheet_name.split('.')[0]
            inner_deck_data.update({
                'deck_name': f'{deck_name}::{inner_deck_name}',
                'deck_id': get_deck_id(deck_name),
                'model_id': get_model_id(inner_deck_data['model_name']),
            })
            DECKS[f'{deck_name} - {sheet_name}'] = inner_deck_data
    else:
        deck_data.update({
            'deck_name': deck_name,
            'deck_id': get_deck_id(deck_name),
            'model_id': get_model_id(deck_data['model_name']),
        })
        DECKS[deck_filename] = deck_data