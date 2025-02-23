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

# How to run the script
```bash
python download_and_import.py <Mixed|FRA|ESP|ITA> <sheet_name>
```

# Deployment to NAS
## Enable SSH
- Go to **Control Panel** > **Terminal & SNMP** and check **Enable SSH service**.
- Note the port number.
- This enables SSHing into the NAS using password authentication.

### Add the public key to the server
- On the local machine, display the public key.
```bash
cat ~/.ssh/id_rsa.pub
```
- Copy it to the clipboard.
- On the server, add the key to the authorized keys file.
```bash
sudo vi /var/services/homes/<USERNAME>/.ssh/authorized_keys
# Paste the public key and save the file
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

### Add 