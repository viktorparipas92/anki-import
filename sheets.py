"""Google Sheets access: reading sheets, downloading them as CSV and writing cells."""
import csv
from collections.abc import Callable
from dataclasses import dataclass

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import settings

CELLS_PER_REQUEST = 500
NOTHING_FOUND = '-'
FILL_BATCH_SIZE = 50


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

    escaped_sheet_name = sheet_name.replace("'", "''")
    quoted_sheet_name = f"'{escaped_sheet_name}'"
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


def append_rows(
    service: 'googleapiclient.discovery.Resource',
    spreadsheet_id: str,
    sheet_name: str,
    rows: list[list[str]],
) -> int:
    """Add rows after the last used row of a sheet and return how many landed."""
    if not rows:
        return 0

    escaped_sheet_name = sheet_name.replace("'", "''")
    quoted_sheet_name = f"'{escaped_sheet_name}'"
    response = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f'{quoted_sheet_name}!A:A',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': rows},
    ).execute()
    return response.get('updates', {}).get('updatedRows', 0)


@dataclass
class Fill:
    """The values found for the empty cells of one row."""

    row_number: int
    headword: str
    values: dict[str, str]


def fill_columns(
    spreadsheet_key: str,
    sheet_name: str,
    trigger_column: str,
    get_values: Callable[[str, dict[str, str]], dict[str, str]],
    headword_columns: tuple[str, ...],
    dry_run: bool = False,
    limit: int | None = None,
    batch_size: int = FILL_BATCH_SIZE,
) -> tuple[list[Fill], list[str]]:
    """Fill every row whose `trigger_column` is empty with what `get_values` returns.

    `get_value` is called with the row's headword and the whole row as a mapping of
    column name to value. Returns the fills and the headwords it found nothing for.
    Cells that already have a value are never read from or written to.
    """
    scopes = settings.SCOPES if dry_run else settings.WRITE_SCOPES
    service = build_service(scopes)
    spreadsheet_id = resolve_spreadsheet_id(service, spreadsheet_key)
    rows = read_rows(service, spreadsheet_id, sheet_name)
    if not rows:
        return [], []

    header = [heading.strip() for heading in rows[0]]
    headword_column = _get_column(header, headword_columns)
    trigger = _get_column(header, (trigger_column,))
    print(f'Headword column: "{header[headword_column]}"')

    row_numbers = _get_empty_rows(rows, headword_column, trigger, limit)
    if not row_numbers:
        print(f'Nothing to fill: every word already has a "{trigger_column}".')
        return [], []

    print(f'{len(row_numbers)} rows missing a "{trigger_column}"')
    fills = []
    missing = []
    pending = []
    for row_number in row_numbers:
        row = rows[row_number - 1]
        headword = row[headword_column].strip()
        values = _get_writable_values(
            get_values(headword, dict(zip(header, row))), row, header
        )
        if dry_run:
            print(f'  {row_number:>5} {headword:<28} {_describe(values)}', flush=True)
        if trigger_column in values:
            fills.append(Fill(row_number, headword, values))
            pending.append(fills[-1])
        else:
            missing.append(headword)

        if not dry_run and len(pending) >= batch_size:
            _write_fills(service, spreadsheet_id, sheet_name, header, pending)
            pending = []

    if not dry_run:
        _write_fills(service, spreadsheet_id, sheet_name, header, pending)

    return fills, missing


def _write_fills(
    service: 'googleapiclient.discovery.Resource',
    spreadsheet_id: str,
    sheet_name: str,
    header: list[str],
    fills: list[Fill],
):
    if not fills:
        return

    cells = [
        (fill.row_number, header.index(column_name), value)
        for fill in fills
        for column_name, value in fill.values.items()
    ]
    num_cells_updated = update_cells(service, spreadsheet_id, sheet_name, cells)
    print(
        f'  {num_cells_updated} cells written, through row {fills[-1].row_number}',
        flush=True,
    )


def _get_writable_values(
    values: dict[str, str], row: list[str], header: list[str]
) -> dict[str, str]:
    writable = {}
    for column_name, value in values.items():
        if not value or column_name not in header:
            continue
        if not row[header.index(column_name)].strip():
            writable[column_name] = value

    return writable


def _describe(values: dict[str, str]) -> str:
    if not values:
        return NOTHING_FOUND

    return '  |  '.join(f'{value}' for value in values.values())


def _get_column(header: list[str], column_names: tuple[str, ...]) -> int:
    for column_name in column_names:
        if column_name in header:
            return header.index(column_name)

    raise ValueError(
        f'No column found. Expected one of {list(column_names)} in {header}.'
    )


def _get_empty_rows(
    rows: list[list[str]],
    headword_column: int,
    target_column: int,
    limit: int | None,
) -> list[int]:
    row_numbers = [
        index + 1
        for index, row in enumerate(rows)
        if index > 0
        and row[headword_column].strip()
        and not row[target_column].strip()
    ]
    return row_numbers[:limit] if limit else row_numbers
