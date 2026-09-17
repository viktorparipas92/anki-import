import argparse
import sys

import settings
import sheets
from dictionaries import _http, svensk_ordbok, wordreference
from fill_translations import (
    DEFAULT_COLUMNS,
    FILLABLE_COLUMNS,
    LANGUAGE,
    fill_translations,
    skip_ambiguous_word,
)

SWEDISH_ONLY_ARGUMENTS = ('--columns', '--language', '--no-prompt')
TRANSLATION_COLUMN = 'English'
PRONUNCIATION_COLUMN = 'Pronunciation'
ARTICLE_COLUMN = 'Article'
TRIGGER_COLUMNS = (TRANSLATION_COLUMN, PRONUNCIATION_COLUMN, ARTICLE_COLUMN)
WORDREFERENCE_HEADWORD_COLUMNS = (
    'French', 'Spanish', 'Italian', 'Origin', 'Source', 'Source_pk'
)
WORD_TYPES_BY_SHEET_NAME = {
    'Adjectives': 'adj',
    'Nouns': 'n',
    'Verbs': 'v',
}
SHEET_NAMES_BY_SPREADSHEET = {'ITA': ('Nouns', 'Adjectives', 'Verbs')}
WORD_TYPE_COLUMN = 'Word type'
WORD_SUBTYPE_COLUMN = 'Word subtype'
ARTICLES_BY_GENDER = {
    wordreference.MASCULINE_NOUN: 'un',
    wordreference.FEMININE_NOUN: 'une',
}


def choose_entry(
    headword: str, entries: list[svensk_ordbok.Entry]
) -> svensk_ordbok.Entry | None:
    """Ask which Svensk ordbok article to use for a word that has several."""
    print(f'\n"{headword}" has {len(entries)} Svensk ordbok articles:')
    for number, entry in enumerate(entries, start=1):
        print(f'  {number}. {_describe_entry(entry)}')

    while True:
        answer = input('  Choose a number, or press Enter to skip the word: ').strip()
        if not answer:
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(entries):
            return entries[int(answer) - 1]

        print(f'  Enter a number between 1 and {len(entries)}, or nothing to skip.')


def _describe_known_sheets() -> str:
    descriptions = []
    for spreadsheet_key, sheet_names in SHEET_NAMES_BY_SPREADSHEET.items():
        joined = ', '.join(sheet_names)
        descriptions.append(f'{spreadsheet_key} ({joined})')

    return '; '.join(descriptions)


def get_sheet_names(spreadsheet_key: str, sheet_name: str | None) -> tuple[str, ...]:
    """Take the sheet asked for, or every sheet the spreadsheet is known to fill."""
    if sheet_name:
        return (sheet_name,)

    sheet_names = SHEET_NAMES_BY_SPREADSHEET.get(spreadsheet_key)
    if not sheet_names:
        raise ValueError(
            f'Name the sheet to fill. Only {_describe_known_sheets()} can be left out.'
        )

    return sheet_names


def get_language_key(spreadsheet_key: str, sheet_name: str | None) -> str:
    """Take the language from the spreadsheet, or from the tab when it is not one."""
    if spreadsheet_key in wordreference.LANGUAGE_CODES:
        return spreadsheet_key

    return sheet_name or ''


def parse_arguments() -> argparse.Namespace:
    """Read the command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            'Fill the empty cells in a vocabulary sheet. Swedish is looked up in '
            'Svensk ordbok and Wiktionary; French, Spanish and Italian in '
            'WordReference. Cells that already have a value are never changed.'
        )
    )
    parser.add_argument(
        'spreadsheet',
        help=(
            'A key from settings.SPREADSHEETS '
            f'({"|".join(sorted(settings.SPREADSHEETS))}) or a spreadsheet title'
        ),
    )
    parser.add_argument(
        'sheet',
        nargs='?',
        help=(
            'The name of the sheet (tab) to fill. Left out for a spreadsheet whose '
            f'sheets are known: {_describe_known_sheets()}'
        ),
    )
    parser.add_argument(
        '--columns',
        nargs='+',
        choices=FILLABLE_COLUMNS,
        help=f'Swedish only. Columns to fill (default: {list(DEFAULT_COLUMNS)})',
    )
    parser.add_argument(
        '--language',
        help=(
            'Swedish only. The Wiktionary language section to translate from '
            f'(default: {LANGUAGE})'
        ),
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Look everything up and print the changes without writing them',
    )
    parser.add_argument(
        '--limit', type=int, help='Only process the first N rows missing a translation'
    )
    parser.add_argument(
        '--no-prompt',
        action='store_true',
        help='Swedish only. Skip ambiguous words instead of asking which article to use',
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help=(
            'Ignore the cached dictionary responses in '
            f'{settings.DICTIONARY_CACHE_DIR}/'
        ),
    )
    return parser.parse_args()


def _describe_entry(entry: svensk_ordbok.Entry) -> str:
    label = entry.word_class
    if entry.article:
        label = f'{entry.article} {label}'

    definitions = '; '.join(
        sense.definition for sense in entry.senses if sense.definition
    )
    category = entry.senses[0].category if entry.senses else None
    if category:
        label = f'{label} [{category}]'

    return f'{label}: {definitions}' if definitions else label


def get_wordreference_values(
    word: str, row: dict[str, str], language_key: str, sheet_name: str
) -> dict[str, str]:
    """Look a row's word up and say which of its cells WordReference can fill."""
    word_type = _get_word_type(row, sheet_name)
    word_subtype = row.get(WORD_SUBTYPE_COLUMN, '')
    translation = wordreference.translate(
        word, language_key, word_type, word_subtype
    )
    pronunciation = translation.pronunciation or settings.NO_PRONUNCIATION
    return {
        TRANSLATION_COLUMN: translation.english,
        WORD_SUBTYPE_COLUMN: translation.word_subtype,
        ARTICLE_COLUMN: ARTICLES_BY_GENDER.get(
            translation.gender, settings.NO_PRONUNCIATION
        ),
        PRONUNCIATION_COLUMN: pronunciation,
    }


def _get_word_type(row: dict[str, str], sheet_name: str) -> str:
    """Take the row's own word type, or the one the sheet's name implies."""
    word_type = row.get(WORD_TYPE_COLUMN, '').strip()
    if word_type:
        return word_type

    return WORD_TYPES_BY_SHEET_NAME.get(sheet_name, '')


def print_translations(
    fills: list[sheets.Fill], missing: list[str], dry_run: bool
):
    """Show what WordReference confirmed, and the words it confirmed nothing for."""
    print(f'\n{len(fills)} translations found.')
    if missing:
        print(f'{len(missing)} words left empty, fill these in by hand:')
        for headword in missing:
            print(f'  {headword}')

    if dry_run and fills:
        print('\nDry run: nothing written. Re-run without --dry-run to apply.')


def _get_unusable_arguments(arguments: argparse.Namespace) -> list[str]:
    given = {
        '--columns': arguments.columns is not None,
        '--language': arguments.language is not None,
        '--no-prompt': arguments.no_prompt,
    }
    return [name for name in SWEDISH_ONLY_ARGUMENTS if given[name]]


if __name__ == '__main__':
    arguments = parse_arguments()
    _http.use_cache = not arguments.no_cache
    try:
        language_key = get_language_key(arguments.spreadsheet, arguments.sheet)
        if language_key in wordreference.LANGUAGE_CODES:
            unusable = _get_unusable_arguments(arguments)
            if unusable:
                raise ValueError(
                    f'{", ".join(unusable)} only applies to Swedish, not to '
                    f'{arguments.spreadsheet}.'
                )

            sheet_names = get_sheet_names(arguments.spreadsheet, arguments.sheet)
            for sheet_name in sheet_names:
                print(f'\n=== {sheet_name} ===')
                fills, missing = sheets.fill_columns(
                    arguments.spreadsheet,
                    sheet_name,
                    TRIGGER_COLUMNS,
                    lambda word, row, sheet=sheet_name: get_wordreference_values(
                        word, row, language_key, sheet
                    ),
                    WORDREFERENCE_HEADWORD_COLUMNS,
                    dry_run=arguments.dry_run,
                    limit=arguments.limit,
                )
                print_translations(fills, missing, arguments.dry_run)
        else:
            if not arguments.sheet:
                raise ValueError('Name the sheet to fill.')

            can_prompt = not arguments.no_prompt and sys.stdin.isatty()
            fill_translations(
                arguments.spreadsheet,
                arguments.sheet,
                column_names=tuple(arguments.columns or DEFAULT_COLUMNS),
                language=arguments.language or LANGUAGE,
                disambiguate=choose_entry if can_prompt else skip_ambiguous_word,
                dry_run=arguments.dry_run,
                limit=arguments.limit,
            )
    except ValueError as error:
        print(error)
        sys.exit(1)
