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


def download_sheet(spreadsheet_key: str, sheet_name: str) -> str | None:
    assert settings.SERVICE_ACCOUNT_FILE, 'SERVICE_ACCOUNT_FILE is not set'
    assert spreadsheet_key in settings.SPREADSHEETS

    credentials = Credentials.from_service_account_file(
        settings.SERVICE_ACCOUNT_FILE, scopes=settings.SCOPES
    )
    service = build('sheets', 'v4', credentials=credentials)

    spreadsheet_id = settings.SPREADSHEETS[spreadsheet_key]
    values = get_sheet_values(service, spreadsheet_id, sheet_name)
    if not values:
        print('No data found.')
        return

    spreadsheet_title = get_spreadsheet_title(service, spreadsheet_id)
    filename = f'{spreadsheet_title} - {sheet_name}.csv'
    write_to_csv(values, filename)
    print(f'Sheet "{sheet_name}" saved as "{filename}"')
    return filename


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python download_sheet.py <Mixed|ITA|ESP|FRA|SWE> <sheet_name>')
        sys.exit(1)

    spreadsheet_key = sys.argv[1]
    sheet_name = sys.argv[2]
    download_sheet(spreadsheet_key, sheet_name)
