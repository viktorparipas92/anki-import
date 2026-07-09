import argparse
import subprocess

from anki_requests import wait_for_ankiconnect



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-lfd', '--latest-french-deck', required=True)
    args = parser.parse_args()

    is_anki_ready = wait_for_ankiconnect()
    if not is_anki_ready:
        raise Exception('AnkiConnect is not running. Exiting.')

    from decks import DECKS

    download_and_import = ['python', '-m', 'scripts.download_and_import']
    mixed_spreadsheet_languages = ['GER', 'ITA', 'FRA']
    for language in mixed_spreadsheet_languages:
        subprocess.run([*download_and_import, 'Mixed', language])

    latest_french_deck = args.latest_french_deck  # i.e 'A2-B1::16. Transports, circulation'
    subprocess.run([*download_and_import, 'FRA', 'Export', latest_french_deck])

    countries_by_spreadsheet_name = {
        'Spanish grammar & vocab': 'ESP',
        'Italian grammar & vocab': 'ITA',
        'Swedish vocab': 'SWE',
    }
    for spreadsheet_name, country_code in countries_by_spreadsheet_name.items():
        for sheet_name in DECKS[spreadsheet_name]:
            arg_name = sheet_name.split('.')[0]
            command = [*download_and_import, country_code, f'{arg_name}']
            print(f'Running command: {' '.join(command)}')
            subprocess.run(command)

    close_at_end = False
    if close_at_end:
        subprocess.run(['osascript', '-e', 'quit app "Anki"'])
