"""Add the words of the French book's glossary to the French vocabulary sheet.

The glossary is the index at the back of Vocabulaire Progressif du Français,
whose entries name the word, its grammatical category and the pages it appears
on. The book is a scan and carries no text, so its pages are read with OCR.
"""
import re
import unicodedata
from dataclasses import dataclass, field

import settings
import sheets
from books import _ocr

FRENCH_COLUMN = 'French'
WORD_TYPE_COLUMN = 'Word type'
DEFAULT_CHAPTER = '26'
DEFAULT_TAG = 'A2-B1'

FRENCH_WORD_TYPES_BY_ABBREVIATION = {
    'n': ('n', 'mf'),
    'n.m': ('n', 'm'),
    'n.f': ('n', 'f'),
    'n.m.pl': ('n', 'mpl'),
    'n.f.pl': ('n', 'fpl'),
    'n.pl': ('n', ''),
    'v': ('v', ''),
    'adj': ('adj', ''),
    'adj.invar': ('adj', 'inv'),
    'adj.poss': ('adj', ''),
    'adj.num': ('adj', ''),
    'adv': ('adv', ''),
    'prep': ('prep', ''),
    'pron': ('pron', ''),
    'conj': ('conj', ''),
    'interj': ('interj', ''),
    'loc': ('expr', ''),
    'loc.v': ('loc v', ''),
    'loc.adv': ('loc adv', ''),
    'loc.adj': ('loc adj', ''),
    'loc.prep': ('loc prep', ''),
    'loc.conj': ('loc conj', ''),
    'n.pr': ('n', ''),
    'n.m.ou.f': ('n', 'mf'),
    'n.f.ou.m': ('n', 'mf'),
    'adv.interr': ('adv', ''),
    'adj.interr': ('adj', ''),
    'pron.interr': ('pron', ''),
    'pron.ind': ('pron', ''),
    'pr.ind': ('pron', ''),
    'ad': ('adj', ''),
    'adi': ('adj', ''),
    'ad.invar': ('adj', 'inv'),
    'adi.invar': ('adj', 'inv'),
    'p.p': ('adj', ''),
    'p.pr': ('adj', ''),
    'pr.indef': ('pron', ''),
    'n.t': ('n', 'f'),
    'en.m': ('n', 'm'),
    'en.f': ('n', 'f'),
}

FAMILIAR_MARKER = '*'
FAMILIARITY = 'fam'

PAGE_NUMBERS_PATTERN = re.compile(r'(?<!\d)(?:\d{1,3}(?:\s*[,;]\s*|\s+))*\d{1,3}\s*[,;]?\s*$')
COLUMN_PATTERN = re.compile(r'.+?\([^()]*\)\s*\d[\d\s,;]*')
LEADING_PAGE_NUMBERS_PATTERN = re.compile(r'^(?:\d{1,3}\s*[,;]\s*)+')
TRAILING_GROUP_PATTERN = re.compile(r'\(([^()]*)\)\s*$')
UNOPENED_GROUP_PATTERN = re.compile(r'\s([^()]*)\)\s*$')
REFLEXIVE_WORD_TYPE = ('v', 'refl')
REFLEXIVE_PATTERN = re.compile(r'\(\s*s[\'’]?e?\s*\)')
WORD_TYPES_THAT_CAN_BE_REFLEXIVE = (('v', ''), ('', ''))
FEMININE_FORM_PATTERN = re.compile(r'\s*\([^()]*\)\s*$')
FOOTER_CHARACTERS = '•·'
LETTERS_PATTERN = re.compile(r'[a-zà-öø-ÿ]', re.IGNORECASE)
FEMININE_SUFFIX_PATTERN = re.compile(r',\s*-\S+')
OPTIONAL_PART_PATTERN = re.compile(r'[\[(]([^\])]*)[\])]')
LIGATURES = {'œ': 'oe', 'æ': 'ae'}


@dataclass(frozen=True)
class Entry:
    """One glossary entry, in the sheet's terms rather than the book's."""

    word: str
    word_type: str = ''
    word_subtype: str = ''
    familiarity: str = ''
    page_numbers: tuple[int, ...] = ()

    @property
    def is_suspect(self) -> bool:
        """Say whether OCR left brackets the word cannot sensibly have."""
        return (
            self.word.count('(') != self.word.count(')')
            or self.word.count('[') != self.word.count(']')
        )

    @property
    def key(self) -> tuple[str, str]:
        """The identity of the row: the sheet keeps one row per word per type."""
        return normalise(self.word), self.word_type

    @property
    def variants(self) -> frozenset[str]:
        """Every key this word could already be in the sheet under."""
        return variants(self.word)

    def to_row(self, header: list[str], chapter: str, tag: str) -> list[str]:
        """Lay the entry out as a sheet row, in the header's column order."""
        values_by_column_name = {
            FRENCH_COLUMN: self.word,
            WORD_TYPE_COLUMN: self.word_type,
            'Word subtype': self.word_subtype,
            'Familiarity': self.familiarity,
            'Tags': tag,
            'Chapter': chapter,
        }
        return [values_by_column_name.get(column_name, '') for column_name in header]


@dataclass
class Report:
    """What one run found, so the caller can print it or assert on it."""

    entries: list[Entry] = field(default_factory=list)
    considered: list[Entry] = field(default_factory=list)
    missing: list[Entry] = field(default_factory=list)
    suspect: list[Entry] = field(default_factory=list)
    num_rows_added: int = 0


def normalise(word: str) -> str:
    """Reduce a word to the one key it is counted and sorted under."""
    return _tidy(OPTIONAL_PART_PATTERN.sub(' ', _clean(word)))


def variants(word: str) -> frozenset[str]:
    """Return every key a word could match, since the book and the sheet differ."""
    cleaned = _clean(word)
    forms = {cleaned}
    for part in cleaned.split(','):
        forms.add(OPTIONAL_PART_PATTERN.sub(' ', part))
        forms.add(OPTIONAL_PART_PATTERN.sub(r'\1', part))

    keys = set()
    for form in forms:
        key = _tidy(form)
        if key:
            keys.update({key, _squash(key)})

    return frozenset(keys)


def _clean(word: str) -> str:
    """Level out the spellings that never tell two words apart."""
    word = unicodedata.normalize('NFC', word).replace('\xa0', ' ').replace('’', "'")
    for ligature, letters in LIGATURES.items():
        word = word.replace(ligature, letters)

    word = word.casefold()
    reflexive = REFLEXIVE_PATTERN.search(word)
    if reflexive is not None:
        word = _write_reflexive(word, reflexive.group())

    word = FEMININE_SUFFIX_PATTERN.sub('', word)
    return re.sub(r"^s'\s*", 'se ', word)


def _tidy(form: str) -> str:
    return re.sub(r'\s+', ' ', form).strip(' -,;.!?')


def _squash(form: str) -> str:
    """Reduce a key further, to survive a lost accent or hyphen."""
    decomposed = unicodedata.normalize('NFD', form)
    without_accents = ''.join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r'[^a-z0-9]', '', without_accents)


def sort_key(word: str) -> str:
    """Return the key the book's glossary sorts a word under."""
    key = re.sub(r'^se ', '', normalise(word))
    decomposed = unicodedata.normalize('NFD', key)
    without_accents = ''.join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r'[^a-z0-9 ]', '', without_accents)


def read_french_glossary(pdf_path: str, pages: str = '') -> list[Entry]:
    """Read the book's glossary, OCR'ing its pages when it carries no text."""
    page_numbers = _parse_page_range(pages) if pages else None
    texts = _read_pages(pdf_path, page_numbers)
    if page_numbers is None:
        texts = [text for text in texts if _count_entries(text)]

    entries = []
    for text in texts:
        for line in text.splitlines():
            entries.extend(_parse_line(line))

    return entries


def import_french_glossary(
    pdf_path: str,
    spreadsheet_key: str,
    sheet_name: str,
    start_from: str = '',
    through_page: int | None = None,
    chapter: str = DEFAULT_CHAPTER,
    tag: str = DEFAULT_TAG,
    pages: str = '',
    dry_run: bool = False,
    limit: int | None = None,
) -> Report:
    """Add every glossary word the sheet does not have yet, alphabetically."""
    entries = read_french_glossary(pdf_path, pages)
    print(f'{len(entries)} entries in the glossary')
    if not entries:
        raise ValueError(
            'No glossary entries found. Pass --pages with the page numbers the '
            'glossary is printed on.'
        )

    considered = sorted(entries, key=lambda entry: sort_key(entry.word))
    if start_from:
        cutoff = sort_key(start_from)
        considered = [entry for entry in considered if sort_key(entry.word) >= cutoff]
        print(f'{len(considered)} of them at or after "{start_from}"')

    if through_page is not None:
        considered = [
            entry
            for entry in considered
            if any(number <= through_page for number in entry.page_numbers)
        ]
        print(f'{len(considered)} of them printed on page {through_page} or before')

    scopes = settings.SCOPES if dry_run else settings.WRITE_SCOPES
    service = sheets.build_service(scopes)
    spreadsheet_id = sheets.resolve_spreadsheet_id(service, spreadsheet_key)
    rows = sheets.read_rows(service, spreadsheet_id, sheet_name)
    if not rows:
        raise ValueError(f'Sheet "{sheet_name}" is empty, so it has no header row.')

    header = [column_name.strip() for column_name in rows[0]]
    known = _get_known_variants(rows, header)
    new_entries = _get_missing_entries(considered, known, limit)
    report = Report(
        entries=entries,
        considered=considered,
        missing=[entry for entry in new_entries if not entry.is_suspect],
        suspect=[entry for entry in new_entries if entry.is_suspect],
    )
    num_present = len(
        {normalise(entry.word) for entry in considered if entry.variants & known}
    )
    _print_report(report, num_present, len(rows) - 1, sheet_name)
    if not report.missing:
        return report

    if dry_run:
        print('\nDry run: nothing written. Re-run without --dry-run to apply.')
        return report

    report.num_rows_added = sheets.append_rows(
        service,
        spreadsheet_id,
        sheet_name,
        [entry.to_row(header, chapter, tag) for entry in report.missing],
    )
    print(
        f'\n{report.num_rows_added} rows added to the bottom of "{sheet_name}". '
        f'Sort the sheet by "{FRENCH_COLUMN}" to put them in place.'
    )
    return report


def _read_pages(pdf_path: str, page_numbers: list[int] | None) -> list[str]:
    """Return the text of the PDF's pages, from its text layer or with OCR."""
    texts = _read_text_layer(pdf_path, page_numbers)
    if sum(len(text.strip()) for text in texts) > 0:
        return texts

    print(f'"{pdf_path}" is a scan with no text, reading it with OCR...')
    if page_numbers is not None:
        return _ocr.read_pages(pdf_path, page_numbers)

    return _ocr_from_the_back(pdf_path)


def _read_text_layer(pdf_path: str, page_numbers: list[int] | None) -> list[str]:
    from pypdf import PdfReader

    pages = PdfReader(pdf_path).pages
    if page_numbers is None:
        return [page.extract_text() or '' for page in pages]

    return [pages[number - 1].extract_text() or '' for number in page_numbers]


def _ocr_from_the_back(pdf_path: str, max_pages_scanned: int = 60) -> list[str]:
    """OCR backwards from the last page for as long as the pages are entries."""
    num_pages = _ocr.get_num_pages(pdf_path)
    texts_by_page = {}
    for page_number in range(num_pages, max(num_pages - max_pages_scanned, 0), -1):
        text = _ocr.read_pages(pdf_path, [page_number])[0]
        if _count_entries(text):
            texts_by_page[page_number] = text
            print(f'  page {page_number}: glossary')
        elif texts_by_page:
            break

    if not texts_by_page:
        raise ValueError(
            f'No glossary found in the last {max_pages_scanned} pages of '
            f'"{pdf_path}". Pass --pages with the page numbers it is printed on.'
        )

    return [texts_by_page[number] for number in sorted(texts_by_page)]


def _count_entries(text: str, minimum: int = 5) -> int:
    """Return how many lines of a page are glossary entries, up to `minimum`."""
    num_entries = 0
    for line in text.splitlines():
        num_entries += len(_parse_line(line))
        if num_entries >= minimum:
            return num_entries

    return 0


def _parse_line(line: str) -> list[Entry]:
    """Read one line of an index, which may print several entries side by side."""
    entries = []
    for part in _split_columns(line):
        entries.extend(_parse_entry(part))

    return entries


def _split_columns(line: str) -> list[str]:
    """Split a line the book sets in columns into the entries standing on it."""
    parts = [match.group() for match in COLUMN_PATTERN.finditer(line)]
    return parts if len(parts) > 1 else [line]


def _parse_entry(line: str) -> list[Entry]:
    """Read one glossary line, as the one or more rows the sheet keeps for it."""
    line = unicodedata.normalize('NFC', line).replace('\xa0', ' ').strip()
    if any(character in line for character in FOOTER_CHARACTERS):
        return []

    page_numbers = PAGE_NUMBERS_PATTERN.search(line)
    if page_numbers is None:
        return []

    word = LEADING_PAGE_NUMBERS_PATTERN.sub('', line[:page_numbers.start()].strip())
    word, word_types = _take_word_types(word.strip())
    familiarity = FAMILIARITY if FAMILIAR_MARKER in word else ''
    word = word.replace(FAMILIAR_MARKER, '').strip()

    reflexive = REFLEXIVE_PATTERN.search(word)
    is_verb = all(word_type in WORD_TYPES_THAT_CAN_BE_REFLEXIVE for word_type in word_types)
    if reflexive is not None and is_verb:
        word = _write_reflexive(word, reflexive.group())
        word_types = [REFLEXIVE_WORD_TYPE]
    else:
        word = FEMININE_FORM_PATTERN.sub('', word)

    word = _repair_brackets(word).strip(' .,;:-–—')
    if not _is_headword(word):
        return []

    numbers = tuple(
        int(number) for number in re.findall(r'\d{1,3}', page_numbers.group())
    )
    return [
        Entry(
            word=word,
            word_type=word_type,
            word_subtype=word_subtype,
            familiarity=familiarity,
            page_numbers=numbers,
        )
        for word_type, word_subtype in word_types
    ]


def _take_word_types(word: str) -> tuple[str, list[tuple[str, str]]]:
    """Split the grammatical category off the end of an entry's word."""
    for pattern in (TRAILING_GROUP_PATTERN, UNOPENED_GROUP_PATTERN):
        group = pattern.search(word)
        if group is None:
            continue

        word_types = _parse_word_types(group.group(1))
        if word_types:
            return word[:group.start()].strip(), word_types

    return word, [('', '')]


def _parse_word_types(marker: str) -> list[tuple[str, str]]:
    """Turn a category marker into the types the sheet gives each its own row."""
    word_types = []
    for part in re.split(r'\bet\b|,|/', marker):
        abbreviation = _normalise_abbreviation(part)
        if not abbreviation:
            continue
        if abbreviation not in FRENCH_WORD_TYPES_BY_ABBREVIATION:
            return []

        word_type = FRENCH_WORD_TYPES_BY_ABBREVIATION[abbreviation]
        if word_type not in word_types:
            word_types.append(word_type)

    return word_types


def _normalise_abbreviation(part: str) -> str:
    """Reduce an abbreviation to the key it is held under."""
    decomposed = unicodedata.normalize('NFD', part.strip().casefold())
    letters = ''.join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r'[^a-z]+', '.', letters).strip('.')


def _repair_brackets(word: str) -> str:
    """Undo the two ways OCR mangles brackets, and leave the rest to be flagged."""
    word = re.sub(r'\(([^()\[\]]*)\]$', r'[\1]', word)
    return re.sub(r'\s+\([^()]*$', '', word)


def _write_reflexive(word: str, pronoun: str) -> str:
    """Move the pronoun in front of the verb, as the sheet writes it."""
    stem = REFLEXIVE_PATTERN.sub('', word).strip()
    return f"s'{stem}" if "'" in pronoun or '’' in pronoun else f'se {stem}'


def _is_headword(word: str) -> bool:
    """Tell an entry apart from a running head or a stray page number."""
    if len(word) < 2 or word.upper() == word and len(word) < 5:
        return False

    return bool(LETTERS_PATTERN.search(word))


def _parse_page_range(pages: str) -> list[int]:
    """Read a range or a comma-separated list as the page numbers it names."""
    page_numbers = []
    for part in pages.split(','):
        part = part.strip()
        if '-' in part.lstrip('-'):
            first, last = (bound.strip() for bound in part.split('-', 1))
            page_numbers.extend(range(int(first), int(last) + 1))
        elif part:
            page_numbers.append(int(part))

    if not page_numbers:
        raise ValueError(f'"{pages}" names no pages. Use a range or a list.')

    return page_numbers


def _get_known_variants(rows: list[list[str]], header: list[str]) -> set[str]:
    """Collect every key the sheet's words already answer to."""
    if FRENCH_COLUMN not in header:
        raise ValueError(f'No "{FRENCH_COLUMN}" column found in {header}.')

    headword_column = header.index(FRENCH_COLUMN)
    known = set()
    for row in rows[1:]:
        if row[headword_column].strip():
            known.update(variants(row[headword_column]))

    return known


def _get_missing_entries(
    entries: list[Entry], known: set[str], limit: int | None
) -> list[Entry]:
    """Pick the entries no row answers to, one per type the book gives them."""
    missing = []
    seen = set()
    for entry in entries:
        if entry.key in seen or entry.variants & known:
            continue

        seen.add(entry.key)
        missing.append(entry)
        if limit and len(missing) == limit:
            break

    return missing


def _print_report(
    report: Report, num_present: int, num_known_rows: int, sheet_name: str
):
    print(
        f'\n"{sheet_name}" has {num_known_rows} rows; '
        f'{num_present} of the glossary\'s words are already there.'
    )
    num_untyped = len([entry for entry in report.missing if not entry.word_type])
    if num_untyped:
        print(
            f'{num_untyped} of the words below have no word type, because the book '
            f'gives none or an abbreviation this script does not know.'
        )

    if report.suspect:
        print(
            f'\n{len(report.suspect)} words left out, because OCR garbled them. '
            f'Add these by hand:'
        )
        for entry in report.suspect:
            print(f'  {entry.word}')

    if not report.missing:
        print('Nothing to add.')
        return

    print(f'\n{len(report.missing)} words to add:')
    for entry in report.missing:
        label = ' '.join(part for part in (entry.word_type, entry.word_subtype) if part)
        pages = ', '.join(str(number) for number in entry.page_numbers)
        print(f'  {entry.word:<34} {label:<9} p. {pages}')
