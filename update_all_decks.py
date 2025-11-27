import argparse
import subprocess
import time

from anki_requests import make_anki_request



def wait_for_ankiconnect(timeout: int = 30, delay: float = 1) -> bool:
    """Wait until AnkiConnect responds."""
    start_time = time.time()
    anki_started = False
    while True:
        try:
            version_data = make_anki_request('version')
            print(f'Anki connect is ready. Version: {version_data["result"]}.')
            return True
        except Exception:
            print('AnkiConnect is not running yet.')
            if not anki_started:
                print(f'Opening Anki...')
                subprocess.Popen(['open', '-a', 'Anki'])
                anki_started = True

            if time.time() - start_time > timeout:
                return False

            time.sleep(delay)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-lfd', '--latest-french-deck', required=True)
    args = parser.parse_args()

    is_anki_ready = wait_for_ankiconnect()
    if not is_anki_ready:
        raise Exception('AnkiConnect is not running. Exiting.')

    from decks import DECKS

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

    close_at_end = False
    if close_at_end:
        subprocess.run(['osascript', '-e', 'quit app "Anki"'])
