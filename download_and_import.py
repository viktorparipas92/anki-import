import os
import sys

from download_sheet import download_sheet
from import_csv_to_anki import import_csv_to_anki

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python download_and_import.py <sheet_name>')
        sys.exit(1)

    sheet_name = sys.argv[1]
    csv_filename = download_sheet(sheet_name)
    if csv_filename is None:
        sys.exit(1)

    import_csv_to_anki(csv_filename)

    os.remove(csv_filename)
    print(f'File "{csv_filename}" removed.')
