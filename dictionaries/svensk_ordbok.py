"""Client for Svensk ordbok (SO), read from the JSON API behind svenska.se."""
import html
import re
from dataclasses import dataclass

import settings
from dictionaries import _http

CACHE_NAMESPACE = 'svensk_ordbok'
MAX_ARTICLES_PER_LEMMA = 10

CATEGORY_ABBREVIATIONS = {
    'vardagligt': 'vard.',
    'ålderdomligt': 'åld.',
    'bibliskt': 'bibl.',
    'nedsättande': 'derog.',
    'formellt': 'formal',
    'högtidligt': 'högtidligt',
    'historiskt': 'historiskt',
    'skämtsamt': 'skämts.',
    'poetiskt': 'poet.',
    'militärt': 'mil.',
    'juridik': 'jur.',
}

PLACEHOLDER_ABBREVIATIONS = {
    'någon': 'ngn',
    'någons': 'ngns',
    'något': 'ngt',
    'någots': 'ngts',
    'någonting': 'ngt',
    'någonstans': 'ngnstans',
    'några': 'ngra',
    'någras': 'ngras',
}
SUBJECT_PLACEHOLDERS = frozenset(
    {'ngn', 'ngns', 'ngt', 'ngts', 'ngra', 'ngras', 'det', 'man'}
)

_HTML_TAG_RE = re.compile(r'<[^>]+>')
_WHITESPACE_RE = re.compile(r'\s+')
_WORD_RE = re.compile(r'\w+', re.UNICODE)


@dataclass
class Sense:
    """One main meaning (huvudbetydelse) of an SO article."""

    definition: str | None = None
    category: str | None = None
    usage: str | None = None


@dataclass
class Entry:
    """One SO article, reduced to the fields the vocabulary sheets use."""

    lemma: str
    word_class: str
    senses: list[Sense]
    article: str | None = None
    pronunciation: str | None = None
    etymology: str | None = None


def look_up(lemma: str) -> list[Entry]:
    """Return every SO article whose headword is exactly `lemma`."""
    response = _search_articles(lemma)
    if response is None:
        return []

    entries = []
    for hit in response.get('hits', {}).get('hits', []):
        article = hit.get('_source', {})
        headword = _strip_inline_html(article.get('ortografi', ''))
        if headword.lower() != lemma.lower():
            continue

        entries.append(_build_entry_from_article(article, lemma))

    return entries


def _search_articles(lemma: str) -> dict | None:
    cached_response = _http.read_cache(CACHE_NAMESPACE, lemma)
    if cached_response is not None:
        return cached_response

    response = _http.get_json(
        f'{settings.SVENSK_ORDBOK_API_URL}/search/so',
        params={
            'q': lemma,
            'exact_match': 'true',
            'size': str(MAX_ARTICLES_PER_LEMMA),
        },
    )
    if response is None:
        return None

    articles_only = {
        'hits': {
            'hits': [
                {'_source': hit.get('_source', {})}
                for hit in response.get('hits', {}).get('hits', [])
            ]
        }
    }
    _http.write_cache(CACHE_NAMESPACE, lemma, articles_only)
    return articles_only


def _build_entry_from_article(article: dict, lemma: str) -> Entry:
    word_class = _strip_inline_html(article.get('ordklass', ''))
    meanings = article.get('huvudbetydelser') or [{}]
    etymology = (meanings[0].get('historiskaUppgifter') or {}).get('etymologi', '')
    return Entry(
        lemma=lemma,
        word_class=word_class,
        senses=[_build_sense(meaning, word_class, lemma) for meaning in meanings],
        article=_get_noun_article(article, word_class),
        pronunciation=_get_stress_notation(article),
        etymology=_strip_inline_html(etymology) or None,
    )


def _build_sense(meaning: dict, word_class: str, lemma: str) -> Sense:
    return Sense(
        definition=_strip_inline_html(meaning.get('definition', '')) or None,
        category=_get_abbreviated_usage_label(meaning),
        usage=_get_verb_complement_pattern(meaning, word_class, lemma),
    )


def _get_noun_article(article: dict, word_class: str) -> str | None:
    if word_class != 'substantiv':
        return None

    for inflection_table in article.get('böjningstabell') or []:
        if _strip_inline_html(inflection_table.get('rubrik', '')) != 'Singular':
            continue

        for row in inflection_table.get('rader') or []:
            for variant in row.get('böjningsvarianter') or []:
                noun_article = _strip_inline_html(variant.get('ledtext', ''))
                if noun_article in ('en', 'ett'):
                    return noun_article

    return _get_noun_article_from_definite_form(article.get('böjning', ''))


def _get_noun_article_from_definite_form(inflection_summary: str) -> str | None:
    forms = _WORD_RE.findall(_strip_inline_html(inflection_summary))
    if not forms:
        return None

    definite_singular = forms[0]
    if definite_singular.endswith('n'):
        return 'en'
    if definite_singular.endswith('t'):
        return 'ett'
    return None


def _get_stress_notation(article: dict) -> str | None:
    for pronunciation in article.get('uttal') or []:
        for key in ('fonetikparentes', 'lemmaMedTryckangivelse'):
            notation = _strip_inline_html(pronunciation.get(key, ''))
            if notation:
                return notation

    return None


def _get_abbreviated_usage_label(meaning: dict) -> str | None:
    label = _strip_inline_html(meaning.get('bruklighetskommentar', ''))
    if not label:
        return None

    for full_label, abbreviation in CATEGORY_ABBREVIATIONS.items():
        if full_label in label.lower():
            return abbreviation

    return label


def _get_verb_complement_pattern(
    meaning: dict, word_class: str, lemma: str
) -> str | None:
    if word_class != 'verb':
        return None

    for construction in meaning.get('valenser') or []:
        pattern = _strip_inline_html(construction.get('valens', ''))
        complement = _strip_subject_and_verb(_abbreviate_placeholders(pattern), lemma)
        if complement:
            return complement

    return None


def _abbreviate_placeholders(pattern: str) -> str:
    return ' '.join(
        _WORD_RE.sub(
            lambda match: PLACEHOLDER_ABBREVIATIONS.get(
                match.group().lower(), match.group()
            ),
            word,
        )
        for word in pattern.split()
    )


def _strip_subject_and_verb(pattern: str, lemma: str) -> str:
    words = pattern.split()
    while words and _is_subject_placeholder(words[0]):
        words = words[1:]

    return ' '.join(words[len(lemma.split()):]).strip()


def _is_subject_placeholder(word: str) -> bool:
    alternatives = word.strip('()[]').lower().split('/')
    return any(alternative in SUBJECT_PLACEHOLDERS for alternative in alternatives)


def _strip_inline_html(markup: str) -> str:
    return _WHITESPACE_RE.sub(
        ' ', html.unescape(_HTML_TAG_RE.sub('', markup))
    ).strip()
