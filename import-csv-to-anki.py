import csv
import sys

import requests
from requests import Response

from decks import DECKS


ANKI_CONNECT_URL = 'http://localhost:8765'


def get_deck_data(filename: str) -> tuple[str, list[str], str, str]:
    try:
        deck_name = DECKS[filename]['deck_name']
        field_names = DECKS[filename]['field_names']
        model_name = DECKS[filename]['model_name']
        unique_field = DECKS[filename]['unique_field']
        return deck_name, field_names, model_name, unique_field
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


def import_csv_to_anki(filename: str):
    """
    Perform a bulk import of notes into Anki, updating existing notes or adding new ones.
    """
    deck_name, field_names, model_name, unique_field = get_deck_data(filename)
    notes_to_add = extract_notes(filename, deck_name, field_names, model_name)
    notes_to_add = check_for_duplicates(notes_to_add, unique_field)
    existing_notes = fetch_existing_notes(deck_name, unique_field)
    notes_to_add = [
        note for note in notes_to_add
        if note['fields'][unique_field] not in existing_notes
    ]
    print(f'{len(notes_to_add)} notes to add')
    print('Adding new notes...')
    make_anki_request('addNotes', params={'notes': notes_to_add})
    print('Import completed.')


def make_anki_request(action: str, *, params: dict | None = None) -> Response:
    """Send a request to AnkiConnect."""
    payload = {
        'action': action,
        'version': 6,
        'params': params or {}
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload)
    json_response = response.json()
    if error := json_response.get('error'):
        raise Exception(f'AnkiConnect Error: {error}')

    return response


def fetch_existing_notes(deck_name: str, unique_field: str) -> dict[str, int]:
    print('Fetching existing notes...')
    find_notes_params = {'query': f'deck:"{deck_name}"'}
    response = make_anki_request('findNotes', params=find_notes_params)
    existing_note_ids = response.json()['result']
    if not existing_note_ids:
        existing_notes = {}
        print('No existing notes found in the deck.')
    else:
        notes_info_params = {'notes': existing_note_ids}
        response = make_anki_request('notesInfo', params=notes_info_params)
        existing_notes_info = response.json()['result']
        existing_notes = {
            note['fields'][unique_field]['value']: note['noteId']
            for note in existing_notes_info
        }
        print(f'Found {len(existing_notes)} existing notes.')

    return existing_notes


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Usage: python import-csv-to-anki.py <csv_file_path>')
        sys.exit(1)

    filename = sys.argv[1]
    import_csv_to_anki(filename)
