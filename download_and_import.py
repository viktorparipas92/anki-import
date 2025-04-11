import os
import sys

from download_sheet import download_sheet
from import_csv_to_anki import import_csv_to_anki


if __name__ == '__main__':
    num_arguments = len(sys.argv)
    if num_arguments < 3 or num_arguments > 4:
        print(
            'Usage: python download_and_import.py <Mixed|ITA|ESP|FRA|SWE> '
            '<sheet_name> [<deck_name>]'
        )
        sys.exit(1)

    spreadsheet_key = sys.argv[1]
    sheet_name = sys.argv[2]
    csv_filename = download_sheet(spreadsheet_key, sheet_name)
    if csv_filename is None:
        sys.exit(1)

    deck_name = sys.argv[3] if num_arguments == 4 else None
    try:
        import_csv_to_anki(csv_filename, deck_name)
        print('Import completed successfully.')
    finally:
        os.remove(csv_filename)
        print(f'File "{csv_filename}" removed.')
