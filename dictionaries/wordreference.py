"""Look words up in WordReference, keeping only translations it confirms both ways.

A page gives the word's primary translations, and separately lists the entries the
word is also found in, English among them. Only a primary translation the English
list names as well is kept, which drops the loose ones.
"""
import re
import urllib.parse
from dataclasses import dataclass

from bs4 import BeautifulSoup

import settings
from dictionaries import _http

CACHE_NAMESPACE = 'wordreference'
TARGET_LANGUAGE_CODE = 'en'
LANGUAGE_CODES = {'FRA': 'fr', 'ESP': 'es', 'ITA': 'it'}

BOT_CHALLENGE_COOKIE = 'nginx_wr_human=1'
PRIMARY_HEADING_STEM_IN_EVERY_LANGUAGE = 'princip'
MAIN_TRANSLATION_ARROW = '⇒'

FEMININE_NOUN = 'nf'
MASCULINE_NOUN = 'nm'
NOUN_OF_EITHER_GENDER = 'n'
ADJECTIVE = 'adj'
VERB = 'v'
REFLEXIVE_VERB = 'v pron'
ANY_PART_OF_SPEECH = ''
NOUN_CATEGORIES = frozenset({FEMININE_NOUN, MASCULINE_NOUN, NOUN_OF_EITHER_GENDER})
VERB_CATEGORIES = frozenset({VERB, REFLEXIVE_VERB})
VERB_PARTICLE = 'to'
TRANSITIVE = 'tr'
INTRANSITIVE = 'i'
TRANSITIVE_AND_INTRANSITIVE = 'i/tr'
REFLEXIVE_SUBTYPE = 'refl'
MIN_LENGTH_TO_MATCH_INSIDE = 3

FEMININE_SUFFIX_PATTERN = re.compile(r',\s*-\S+')
OPTIONAL_PART_PATTERN = re.compile(r'[\[(]([^\])]*)[\])]')
REFLEXIVE_PREFIX_PATTERN = re.compile(r"^(?:se\s+|s')", re.IGNORECASE)
PRONUNCIATION_SELECTOR = '.pronWR'
PRONUNCIATION_PATTERN = re.compile(r'\[([^\[\]]+)\]')
VARIANT_SPELLING_PATTERN = re.compile(r',.*$')


@dataclass(frozen=True)
class Translation:
    """What WordReference has to say about one row of the sheet."""

    english: str = ''
    word_subtype: str = ''
    pronunciation: str = ''


@dataclass(frozen=True)
class Box:
    """One box of the primary translations, holding one sense of the word."""

    sense: str
    words: tuple[str, ...]
    part_of_speech: str = ''

    @property
    def category(self) -> str:
        """Reduce the printed part of speech to one the sheet also distinguishes."""
        return _get_category(self.part_of_speech)


@dataclass(frozen=True)
class Entry:
    """A word's page: its primary translations and the English words linking back."""

    headword: str
    boxes: tuple[Box, ...]
    reverse_words: frozenset[str]
    pronunciation: str = ''

    def get_result(self, category: str = ANY_PART_OF_SPEECH) -> Translation:
        """The confirmed translations, by comma within a box, semicolon between."""
        confirmed = []
        taken = set()
        used_boxes = []
        for box in self.boxes:
            if not _matches_category(box.category, category):
                continue

            words = []
            for word in box.words:
                folded = _fold(word)
                if folded in taken or not _is_confirmed(word, self.reverse_words):
                    continue

                taken.add(folded)
                words.append(_spell(word, box.category) if not words else word)

            if words:
                confirmed.append(', '.join(words))
                used_boxes.append(box)

        return Translation(
            english='; '.join(confirmed),
            word_subtype=_get_verb_subtype(category, used_boxes),
            pronunciation=self.pronunciation,
        )


def look_up(word: str, language_key: str) -> Entry | None:
    """Find a word's page, falling back to plainer spellings of it."""
    for form in search_forms(word):
        entry = _look_up_form(form, language_key)
        if entry is not None and entry.boxes:
            return entry

    return None


def translate(
    word: str, language_key: str, word_type: str = '', word_subtype: str = ''
) -> Translation:
    """Return what WordReference confirms for a row, empty when it has nothing."""
    entry = look_up(word, language_key)
    if entry is None:
        return Translation()

    return entry.get_result(get_sheet_category(word, word_type, word_subtype))


def get_sheet_category(word: str, word_type: str, word_subtype: str) -> str:
    """Reduce a sheet row to a part-of-speech category."""
    word_type = word_type.strip().casefold()
    word_subtype = word_subtype.strip().casefold()
    if is_reflexive(word) or word_subtype.startswith('refl'):
        return REFLEXIVE_VERB

    if word_type == 'n':
        if word_subtype.startswith('mf'):
            return NOUN_OF_EITHER_GENDER
        if word_subtype.startswith('f'):
            return FEMININE_NOUN
        if word_subtype.startswith('m'):
            return MASCULINE_NOUN

        return NOUN_OF_EITHER_GENDER

    if word_type == 'adj':
        return ADJECTIVE
    if word_type == 'v':
        return VERB

    return ANY_PART_OF_SPEECH


def is_reflexive(word: str) -> bool:
    """Say whether the sheet spells this word as a reflexive verb."""
    return REFLEXIVE_PREFIX_PATTERN.match(word.strip()) is not None


def search_forms(word: str) -> list[str]:
    """Return the spellings to try, from the sheet's own down to the root form."""
    word = _tidy(FEMININE_SUFFIX_PATTERN.sub('', word))
    candidates = [
        OPTIONAL_PART_PATTERN.sub(r'\1', word),
        OPTIONAL_PART_PATTERN.sub(' ', word),
        REFLEXIVE_PREFIX_PATTERN.sub('', OPTIONAL_PART_PATTERN.sub(' ', word)),
    ]
    forms = []
    for candidate in candidates:
        form = _tidy(candidate)
        if form and form not in forms:
            forms.append(form)

    return forms


def get_language_path(language_key: str) -> str:
    """Return the URL segment for a language's pair with English."""
    if language_key not in LANGUAGE_CODES:
        raise ValueError(
            f'No WordReference language pair for "{language_key}". '
            f'Add it to LANGUAGE_CODES, one of {sorted(LANGUAGE_CODES)}.'
        )

    return f'{LANGUAGE_CODES[language_key]}{TARGET_LANGUAGE_CODE}'


def _look_up_form(form: str, language_key: str) -> Entry | None:
    language_path = get_language_path(language_key)
    html = _fetch(form, language_path)
    if html is None:
        return None

    soup = BeautifulSoup(html, 'html.parser')
    return Entry(
        headword=form,
        boxes=_parse_boxes(soup),
        reverse_words=_parse_reverse_words(soup, language_path),
        pronunciation=_parse_pronunciation(soup),
    )


def _parse_pronunciation(soup: BeautifulSoup) -> str:
    """Read the word's IPA as the sheet writes it: bare, and the first form only."""
    element = soup.select_one(PRONUNCIATION_SELECTOR)
    if element is None:
        return ''

    text = element.get_text(' ', strip=True)
    spellings = PRONUNCIATION_PATTERN.findall(text)
    if not spellings:
        return ''

    base_form = VARIANT_SPELLING_PATTERN.sub('', spellings[0])
    return _tidy(base_form)


def _fetch(form: str, language_path: str) -> str | None:
    cache_key = f'{language_path}:{form}'
    cached = _http.read_cache(CACHE_NAMESPACE, cache_key)
    if cached is not None:
        return cached or None

    url = f'{settings.WORDREFERENCE_URL}/{language_path}/{urllib.parse.quote(form)}'
    html = _http.get_text(url, headers={'Cookie': BOT_CHALLENGE_COOKIE})
    _http.write_cache(CACHE_NAMESPACE, cache_key, html or '')
    return html


def _parse_boxes(soup: BeautifulSoup) -> tuple[Box, ...]:
    table = _find_primary_table(soup)
    if table is None:
        return ()

    boxes = []
    for row in table.find_all('tr'):
        cells = row.find_all('td', recursive=False)
        if not cells:
            continue

        source = _get_cell(cells, 'FrWrd')
        if source is not None and _clean_cell(source):
            boxes.append(
                Box(
                    sense=_get_sense(cells),
                    words=(),
                    part_of_speech=_get_part_of_speech(source),
                )
            )
        if not boxes:
            continue

        target = _get_cell(cells, 'ToWrd')
        if target is None:
            continue

        words = _split_words(_clean_cell(target))
        if words:
            box = boxes[-1]
            boxes[-1] = Box(box.sense, box.words + words, box.part_of_speech)

    return tuple(box for box in boxes if box.words)


def _find_primary_table(soup: BeautifulSoup):
    for table in soup.find_all('table', class_='WRD'):
        heading = table.find(class_='wrtopsection')
        if heading is None:
            continue
        heading_text = heading.get_text(' ', strip=True).casefold()
        if PRIMARY_HEADING_STEM_IN_EVERY_LANGUAGE in heading_text:
            return table

    return None


def _parse_reverse_words(soup: BeautifulSoup, language_path: str) -> frozenset[str]:
    reverse_path = _get_reverse_path(language_path)
    words = set()
    for word_list in soup.find_all('div', class_='FTlist'):
        for link in word_list.find_all('a'):
            if link.get('href', '').startswith(reverse_path):
                words.add(_fold(link.get_text(' ', strip=True)))

    return frozenset(words)


def _get_reverse_path(language_path: str) -> str:
    """Return the path of the opposite pair, which the English entries link to."""
    source_code, target_code = language_path[:2], language_path[2:]
    return f'/{target_code}{source_code}/'


def _get_part_of_speech(cell) -> str:
    marker = cell.find('em')
    return _tidy(marker.get_text(' ', strip=True)) if marker is not None else ''


def _get_category(part_of_speech: str) -> str:
    marker = re.sub(r'[^a-z ]', ' ', part_of_speech.casefold())
    words = marker.split()
    if not words:
        return ANY_PART_OF_SPEECH

    head = words[0]
    if head.startswith('n'):
        has_feminine = 'nf' in marker or head == 'n' and 'f' in words
        has_masculine = 'nm' in marker or head == 'n' and 'm' in words
        if has_feminine and has_masculine:
            return NOUN_OF_EITHER_GENDER
        if has_feminine:
            return FEMININE_NOUN
        if has_masculine:
            return MASCULINE_NOUN

        return NOUN_OF_EITHER_GENDER

    if head.startswith(ADJECTIVE):
        return ADJECTIVE
    if head.startswith(VERB):
        return REFLEXIVE_VERB if 'pron' in words else VERB

    return ANY_PART_OF_SPEECH


def _get_transitivity(part_of_speech: str) -> str:
    words = re.sub(r'[^a-z ]', ' ', part_of_speech.casefold()).split()
    if any(word.startswith('vtr') for word in words):
        return TRANSITIVE
    if any(word == 'vi' for word in words):
        return INTRANSITIVE

    return ''


def _get_verb_subtype(category: str, boxes: list[Box]) -> str:
    if category == REFLEXIVE_VERB:
        return REFLEXIVE_SUBTYPE

    categories = {box.category for box in boxes}
    is_verb = bool(categories) and categories <= VERB_CATEGORIES
    if category != VERB and not (category == ANY_PART_OF_SPEECH and is_verb):
        return ''

    transitivities = {_get_transitivity(box.part_of_speech) for box in boxes}
    if {TRANSITIVE, INTRANSITIVE} <= transitivities:
        return TRANSITIVE_AND_INTRANSITIVE
    if TRANSITIVE in transitivities:
        return TRANSITIVE
    if INTRANSITIVE in transitivities:
        return INTRANSITIVE

    return ''


def _matches_category(box_category: str, wanted: str) -> bool:
    if wanted == ANY_PART_OF_SPEECH:
        return box_category != REFLEXIVE_VERB
    if box_category == wanted:
        return True

    return (
        wanted in NOUN_CATEGORIES
        and box_category in NOUN_CATEGORIES
        and NOUN_OF_EITHER_GENDER in (wanted, box_category)
    )


def _is_confirmed(word: str, reverse_words: frozenset[str]) -> bool:
    """Say whether the English entries name this translation, or part of it."""
    folded = _fold(word)
    if folded in reverse_words:
        return True

    return any(
        len(reverse) >= MIN_LENGTH_TO_MATCH_INSIDE and _holds_words(folded, reverse)
        for reverse in reverse_words
    )


def _holds_words(translation: str, reverse: str) -> bool:
    return re.search(rf'(?<!\w){re.escape(reverse)}(?!\w)', translation) is not None


def _spell(word: str, category: str) -> str:
    if category not in VERB_CATEGORIES:
        return word

    return word if word.split()[:1] == [VERB_PARTICLE] else f'{VERB_PARTICLE} {word}'


def _get_cell(cells: list, class_name: str):
    for cell in cells:
        if class_name in (cell.get('class') or []):
            return cell

    return None


def _get_sense(cells: list) -> str:
    for cell in cells:
        if not cell.get('class'):
            sense = cell.get_text(' ', strip=True)
            if sense:
                return sense.strip('()')

    return ''


def _clean_cell(cell) -> str:
    copied = BeautifulSoup(str(cell), 'html.parser')
    for tag in copied.find_all(['em', 'span']):
        tag.decompose()

    text = copied.get_text(' ', strip=True)
    text = re.sub(r'\([^()]*\)|\[[^\[\]]*\]', ' ', text)
    return _tidy(text)


def _split_words(text: str) -> tuple[str, ...]:
    return tuple(word for part in text.split(',') if (word := _tidy(part)))


def _tidy(text: str) -> str:
    text = text.replace('\xa0', ' ').replace(MAIN_TRANSLATION_ARROW, ' ')
    return re.sub(r'\s+', ' ', text).strip(' ,;:+/')


def _fold(text: str) -> str:
    return _tidy(text).casefold()
