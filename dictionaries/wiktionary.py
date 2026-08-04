"""Client for English Wiktionary, reduced to the sheets' translation format."""
import html
import re

import settings
from dictionaries import _http

CACHE_NAMESPACE = 'wiktionary'
TITLES_PER_REQUEST = 50

MAX_SENSES = 3
MAX_SYNONYMS_PER_SENSE = 4
MAX_HINT_PARENTHETICAL_LENGTH = 22

VERB_HEADING = 'Verb'
INFINITIVE_MARKER = 'to '
PART_OF_SPEECH_HEADINGS = frozenset({
    'Noun', 'Proper noun', VERB_HEADING, 'Adjective', 'Adverb', 'Pronoun',
    'Numeral', 'Preposition', 'Conjunction', 'Interjection', 'Determiner',
    'Prefix', 'Suffix', 'Particle', 'Phrase', 'Proverb',
})

MARGINAL_SENSE_LABELS = frozenset({
    'archaic', 'obsolete', 'dated', 'rare', 'poetic', 'historical', 'dialectal',
    'idiomatic', 'nonstandard', 'proscribed', 'literary', 'literally', 'humorous',
})
LABEL_TEMPLATES = frozenset({'lb', 'label', 'lbl', 'tlb'})
LINK_TEMPLATES = frozenset({
    'l', 'll', 'link', 'l-self', 'm', 'm-self', 'mention', 'ux', 'w', 'taxfmt',
})

_LANGUAGE_SECTION_TEMPLATE = r'^==[ \t]*{}[ \t]*==[ \t]*$(.*?)(?=^==[^=]|\Z)'
_HEADING_RE = re.compile(r'^(={3,})[ \t]*(.+?)[ \t]*\1[ \t]*$', re.MULTILINE)
_DEFINITION_RE = re.compile(r'^#[ \t]+(.*\S)[ \t]*$', re.MULTILINE)
_LABEL_TEMPLATE_RE = re.compile(r'\{\{([^{}|]+)\|([^{}]*)\}\}')
_INNERMOST_TEMPLATE_RE = re.compile(r'\{\{([^{}]*)\}\}')
_WIKI_LINK_RE = re.compile(r'\[\[([^\[\]|]*)(?:\|([^\[\]]*))?\]\]')
_EXTERNAL_LINK_RE = re.compile(r'\[(?:https?|//)\S*[ \t]*([^\]]*)\]')
_REF_RE = re.compile(r'<ref[^>]*>.*?</ref>|<ref[^>]*/>', re.DOTALL)
_TAG_RE = re.compile(r'<[^>]+>')
_PARENTHETICAL_RE = re.compile(r'\(([^()]*)\)')
_ENGLISH_ARTICLE_RE = re.compile(r'^(?:an?|the)\s+', re.IGNORECASE)
_INFINITIVE_MARKER_RE = re.compile(r'^to\s+')
_BOLD_OR_ITALIC_RE = re.compile(r"'{2,}")
_WHITESPACE_RE = re.compile(r'\s+')


def fetch_wikitext(lemmas: list[str]) -> dict[str, str]:
    """Return {lemma: wikitext}, using an empty string for the missing pages."""
    wikitext_by_lemma = {}
    uncached_lemmas = []
    for lemma in lemmas:
        cached_wikitext = _http.read_cache(CACHE_NAMESPACE, lemma)
        if cached_wikitext is None:
            uncached_lemmas.append(lemma)
        else:
            wikitext_by_lemma[lemma] = cached_wikitext

    for index in range(0, len(uncached_lemmas), TITLES_PER_REQUEST):
        batch = uncached_lemmas[index:index + TITLES_PER_REQUEST]
        wikitext_by_lemma.update(_fetch_wikitext_batch(batch))

    return wikitext_by_lemma


def get_english_senses(
    wikitext: str, language: str, parts_of_speech: tuple[str, ...] = ()
) -> list[str]:
    """Return a language section's senses as sheet-ready English phrases."""
    language_section = _get_language_section(wikitext, language)
    if not language_section:
        return []

    definitions, heading = _get_definitions(language_section, parts_of_speech)
    senses = []
    for definition in _drop_marginal_senses(definitions):
        sense = _format_sense_as_synonym_list(
            _convert_wikitext_to_plain_text(definition), heading
        )
        if sense and sense not in senses:
            senses.append(sense)

    return senses


def _fetch_wikitext_batch(lemmas: list[str]) -> dict[str, str]:
    response = _http.get_json(
        settings.WIKTIONARY_API_URL,
        params={
            'action': 'query',
            'format': 'json',
            'formatversion': '2',
            'prop': 'revisions',
            'rvprop': 'content',
            'rvslots': 'main',
            'titles': '|'.join(lemmas),
        },
    )
    if response is None:
        return {}

    requested_lemma_by_title = {lemma: lemma for lemma in lemmas}
    for normalisation in response.get('query', {}).get('normalized', []):
        requested_lemma_by_title[normalisation['to']] = normalisation['from']

    wikitext_by_lemma = {}
    for page in response.get('query', {}).get('pages', []):
        title = page.get('title')
        lemma = requested_lemma_by_title.get(title, title)
        revisions = page.get('revisions') or [{}]
        wikitext = revisions[0].get('slots', {}).get('main', {}).get('content', '')
        wikitext_by_lemma[lemma] = wikitext
        _http.write_cache(CACHE_NAMESPACE, lemma, wikitext)

    return wikitext_by_lemma


def _get_language_section(wikitext: str, language: str) -> str:
    pattern = _LANGUAGE_SECTION_TEMPLATE.format(re.escape(language))
    section = re.search(pattern, wikitext, re.MULTILINE | re.DOTALL)
    return section.group(1) if section else ''


def _get_definitions(
    language_section: str, parts_of_speech: tuple[str, ...]
) -> tuple[list[str], str | None]:
    blocks = _split_into_part_of_speech_blocks(language_section)
    if not blocks:
        return [], None

    for heading, body in blocks:
        if heading in parts_of_speech:
            return _DEFINITION_RE.findall(body), heading

    main_heading, main_body = blocks[0]
    return _DEFINITION_RE.findall(main_body), main_heading


def _split_into_part_of_speech_blocks(
    language_section: str,
) -> list[tuple[str, str]]:
    headings = list(_HEADING_RE.finditer(language_section))
    blocks = []
    for index, heading in enumerate(headings):
        name = heading.group(2)
        if name not in PART_OF_SPEECH_HEADINGS:
            continue

        end = (
            headings[index + 1].start()
            if index + 1 < len(headings)
            else len(language_section)
        )
        blocks.append((name, language_section[heading.end():end]))

    return blocks


def _drop_marginal_senses(definitions: list[str]) -> list[str]:
    current_senses = [
        definition
        for definition in definitions
        if not _get_sense_labels(definition) & MARGINAL_SENSE_LABELS
    ]
    return current_senses or definitions


def _get_sense_labels(definition: str) -> frozenset[str]:
    labels = set()
    for template in _LABEL_TEMPLATE_RE.finditer(definition):
        if template.group(1).strip() not in LABEL_TEMPLATES:
            continue

        arguments_after_language_code = template.group(2).split('|')[1:]
        labels.update(
            argument.strip().lower() for argument in arguments_after_language_code
        )

    return frozenset(labels)


def _convert_wikitext_to_plain_text(definition: str) -> str:
    text = _REF_RE.sub('', definition)
    text = _expand_all_templates(text)
    text = _WIKI_LINK_RE.sub(lambda match: match.group(2) or match.group(1), text)
    text = _EXTERNAL_LINK_RE.sub(lambda match: match.group(1), text)
    text = _BOLD_OR_ITALIC_RE.sub('', text)
    text = _TAG_RE.sub('', html.unescape(text))
    return _WHITESPACE_RE.sub(' ', text).strip()


def _expand_all_templates(text: str) -> str:
    while True:
        expanded = _INNERMOST_TEMPLATE_RE.sub(
            lambda match: _expand_template_to_display_text(match.group(1)), text
        )
        if expanded == text:
            return text
        text = expanded


def _expand_template_to_display_text(template_body: str) -> str:
    arguments = template_body.split('|')
    name = arguments[0].strip()
    if name not in LINK_TEMPLATES:
        return ''

    positional_arguments = [
        argument.strip() for argument in arguments[1:] if '=' not in argument
    ]
    if name == 'w':
        return next(
            (argument for argument in reversed(positional_arguments) if argument), ''
        )

    arguments_after_language_code = positional_arguments[1:] or positional_arguments
    for argument in reversed(arguments_after_language_code):
        if argument:
            return argument

    return ''


def _format_sense_as_synonym_list(sense: str, heading: str | None) -> str:
    sense = _drop_definition_length_parentheticals(sense).strip(' ,;:.')
    if not sense:
        return ''

    synonyms = [
        _ENGLISH_ARTICLE_RE.sub('', synonym.strip())
        for synonym in _split_synonyms_outside_parentheses(sense)
    ]
    synonyms = [synonym for synonym in synonyms if synonym]
    if not synonyms:
        return ''

    synonyms[0] = _uncapitalise_unless_proper_noun(synonyms[0])
    if heading == VERB_HEADING:
        synonyms = [
            _INFINITIVE_MARKER_RE.sub('', synonym) for synonym in synonyms
        ]
        synonyms[0] = f'{INFINITIVE_MARKER}{synonyms[0]}'

    return ', '.join(synonyms[:MAX_SYNONYMS_PER_SENSE])


def _uncapitalise_unless_proper_noun(sense: str) -> str:
    first_word = sense.split(' ', 1)[0]
    if first_word.isupper() or not first_word[1:].islower():
        return sense

    return sense[0].lower() + sense[1:]


def _drop_definition_length_parentheticals(sense: str) -> str:
    while True:
        shortened = _PARENTHETICAL_RE.sub(
            lambda match: match.group(0)
            if len(match.group(0)) <= MAX_HINT_PARENTHETICAL_LENGTH
            else '',
            sense,
        )
        if shortened == sense:
            return _WHITESPACE_RE.sub(' ', sense).strip()
        sense = shortened


def _split_synonyms_outside_parentheses(sense: str) -> list[str]:
    synonyms = []
    parenthesis_depth = 0
    current_synonym = ''
    for character in sense:
        if character == '(':
            parenthesis_depth += 1
        elif character == ')':
            parenthesis_depth = max(0, parenthesis_depth - 1)

        if character == ',' and parenthesis_depth == 0:
            synonyms.append(current_synonym)
            current_synonym = ''
        else:
            current_synonym += character

    synonyms.append(current_synonym)
    return synonyms
