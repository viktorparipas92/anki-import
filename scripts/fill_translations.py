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
WORDREFERENCE_HEADWORD_COLUMNS = ('French', 'Spanish', 'Italian')
WORD_TYPE_COLUMN = 'Word type'
WORD_SUBTYPE_COLUMN = 'Word subtype'
PRONUNCIATION_COLUMN = 'Pronunciation'


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
    parser.add_argument('sheet', help='The name of the sheet (tab) to fill')
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
    word: str, row: dict[str, str], language_key: str
) -> dict[str, str]:
    """Look a row's word up and say which of its cells WordReference can fill."""
    translation = wordreference.translate(
        word,
        language_key,
        row.get(WORD_TYPE_COLUMN, ''),
        row.get(WORD_SUBTYPE_COLUMN, ''),
    )
    return {
        TRANSLATION_COLUMN: translation.english,
        WORD_SUBTYPE_COLUMN: translation.word_subtype,
        PRONUNCIATION_COLUMN: translation.pronunciation,
    }


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
        if arguments.spreadsheet in wordreference.LANGUAGE_CODES:
            unusable = _get_unusable_arguments(arguments)
            if unusable:
                raise ValueError(
                    f'{", ".join(unusable)} only applies to Swedish, not to '
                    f'{arguments.spreadsheet}.'
                )

            fills, missing = sheets.fill_columns(
                arguments.spreadsheet,
                arguments.sheet,
                TRANSLATION_COLUMN,
                lambda word, row: get_wordreference_values(
                    word, row, arguments.spreadsheet
                ),
                WORDREFERENCE_HEADWORD_COLUMNS,
                dry_run=arguments.dry_run,
                limit=arguments.limit,
            )
            print_translations(fills, missing, arguments.dry_run)
        else:
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
