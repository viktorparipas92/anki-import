import os
import sys

import settings
from sheets import download_sheet
from anki_actions.import_csv_to_anki import import_csv_to_anki

FRENCH_EXPORT = ('FRA', 'Export')


def get_deck_name(
    spreadsheet_key: str, sheet_name: str, given_name: str | None
) -> str | None:
    """The subdeck to import into, named on the command line or in the environment."""
    if given_name:
        return given_name

    if (spreadsheet_key, sheet_name) != FRENCH_EXPORT:
        return None

    if not settings.LATEST_FRENCH_DECK:
        raise ValueError('Name the deck to import into, or set LATEST_FRENCH_DECK.')

    return settings.LATEST_FRENCH_DECK


if __name__ == '__main__':
    num_arguments = len(sys.argv)
    if num_arguments < 3 or num_arguments > 4:
        print(
            'Usage: python -m scripts.download_and_import <Mixed|ITA|ESP|FRA|SWE> '
            '<sheet_name> [<deck_name>]'
        )
        sys.exit(1)

    spreadsheet_key = sys.argv[1]
    sheet_name = sys.argv[2]
    given_name = sys.argv[3] if num_arguments == 4 else None
    try:
        deck_name = get_deck_name(spreadsheet_key, sheet_name, given_name)
    except ValueError as error:
        print(error)
        sys.exit(1)

    csv_filename = download_sheet(spreadsheet_key, sheet_name)
    if csv_filename is None:
        sys.exit(1)

    try:
        import_csv_to_anki(csv_filename, deck_name)
        print('Import completed successfully.')
    finally:
        os.remove(csv_filename)
        print(f'File "{csv_filename}" removed.')
