"""Google Sheets access: reading sheets, downloading them as CSV and writing cells."""
import csv

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import settings

CELLS_PER_REQUEST = 500


def build_service(
    scopes: list[str] | None = None,
) -> 'googleapiclient.discovery.Resource':
    """Authenticate the service account and return a Sheets API client."""
    assert settings.SERVICE_ACCOUNT_FILE, 'SERVICE_ACCOUNT_FILE is not set'

    credentials = Credentials.from_service_account_file(
        settings.SERVICE_ACCOUNT_FILE, scopes=scopes or settings.SCOPES
    )
    return build('sheets', 'v4', credentials=credentials)


def get_spreadsheet_title(
    service: 'googleapiclient.discovery.Resource', spreadsheet_id: str
) -> str:
    """Return the spreadsheet's title."""
    spreadsheet_service = service.spreadsheets()
    spreadsheet: dict = spreadsheet_service.get(spreadsheetId=spreadsheet_id).execute()
    return spreadsheet.get('properties', {}).get('title', 'Untitled Spreadsheet')


def resolve_spreadsheet_id(
    service: 'googleapiclient.discovery.Resource', spreadsheet_key: str
) -> str:
    """Look up a spreadsheet ID by SPREADSHEETS key ("SWE") or by title."""
    if spreadsheet_key in settings.SPREADSHEETS:
        return settings.SPREADSHEETS[spreadsheet_key]

    for key, spreadsheet_id in settings.SPREADSHEETS.items():
        if get_spreadsheet_title(service, spreadsheet_id) == spreadsheet_key:
            print(f'Spreadsheet "{spreadsheet_key}" is configured as "{key}"')
            return spreadsheet_id

    raise ValueError(
        f'Unknown spreadsheet "{spreadsheet_key}". '
        f'Use one of {sorted(settings.SPREADSHEETS)} or a spreadsheet title.'
    )


def get_sheet_values(
    service: 'googleapiclient.discovery.Resource',
    spreadsheet_id: str,
    sheet_name: str,
) -> list:
    """Return the values of a sheet, as the API sends them."""
    sheet_range = f'{sheet_name}!A:Z'
    spreadsheet_value_service = service.spreadsheets().values()
    result = spreadsheet_value_service.get(
        spreadsheetId=spreadsheet_id, range=sheet_range
    ).execute()
    print(f'Sheet "{sheet_name}" downloaded')
    return result.get('values', [])


def read_rows(
    service: 'googleapiclient.discovery.Resource',
    spreadsheet_id: str,
    sheet_name: str,
) -> list[list[str]]:
    """Return a sheet's rows, right-padded so an empty cell is never a missing one."""
    rows = get_sheet_values(service, spreadsheet_id, sheet_name)
    if not rows:
        return []

    width = max(len(row) for row in rows)
    return [(row + [''] * width)[:width] for row in rows]


def update_cells(
    service: 'googleapiclient.discovery.Resource',
    spreadsheet_id: str,
    sheet_name: str,
    cells: list[tuple[int, int, str]],
) -> int:
    """Write cells given as (row number, column index, value), touching no others."""
    if not cells:
        return 0

    quoted_sheet_name = "'{}'".format(sheet_name.replace("'", "''"))
    data = [
        {
            'range': f'{quoted_sheet_name}!{get_column_letter(column)}{row}',
            'values': [[value]],
        }
        for row, column, value in cells
    ]

    num_cells_updated = 0
    spreadsheet_value_service = service.spreadsheets().values()
    for index in range(0, len(data), CELLS_PER_REQUEST):
        body = {
            'valueInputOption': 'RAW',
            'data': data[index:index + CELLS_PER_REQUEST],
        }
        response = spreadsheet_value_service.batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        ).execute()
        num_cells_updated += response.get('totalUpdatedCells', 0)

    return num_cells_updated


def get_column_letter(column_index: int) -> str:
    """Turn a zero-based column index into its A1 notation letter(s)."""
    letters = ''
    column_index += 1
    while column_index:
        column_index, remainder = divmod(column_index - 1, 26)
        letters = chr(ord('A') + remainder) + letters

    return letters


def download_sheet(spreadsheet_key: str, sheet_name: str) -> str | None:
    """Save a sheet as CSV and return the filename, or None when it is empty."""
    service = build_service()
    spreadsheet_id = resolve_spreadsheet_id(service, spreadsheet_key)
    values = get_sheet_values(service, spreadsheet_id, sheet_name)
    if not values:
        print('No data found.')
        return None

    spreadsheet_title = get_spreadsheet_title(service, spreadsheet_id)
    filename = f'{spreadsheet_title} - {sheet_name}.csv'
    write_to_csv(values, filename)
    print(f'Sheet "{sheet_name}" saved as "{filename}"')
    return filename


def write_to_csv(values: list, filename: str):
    """Write sheet values to a CSV file."""
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(values)
