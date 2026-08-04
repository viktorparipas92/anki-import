"""Fill the empty cells of a vocabulary sheet from Svensk ordbok and Wiktionary."""
from collections.abc import Callable, Iterable
from dataclasses import dataclass

import settings
import sheets
from dictionaries import svensk_ordbok, wiktionary

LANGUAGE = 'Swedish'

HEADWORD_COLUMNS = ('Origin', 'Source', 'Swedish')
TRANSLATION_COLUMN = 'English'

DEFAULT_COLUMNS = (TRANSLATION_COLUMN, 'Article', 'Type', 'Category', 'Usage')
FILLABLE_COLUMNS = DEFAULT_COLUMNS + ('Etymology', 'Pronunciation')

WORD_CLASSES_IMPLIED_BY_ARTICLE = frozenset({'substantiv'})
MAX_SENSES_WITHOUT_ENTRY = 3

WIKTIONARY_HEADINGS_BY_SO_WORD_CLASS = {
    'substantiv': ('Noun', 'Proper noun'),
    'verb': ('Verb',),
    'adjektiv': ('Adjective',),
    'adverb': ('Adverb',),
    'pronomen': ('Pronoun',),
    'räkneord': ('Numeral',),
    'preposition': ('Preposition',),
    'konjunktion': ('Conjunction',),
    'subjunktion': ('Conjunction',),
    'interjektion': ('Interjection',),
    'determinerare': ('Determiner',),
}


@dataclass
class Fill:
    """A single value to write into one empty cell."""

    row_number: int
    headword: str
    column_name: str
    value: str


def skip_ambiguous_word(
    headword: str, entries: list[svensk_ordbok.Entry]
) -> svensk_ordbok.Entry | None:
    """Leave a word with several Svensk ordbok articles alone."""
    return None


def fill_translations(
    spreadsheet_key: str,
    sheet_name: str,
    column_names: tuple[str, ...] = DEFAULT_COLUMNS,
    language: str = LANGUAGE,
    disambiguate: Callable = skip_ambiguous_word,
    dry_run: bool = False,
    limit: int | None = None,
) -> list[Fill]:
    """Look up every incomplete row of a sheet and fill in what is missing."""
    scopes = settings.SCOPES if dry_run else settings.WRITE_SCOPES
    service = sheets.build_service(scopes)
    spreadsheet_id = sheets.resolve_spreadsheet_id(service, spreadsheet_key)

    rows = sheets.read_rows(service, spreadsheet_id, sheet_name)
    if not rows:
        print('No data found.')
        return []

    header = [column_name.strip() for column_name in rows[0]]
    headword_column = _get_headword_column(header)
    target_columns = _get_target_columns(header, column_names)
    print(
        f'Headword column: "{header[headword_column]}". '
        f'Filling: {", ".join(header[column] for column in target_columns)}'
    )

    rows_to_fill = _get_rows_missing_translation(
        rows, headword_column, _get_translation_column(header), limit
    )
    if not rows_to_fill:
        print('Nothing to fill: every word already has a translation.')
        return []

    headwords = sorted({rows[index][headword_column].strip() for index in rows_to_fill})
    print(
        f'{len(rows_to_fill)} rows missing a translation, '
        f'{len(headwords)} words to look up'
    )

    print('Fetching Wiktionary entries...')
    wikitext_by_headword = wiktionary.fetch_wikitext(headwords)

    print('Fetching Svensk ordbok entries...')
    fills = []
    skipped_headwords = []
    for index in rows_to_fill:
        row = rows[index]
        headword = row[headword_column].strip()
        entries = svensk_ordbok.look_up(headword)
        entry = _get_matching_entry(entries, row, header)
        if entry is None and len(entries) > 1:
            entry = disambiguate(headword, entries)
            if entry is None:
                skipped_headwords.append(
                    (headword, f'{len(entries)} Svensk ordbok articles, not chosen')
                )
                continue

        english = _get_english(
            wikitext_by_headword.get(headword, ''), language, entry
        )
        if entry is None and not english:
            skipped_headwords.append(
                (headword, 'not in Svensk ordbok or Wiktionary')
            )
            continue

        fills.extend(
            _get_fills(row, index + 1, headword, header, target_columns, entry, english)
        )

    _print_report(fills, skipped_headwords)
    if not fills:
        return []

    if dry_run:
        print('\nDry run: nothing written. Re-run without --dry-run to apply.')
        return fills

    cells = [
        (fill.row_number, header.index(fill.column_name), fill.value) for fill in fills
    ]
    num_cells_updated = sheets.update_cells(
        service, spreadsheet_id, sheet_name, cells
    )
    print(f'\n{num_cells_updated} cells written to "{sheet_name}".')
    return fills


def _get_headword_column(header: list[str]) -> int:
    for column_name in HEADWORD_COLUMNS:
        if column_name in header:
            return header.index(column_name)

    raise ValueError(
        f'No headword column found. Expected one of {list(HEADWORD_COLUMNS)} '
        f'in {header}.'
    )


def _get_target_columns(header: list[str], column_names: tuple[str, ...]) -> list[int]:
    target_columns = [
        header.index(column_name) for column_name in column_names
        if column_name in header
    ]
    if not target_columns:
        raise ValueError(
            f'None of the requested columns {list(column_names)} exist in {header}.'
        )

    return sorted(target_columns)


def _get_translation_column(header: list[str]) -> int:
    if TRANSLATION_COLUMN not in header:
        raise ValueError(
            f'No "{TRANSLATION_COLUMN}" column found in {header}.'
        )

    return header.index(TRANSLATION_COLUMN)


def _get_rows_missing_translation(
    rows: list[list[str]],
    headword_column: int,
    translation_column: int,
    limit: int | None,
) -> list[int]:
    rows_missing_translation = [
        index
        for index, row in enumerate(rows)
        if index > 0
        and row[headword_column].strip()
        and not row[translation_column].strip()
    ]
    return (
        rows_missing_translation[:limit] if limit else rows_missing_translation
    )


def _get_matching_entry(
    entries: list[svensk_ordbok.Entry], row: list[str], header: list[str]
) -> svensk_ordbok.Entry | None:
    if len(entries) <= 1:
        return entries[0] if entries else None

    word_class = _get_cell_value(row, header, 'Type')
    if word_class:
        matching = [entry for entry in entries if entry.word_class == word_class]
        if matching:
            return matching[0]

    noun_article = _get_cell_value(row, header, 'Article')
    if noun_article:
        matching = [entry for entry in entries if entry.article == noun_article]
        if matching:
            return matching[0]

    return None


def _get_english(
    wikitext: str, language: str, entry: svensk_ordbok.Entry | None
) -> str:
    senses = wiktionary.get_english_senses(
        wikitext, language, _get_wiktionary_headings(entry)
    )
    return '; '.join(senses[:_get_num_senses(entry)])


def _get_num_senses(entry: svensk_ordbok.Entry | None) -> int:
    if entry is None:
        return MAX_SENSES_WITHOUT_ENTRY

    return len(entry.senses)


def _get_wiktionary_headings(
    entry: svensk_ordbok.Entry | None,
) -> tuple[str, ...]:
    if entry is None:
        return ()

    return WIKTIONARY_HEADINGS_BY_SO_WORD_CLASS.get(entry.word_class, ())


def _get_fills(
    row: list[str],
    row_number: int,
    headword: str,
    header: list[str],
    target_columns: list[int],
    entry: svensk_ordbok.Entry | None,
    english: str,
) -> list[Fill]:
    values_by_column_name = {'English': english}
    if entry is not None:
        values_by_column_name.update({
            'Article': entry.article or '',
            'Type': (
                ''
                if entry.word_class in WORD_CLASSES_IMPLIED_BY_ARTICLE
                else entry.word_class
            ),
            'Category': _join_senses(sense.category for sense in entry.senses),
            'Usage': _join_senses(sense.usage for sense in entry.senses),
            'Etymology': entry.etymology or '',
            'Pronunciation': entry.pronunciation or '',
        })

    return [
        Fill(
            row_number=row_number,
            headword=headword,
            column_name=header[column],
            value=value,
        )
        for column in target_columns
        if not row[column].strip()
        and (value := values_by_column_name.get(header[column], ''))
    ]


def _join_senses(values: Iterable[str | None]) -> str:
    unique_values = []
    for value in values:
        if value and value not in unique_values:
            unique_values.append(value)

    return '; '.join(unique_values)


def _get_cell_value(row: list[str], header: list[str], column_name: str) -> str:
    if column_name not in header:
        return ''

    return row[header.index(column_name)].strip()


def _print_report(fills: list[Fill], skipped_headwords: list[tuple[str, str]]):
    if skipped_headwords:
        print(f'\n{len(skipped_headwords)} words skipped, fill these in by hand:')
        for headword, reason in skipped_headwords:
            print(f'  {headword} ({reason})')

    if not fills:
        print('\nNo empty cells to fill.')
        return

    headword_by_row = {fill.row_number: fill.headword for fill in fills}
    print(f'\n{len(fills)} cells to fill in {len(headword_by_row)} rows:')
    for row_number, headword in sorted(headword_by_row.items()):
        num_columns = len([fill for fill in fills if fill.row_number == row_number])
        print(f'  {row_number:>5} {headword} ({num_columns} cells)')
