# Local use

## Prerequisites
### Installing the AnkiConnect Add-on
- Open Anki.
- Go to **Tools** > **Add-ons** > **Get Add-ons**.
- Enter the code `2055492159` and click **OK**.
- Restart Anki. 

### Google credentials
- Ensure that an API key is generated so you can use the Google Spreadsheet API.
  1. Go to https://console.cloud.google.com
  2. Go to **IAM and Admin** > **Service Accounts**
  3. Create new API key, and it will be automatically downloaded.
- The credentials should be stored in a JSON file. 
- The filename must be added to `settings.py` as `SERVICE_ACCOUNT_FILE`.

### Spreadsheets
- The scripts work with multiple Google Spreadsheets, each with multiple tabs (sheets).
- The column names in a sheet must match the field names of the specified model.
- Each spreadsheet ID must be added to the `SPREADSHEETS` dict in `settings.py`, keyed by language (e.g. `Mixed`, `FRA`, `ESP`, `ITA`, `SWE`). You can find the ID in the spreadsheet URL.
- Each spreadsheet needs to be shared with the service account.

### Decks and models
The decks and models specified in `decks.py` must be present in Anki.

## Dependencies
Install the dependencies from the requirements file:
```bash
pip install -r requirements.txt
```

## How to run
Run all commands from the repository root, so the `scripts` and `anki_actions`
packages are importable.

The code is organised as:
- `anki_actions/` — modules that talk to Anki (`sync`, `create_deck`, `import_csv_to_anki`, `get_deck_id`, `get_model_id`).
- `dictionaries/` — dictionary clients (`svensk_ordbok`, `wiktionary`).
- `books/` — the French book's glossary (`french_glossary`) and the OCR that reads its scanned pages.
- `scripts/` — entry points (`update_all_decks`, `download_and_import`, `fill_translations`, `import_french_glossary`).
- `anki_requests.py`, `settings.py`, `sheets.py`, `fill_translations.py`, `decks.py` — shared logic, config and data at the root.

### Import a single sheet
```bash
python -m scripts.download_and_import <Mixed|FRA|ESP|ITA|SWE> <sheet_name> [<deck_name>]
```

#### Examples
```bash
python -m scripts.download_and_import FRA Export "A2-B1::21. L'argent, la banque"
python -m scripts.download_and_import Mixed GER
python -m scripts.download_and_import ESP "Nouns - Translation"
python -m scripts.download_and_import ITA "Nouns - Translation"
```

### Fill in missing translations
Fills the empty cells of a sheet from Svensk ordbok and English Wiktionary.
Cells that already have a value are never changed. Needs edit access to the
spreadsheet.

```bash
python -m scripts.fill_translations <Mixed|FRA|ESP|ITA|SWE> <sheet_name> [--dry-run]
```

#### Examples
```bash
python -m scripts.fill_translations SWE Input --dry-run
python -m scripts.fill_translations SWE Input
```

`Article`, `Type`, `Category`, `Usage` and `English` are filled by default; ask
for `Etymology` or `Pronunciation` with `--columns`. See `--help` for the rest.

### Add the French book's glossary to the Collection sheet
Adds every word from the index of *Vocabulaire Progressif du Français* that the
`Collection` sheet does not have yet, at the bottom, to be sorted by hand
afterwards. Existing rows are never touched. Needs edit access to the spreadsheet.

```bash
python -m scripts.import_french_glossary <path to the PDF> --from p --dry-run
python -m scripts.import_french_glossary <path to the PDF> --from p
```

`--from` starts partway through the alphabet. A new word gets its `Word type`, a
noun's gender as `Word subtype`, `fam` where the book stars the word, and the
`--chapter` and `--tag` given on the command line; the rest is left to fill in by
hand, as are the few words OCR mangles, which are listed and left out.

The book is a scan, so its pages are read with the OCR built into macOS. Those
dependencies are macOS only and therefore kept out of `requirements.txt`:
```bash
pip install -r requirements-ocr.txt
```

### Import everything, then sync
`update_all_decks` opens Anki if needed and imports every configured sheet.
```bash
python -m scripts.update_all_decks -lfd "<latest French deck>"
python -m anki_actions.sync
```

### Sync to AnkiWeb
```bash
python -m anki_actions.sync
```

### Scheduled run
Local only — the NAS uses DSM Task Scheduler instead. A user cron job runs the
full import + sync daily at 12:00 (see `crontab -l`):
```
0 12 * * * cd <repo> && . .venv/bin/activate && python -m scripts.update_all_decks -lfd "<latest French deck>" && python -m anki_actions.sync
```

# Use on the NAS
Anki runs in one container, the importer in another. Everything above keeps
working locally without any of this.

|  | Local | NAS |
| --- | --- | --- |
| Anki client | your desktop app, opened by the scripts | `anki-desktop` container, started by Compose |
| Running a command | `python -m scripts.<name>` | `sudo docker compose --profile on-demand run --rm anki-importer python -m scripts.<name>` |
| Latest French deck | `-lfd "<deck>"` | `LATEST_FRENCH_DECK` in `.env` |
| Google credentials | `secrets/` in the repo | the same files, mounted read-only |
| Dependencies | `pip install -r requirements.txt` | built into the importer image |
| Scheduling | user cron | DSM Task Scheduler |

## Prerequisites
Everything here has to be done by hand, once.

### Enable SSH — in DSM, in your browser
- Go to **Control Panel** > **Terminal & SNMP** and check **Enable SSH service**.
- Note the port number shown next to it. It is currently `23232`.
- This enables SSHing into the NAS using password authentication.

### Connect to the server — from your own machine
`<USERNAME>` is a DSM account in the **administrators** group, since DSM refuses
SSH for anyone else, and you log in with that account's DSM password.
`<NAS_IP_ADDRESS>` is under **Control Panel** > **Network** > **Network Interface**.
```bash
ssh <USERNAME>@<NAS_IP_ADDRESS> -p 23232
```

### Add the public key to the server — from your own machine
Optional, for logging in without a password. The deploy does not need it, since it
runs on the NAS itself.
```bash
ssh-copy-id -p 23232 -i ~/.ssh/id_ed25519.pub <USERNAME>@<NAS_IP_ADDRESS>
```
- Set up file permissions
```bash
chmod 700 /var/services/homes/<USERNAME>/.ssh
sudo chown <USERNAME>:users /var/services/homes/<USERNAME>/.ssh/authorized_keys
chmod 600 /var/services/homes/<USERNAME>/.ssh/authorized_keys
```
- Enable public key authentication in the SSH configuration file.
```bash
sudo vi /etc/ssh/sshd_config
# Uncomment the line `PubkeyAuthentication yes`
# Uncomment the line `AuthorizedKeysFile .ssh/authorized_keys`
```

### Allow docker without a password — on the NAS, over SSH
```bash
which docker
echo '<USERNAME> ALL=(ALL) NOPASSWD: /usr/local/bin/docker' | sudo tee -a /etc/sudoers
sudo -n docker ps
```

### Install the GitHub Actions runner — on the NAS, over SSH
The workflow runs on `self-hosted`, because GitHub's hosted runners cannot reach the
NAS on the LAN. Keep the repository private: a public one lets any pull request run
code on the runner.
```bash
uname -m    # x86_64 -> linux-x64, aarch64 -> linux-arm64
mkdir -p ~/actions-runner && cd ~/actions-runner
```
Take the `curl`, `tar` and `./config.sh` lines from **Settings** > **Actions** >
**Runners** > **New self-hosted runner** > **Linux**; they carry the version and a
registration token. Then:
```bash
sudo ./svc.sh install && sudo ./svc.sh start
```
If `svc.sh` fails for lack of systemd, run `./run.sh` from a **Task Scheduler**
**Boot-up** trigger instead. The runner must show *Idle* before pushing.

### Install Anki — in your browser
Only possible once the first deploy has started the container, which ships
without Anki itself.
1. Open `http://<NAS_HOST>:3000`. In the launcher, choose a version and enter
   `25.9.5`. Not the latest, which asks for `anki-release==26.8` and was never
   published to PyPI, and not `26.5`, which needs Python 3.10 while the launcher
   still declares support for 3.9, so `uv` cannot resolve it.
2. Install the AnkiConnect add-on as under **Local use**, then restart Anki
   (right-click the desktop > **Anki**). It then listens on `0.0.0.0:8765` inside
   the Docker network.
3. Log in to AnkiWeb, so `sync` works.

### Schedule the daily run — in DSM, in your browser
**Control Panel** > **Task Scheduler**, a user-defined script at 12:00:
```bash
cd <NAS_PATH> && sudo docker compose --profile on-demand run --rm anki-importer
```

## Deploy
Pushing to `main` deploys, via `.github/workflows/deploy-to-synology.yml`. Set
these repository secrets under **Settings** > **Secrets and variables** >
**Actions**:

| Secret | Value |
| --- | --- |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | the whole service account JSON file |

And these repository variables, on the same page:

| Variable | Value |
| --- | --- |
| `LATEST_FRENCH_DECK` | e.g. `A2-B1::26. Others` |
| `TZ` | optional, e.g. `Europe/Stockholm` |

They have to be repository-level, not environment-level, since the workflow declares
no environment. `NAS_PATH` is at the top of the workflow.
`GOOGLE_SERVICE_ACCOUNT_JSON` and `LATEST_FRENCH_DECK` are written to the NAS on
every deploy; leave either unset to keep the file already there instead.

## How to run
The scheduled task imports everything and syncs. Run it by hand the same way, or
any other entry point:
```bash
sudo docker compose --profile on-demand run --rm anki-importer
sudo docker compose --profile on-demand run --rm anki-importer python -m scripts.fill_translations SWE Input --dry-run
```
The importer is behind the `on-demand` profile, so `docker compose up` never
starts it.
