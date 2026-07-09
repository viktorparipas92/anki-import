# Prerequisites
## Installing the AnkiConnect Add-on
- Open Anki.
- Go to **Tools** > **Add-ons** > **Get Add-ons**.
- Enter the code `2055492159` and click **OK**.
- Restart Anki. 

## Google credentials
- Ensure that an API key is generated so you can use the Google Spreadsheet API.
  1. Go to https://console.cloud.google.com
  2. Go to **IAM and Admin** > **Service Accounts**
  3. Create new API key, and it will be automatically downloaded.
- The credentials should be stored in a JSON file. 
- The filename must be added to `settings.py` as `SERVICE_ACCOUNT_FILE`.

## Spreadsheets
- The scripts work with multiple Google Spreadsheets, each with multiple tabs (sheets).
- The column names in a sheet must match the field names of the specified model.
- Each spreadsheet ID must be added to the `SPREADSHEETS` dict in `settings.py`, keyed by language (e.g. `Mixed`, `FRA`, `ESP`, `ITA`, `SWE`). You can find the ID in the spreadsheet URL.
- Each spreadsheet needs to be shared with the service account.

## Decks and models
The decks and models specified in `decks.py` must be present in Anki.

# Dependencies
Install the dependencies from the requirements file:
```bash
pip install -r requirements.txt
```

# How to run

Run all commands from the repository root, so the `scripts` and `anki_actions`
packages are importable.

The code is organised as:
- `anki_actions/` — modules that talk to Anki (`sync`, `create_deck`, `import_csv_to_anki`, `get_deck_id`, `get_model_id`).
- `scripts/` — entry points (`update_all_decks`, `download_and_import`).
- `anki_requests.py`, `settings.py`, `download_sheet.py`, `decks.py` — shared helpers, config and data at the root.

## Import a single sheet
```bash
python -m scripts.download_and_import <Mixed|FRA|ESP|ITA|SWE> <sheet_name> [<deck_name>]
```

### Examples
```bash
python -m scripts.download_and_import FRA Export "A2-B1::21. L'argent, la banque"
python -m scripts.download_and_import Mixed GER
python -m scripts.download_and_import ESP "Nouns - Translation"
python -m scripts.download_and_import ITA "Nouns - Translation"
```

## Import everything, then sync
`update_all_decks` opens Anki if needed and imports every configured sheet.
```bash
python -m scripts.update_all_decks -lfd "<latest French deck>"
python -m anki_actions.sync
```

## Sync to AnkiWeb
```bash
python -m anki_actions.sync
```

## Scheduled run
A user cron job runs the full import + sync daily at 12:00 (see `crontab -l`):
```
0 12 * * * cd <repo> && . .venv/bin/activate && python -m scripts.update_all_decks -lfd "<latest French deck>" && python -m anki_actions.sync
```
# Deployment to NAS
## Enable SSH
- Go to **Control Panel** > **Terminal & SNMP** and check **Enable SSH service**.
- Note the port number.
- This enables SSHing into the NAS using password authentication.

### Add the public key to the server
```bash
ssh-copy-id -p <PORT> -i ~/.ssh/id_rsa.pub <USERNAME>@<HOST>
```
- Set up file permissions
```bash
chmod 700 /var/services/homes/<USERNAME>/.ssh
sudo chown viktor-nas-admin:users /var/services/homes/<USERNAME>/.ssh/authorized_keys
chmod 600 /var/services/homes/<USERNAME>/.ssh/authorized_keys
```
- Enable public key authentication in the SSH configuration file.
```bash
sudo vi /etc/ssh/sshd_config
# Uncomment the line `PubkeyAuthenticatigion yes`
# Uncomment the line `AuthorizedKeysFile .ssh/authorized_keys
```

## Connect to the server
```bash
ssh <USERNAME>@<NAS_IP_ADDRESS> -p <PORT>
```
