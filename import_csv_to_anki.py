import csv
import sys

from anki_requests import make_anki_request
from decks import DECKS


def get_deck_data(filename: str) -> tuple[str, list[str], str, str]:
    try:
        deck_name = DECKS[filename]['deck_name']
        field_names = DECKS[filename]['field_names']
        model_name = DECKS[filename]['model_name']
        unique_field = DECKS[filename]['unique_field']
        deck_id = DECKS[filename]['deck_id']
        return deck_name, field_names, model_name, unique_field, deck_id
    except KeyError:
        raise ValueError(
            f"The file '{filename}' does not have a corresponding deck "
            f"name in the DECKS dictionary. Please add it."
        )


def extract_fields(row: dict, field_names: list[str]) -> dict:
    return {name: row[name] or '' for name in field_names}


def construct_note(
    row: dict, *, field_names: list[str], deck: str, model: str
) -> dict:
    return {
        'deckName': deck,
        'modelName': model,
        'fields': extract_fields(row, field_names),
        'tags': [],
    }


def extract_notes(
    filename: str, deck: str, field_names: list[str], model_name: str
) -> list[dict]:
    with open(filename, newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        notes = [
            construct_note(row, field_names=field_names, deck=deck, model=model_name)
            for row in reader
        ]
        return notes


def check_for_duplicates(notes: list[dict], unique_field: str) -> list[dict]:
    seen = set()
    unique_notes = []
    for note in notes:
        unique_value = note['fields'][unique_field]
        if unique_value in seen:
            print(f'Removing duplicate {unique_field}: {unique_value}.')
        else:
            seen.add(unique_value)
            unique_notes.append(note)

    return unique_notes


def import_csv_to_anki(filename: str, deck_name: str | None = None):
    """
    Perform a bulk import of notes into Anki, updating existing notes or adding new ones.
    """
    deck_name_from_data, field_names, model_name, unique_field, deck_id = get_deck_data(filename)
    if deck_id is None:
        raise Exception(
            f'Deck with name {deck_name_from_data} not found in Anki.'
        )

    deck_name = (
        f'{deck_name_from_data}::{deck_name}' if deck_name else deck_name_from_data
    )
    notes_to_import = extract_notes(filename, deck_name, field_names, model_name)
    notes_to_import = check_for_duplicates(notes_to_import, unique_field)
    existing_notes = fetch_existing_notes(deck_name, unique_field)

    print('Updating existing notes...')
    notes_to_add = []
    num_notes_updated: int = 0
    updated_notes: list[str] = []
    for note in notes_to_import:
        unique_value = note['fields'][unique_field]
        if unique_value in existing_notes:
            existing_note = existing_notes[unique_value]
            if note['fields'] != existing_note['fields']:
                note['id'] = existing_note['noteId']
                make_anki_request('updateNoteFields', params={'note': note})
                num_notes_updated += 1
                updated_notes.append(unique_value)
        else:
            notes_to_add.append(note)

    print(f'{num_notes_updated} notes updated: {updated_notes}')

    print(f'{len(notes_to_add)} notes to add')
    if notes_to_add:
        print('Adding new notes...')
        make_anki_request('addNotes', params={'notes': notes_to_add})

    print('Import completed.')


def fetch_existing_notes(deck_name: str, unique_field: str) -> dict[str, dict]:
    print('Fetching existing notes...')
    find_notes_params = {'query': f'deck:"{deck_name}"'}
    response = make_anki_request('findNotes', params=find_notes_params)
    existing_note_ids = response['result']
    if not existing_note_ids:
        existing_notes = {}
        print('No existing notes found in the deck.')
        return existing_notes

    notes_info_params = {'notes': existing_note_ids}
    response = make_anki_request('notesInfo', params=notes_info_params)
    existing_notes_info = response['result']

    existing_notes_info = [
        _extract_note_data_from_info(note_info)
        for note_info in existing_notes_info
    ]

    # Key the notes by the unique field value to make it easier to look up
    existing_notes = {
        note['fields'][unique_field]: note
        for note in existing_notes_info
    }
    print(f'Found {len(existing_notes)} existing notes.')
    return existing_notes


def _extract_note_data_from_info(note_info: dict) -> dict:
    extracted_note_info = filter_by_keys(note_info, ['noteId', 'fields'])
    extracted_note_info['fields'] = {
        field_name: field_info['value']
        for field_name, field_info in note_info['fields'].items()
    }
    return extracted_note_info


def filter_by_keys(dictionary: dict, keys: list[str]) -> dict:
    return {key: dictionary[key] for key in keys if key in dictionary}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python import-csv-to-anki.py <csv_file_path>')
        sys.exit(1)

    filename = sys.argv[1]
    import_csv_to_anki(filename)
