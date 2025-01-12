# Prerequisites
## Installing the AnkiConnect Add-on
- Open Anki.
- Go to **Tools** > **Add-ons** > **Get Add-ons**.
- Enter the code `2055492159` and click **OK**.
- Restart Anki.

## Google credentials
- Ensure that an API key is generated so you can use the Google Spreadsheet API.
- The credentials should be stored in a JSON file. 
- The filename must be added to `settings.py` as `SERVICE_ACCOUNT_FILE`.

## Spreadsheets
- The script is designed to work with a single Google Spreadsheet with multiple tabs.
- The ID of the spreadsheet must be added to `settings.py` as `SPREADSHEET_ID`. You can find the ID in the URL of the spreadsheet.

## Decks and models
The decks and models specified in `decks.py` must be present in Anki.

# Dependencies
Install the dependencies from the requirements file:
```bash
pip install -r requirements.txt
```


