import argparse
import subprocess

from decks import DECKS

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-lfd', '--latest-french-deck', required=True)
    args = parser.parse_args()

    script_name = 'download_and_import.py'
    mixed_spreadsheet_languages = ['GER', 'ITA', 'FRA', 'SWE']
    for language in mixed_spreadsheet_languages:
        subprocess.run(['python3', script_name, 'Mixed', language])

    latest_french_deck = args.latest_french_deck  # i.e 'A2-B1::16. Transports, circulation'
    subprocess.run(['python3', script_name, 'FRA', 'Export', latest_french_deck])

    countries_by_spreadsheet_name = {
        'Spanish grammar & vocab': 'ESP',
        'Italian grammar & vocab': 'ITA',
    }
    for spreadsheet_name, country_code in countries_by_spreadsheet_name.items():
        for sheet_name in DECKS[spreadsheet_name]:
            arg_name = sheet_name.split('.')[0]
            command = ['python', script_name, country_code, f'{arg_name}']
            print(f'Running command: {' '.join(command)}')
            subprocess.run(command)
