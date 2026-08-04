import argparse
import sys

import settings
from dictionaries import _http, svensk_ordbok
from fill_translations import (
    DEFAULT_COLUMNS,
    FILLABLE_COLUMNS,
    LANGUAGE,
    fill_translations,
    skip_ambiguous_word,
)


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


def parse_arguments() -> argparse.Namespace:
    """Read the command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            'Fill the empty cells in a vocabulary sheet from Svensk ordbok and '
            'Wiktionary. Cells that already have a value are never changed.'
        )
    )
    parser.add_argument(
        'spreadsheet',
        help=(
            'A key from settings.SPREADSHEETS '
            f'({"|".join(sorted(settings.SPREADSHEETS))}) or a spreadsheet title'
        ),
    )
    parser.add_argument('sheet', help='The name of the sheet (tab) to fill')
    parser.add_argument(
        '--columns',
        nargs='+',
        choices=FILLABLE_COLUMNS,
        default=list(DEFAULT_COLUMNS),
        help='Columns to fill (default: %(default)s)',
    )
    parser.add_argument(
        '--language',
        default=LANGUAGE,
        help='The Wiktionary language section to translate from (default: %(default)s)',
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
        help='Skip ambiguous words instead of asking which article to use',
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


if __name__ == '__main__':
    arguments = parse_arguments()
    _http.use_cache = not arguments.no_cache
    can_prompt = not arguments.no_prompt and sys.stdin.isatty()
    try:
        fill_translations(
            arguments.spreadsheet,
            arguments.sheet,
            column_names=tuple(arguments.columns),
            language=arguments.language,
            disambiguate=choose_entry if can_prompt else skip_ambiguous_word,
            dry_run=arguments.dry_run,
            limit=arguments.limit,
        )
    except ValueError as error:
        print(error)
        sys.exit(1)
