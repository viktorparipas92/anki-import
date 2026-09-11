import re
from pathlib import Path

from anki_actions.model_templates import (
    get_media_directory_path,
    get_model_styling,
    get_model_templates,
    update_model_styling,
    update_model_templates,
)

MODELS_DIRECTORY = Path('models')
MEDIA_DIRECTORY = MODELS_DIRECTORY / 'media'
SNIPPETS_DIRECTORY = MODELS_DIRECTORY / 'snippets'
STYLING_FILENAME = 'styling.css'
FILENAMES_BY_SIDE = {'Front': 'front.html', 'Back': 'back.html'}

INCLUDE_PATTERN = re.compile(r'<!-- include: ([\w-]+) -->')
EXPANDED_PATTERN = re.compile(
    r'<!-- ([\w-]+) start -->\n(.*?)\n<!-- \1 end -->', re.DOTALL
)

VERSIONED_MODEL_NAMES = ['French vocab']
VERSIONED_MEDIA_FILENAMES = ['_stylesheet.css', '_word_lookups.js']


def export_model(model_name: str):
    """Write the templates and styling of a note type into the models directory."""
    model_directory = MODELS_DIRECTORY / model_name
    model_directory.mkdir(parents=True, exist_ok=True)

    styling = get_model_styling(model_name)
    _write_file(model_directory / STYLING_FILENAME, styling)

    templates_by_card_name = get_model_templates(model_name)
    for card_name, content_by_side in templates_by_card_name.items():
        card_directory = model_directory / card_name
        card_directory.mkdir(exist_ok=True)
        for side, filename in FILENAMES_BY_SIDE.items():
            _write_file(card_directory / filename, content_by_side[side])


def read_model(model_name: str) -> tuple[str, dict[str, dict[str, str]]]:
    """Read the templates and styling of a note type from the models directory."""
    model_directory = MODELS_DIRECTORY / model_name
    styling = _read_file(model_directory / STYLING_FILENAME)

    templates_by_card_name = {}
    for card_directory in sorted(model_directory.iterdir()):
        if not card_directory.is_dir():
            continue

        content_by_side = {}
        for side, filename in FILENAMES_BY_SIDE.items():
            content_by_side[side] = _read_file(card_directory / filename)

        templates_by_card_name[card_directory.name] = content_by_side

    return styling, templates_by_card_name


def import_model(model_name: str):
    """Overwrite a note type in Anki with the files in the models directory."""
    styling, templates_by_card_name = read_model(model_name)
    update_model_styling(model_name, styling)
    update_model_templates(model_name, templates_by_card_name)


def export_media():
    """Copy the versioned media files out of Anki's media folder."""
    anki_directory = Path(get_media_directory_path())
    MEDIA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for filename in VERSIONED_MEDIA_FILENAMES:
        content = _read_media_file(anki_directory / filename)
        (MEDIA_DIRECTORY / filename).write_text(content, encoding='utf-8')


def import_media():
    """Copy the versioned media files into Anki's media folder."""
    anki_directory = Path(get_media_directory_path())
    for filename in VERSIONED_MEDIA_FILENAMES:
        content = (MEDIA_DIRECTORY / filename).read_text(encoding='utf-8')
        (anki_directory / filename).write_text(content, encoding='utf-8')


def read_media_versions(filename: str) -> tuple[str, str]:
    """Read a media file both from Anki's media folder and from the repository."""
    anki_directory = Path(get_media_directory_path())
    anki_content = _read_media_file(anki_directory / filename)
    repository_content = (MEDIA_DIRECTORY / filename).read_text(encoding='utf-8')
    return anki_content, repository_content


def _read_media_file(path: Path) -> str:
    if path.is_symlink():
        raise Exception(
            f'{path} is a symlink. Anki does not sync symlinked media, so the file '
            f'would be deleted from AnkiWeb and from the phone. Replace it with a copy.'
        )

    if not path.exists():
        return ''

    return path.read_text(encoding='utf-8')


def _expand_includes(content: str) -> str:
    """Replace every include with the snippet, as Anki has to store it."""
    def expand(match: re.Match) -> str:
        snippet_name = match.group(1)
        path = SNIPPETS_DIRECTORY / f'{snippet_name}.html'
        snippet = path.read_text(encoding='utf-8').rstrip('\n')
        return (
            f'<!-- {snippet_name} start -->\n'
            f'{snippet}\n'
            f'<!-- {snippet_name} end -->'
        )

    return INCLUDE_PATTERN.sub(expand, content)


def _collapse_includes(content: str) -> str:
    """Replace every expanded snippet with the include, as the repository keeps it."""
    def collapse(match: re.Match) -> str:
        snippet_name = match.group(1)
        return f'<!-- include: {snippet_name} -->'

    return EXPANDED_PATTERN.sub(collapse, content)


def _write_file(path: Path, content: str):
    collapsed = _collapse_includes(content)
    path.write_text(collapsed + '\n', encoding='utf-8')


def _read_file(path: Path) -> str:
    content = path.read_text(encoding='utf-8')
    expanded = _expand_includes(content)
    return expanded.rstrip('\n')
