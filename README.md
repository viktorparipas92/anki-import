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
- The script is designed to work with a single Google Spreadsheet with multiple tabs.
- The column names in the spreadsheet must match the field names of the specified model.
- The ID of the spreadsheet must be added to `settings.py` as `SPREADSHEET_ID`. You can find the ID in the URL of the spreadsheet.
- The spreadsheet needs to be shared with the service account.

## Decks and models
The decks and models specified in `decks.py` must be present in Anki.

# Dependencies
Install the dependencies from the requirements file:
```bash
pip install -r requirements.txt
```

# How to run the script
```bash
python download_and_import.py <Mixed|FRA|ESP|ITA> <sheet_name>
```

## Examples
```bash
python download_and_import.py FRA Export "A2-B1::21. L'argent, la banque"
python download_and_import.py Mixed <FRA|ITA|GER|SWE>
python download_and_import.py ESP "Nouns - Translation"
python download_and_import.py ITA "Nouns - Translation"

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
