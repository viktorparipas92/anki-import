import csv
import sys

import requests

from decks import DECKS


def get_deck_data(filename: str) -> tuple[str, list[str], str]:
    try:
        deck_name = DECKS[filename]['deck_name']
        field_names = DECKS[filename]['field_names']
        model_name = DECKS[filename]['model_name']
        return deck_name, field_names, model_name
    except KeyError:
        raise ValueError(
            f"The file '{filename}' does not have a corresponding deck "
            f"name in the DECKS dictionary. Please add it."
        )


def extract_fields(row: dict, field_names: list[str]) -> dict:
    return {name: row[name] for name in field_names}


def construct_note(
    row: dict, *, field_names: list[str], deck: str, model: str
) -> dict:
    return {
        'deckName': deck,
        'modelName': model,
        'fields': extract_fields(row, field_names),
        'tags': [],
        'options': {
            'allowDuplicate': True,
        }
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


def import_csv_to_anki(filename: str):
    deck_name, field_names, model_name = get_deck_data(filename)
    notes = extract_notes(filename, deck_name, field_names, model_name)
    payload = {
        'action': 'addNotes',
        'version': 6,
        'params': {'notes': notes}
    }
    response = requests.post('http://localhost:8765', json=payload)
    return response.status_code


if __name__ == "__main__":
    print("Hi")
    if len(sys.argv) != 2:
        print("Usage: python import-csv-to-anki.py <csv_file_path>")
        sys.exit(1)

    filename = sys.argv[1]
    result = import_csv_to_anki(filename)
    print(result)