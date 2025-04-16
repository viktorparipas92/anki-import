import subprocess


if __name__ == '__main__':
    script_name = 'download_and_import.py'
    mixed_spreadsheet_languages = ['GER', 'ITA', 'FRA', 'SWE']
    for language in mixed_spreadsheet_languages:
        subprocess.run(['python3', script_name, 'Mixed', language])

    latest_french_deck = 'A2-B1::16. Transports, circulation'
    subprocess.run(['python3', script_name, 'FRA', 'Export', latest_french_deck])