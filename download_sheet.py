#!/usr/bin/env python3
import csv
import sys

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import settings


def get_spreadsheet_title(
    service: 'googleapiclient.discovery.Resource', spreadsheet_id: str
) -> str:
    spreadsheet_service = service.spreadsheets()
    spreadsheet: dict = spreadsheet_service.get(spreadsheetId=spreadsheet_id).execute()
    return spreadsheet.get('properties', {}).get('title', 'Untitled Spreadsheet')


def get_sheet_values(
    service: 'googleapiclient.discovery.Resource',
    spreadsheet_id: str,
    sheet_name: str,
) -> list:
    sheet_range = f'{sheet_name}!A:Z'
    spreadsheet_value_service = service.spreadsheets().values()
    result = spreadsheet_value_service.get(
        spreadsheetId=spreadsheet_id, range=sheet_range
    ).execute()
    print(f'Sheet "{sheet_name}" downloaded')
    return result.get('values', [])


def write_to_csv(values: list, filename: str):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(values)


def download_sheet(sheet_name: str) -> str | None:
    assert settings.SERVICE_ACCOUNT_FILE, 'SERVICE_ACCOUNT_FILE is not set'
    assert settings.SPREADSHEET_ID, 'SPREADSHEET_ID is not set'
    credentials = Credentials.from_service_account_file(
        settings.SERVICE_ACCOUNT_FILE, scopes=settings.SCOPES
    )
    service = build('sheets', 'v4', credentials=credentials)
    values = get_sheet_values(service, settings.SPREADSHEET_ID, sheet_name)
    if not values:
        print('No data found.')
        return

    spreadsheet_title = get_spreadsheet_title(service, settings.SPREADSHEET_ID)
    filename = f'{spreadsheet_title} - {sheet_name}.csv'
    write_to_csv(values, filename)
    print(f'Sheet "{sheet_name}" saved as "{filename}"')
    return filename


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python download_sheet.py <sheet_name>')
        sys.exit(1)

    sheet_name = sys.argv[1]
    download_sheet(sheet_name)
