import argparse
import difflib
import sys

from anki_actions.model_templates import get_model_styling, get_model_templates
from anki_requests import wait_for_ankiconnect
from model_files import (
    FILENAMES_BY_SIDE,
    MEDIA_DIRECTORY,
    MODELS_DIRECTORY,
    VERSIONED_MEDIA_FILENAMES,
    VERSIONED_MODEL_NAMES,
    import_media,
    import_model,
    read_media_versions,
    read_model,
)

EMPTY_CONTENT_BY_SIDE = {'Front': '', 'Back': ''}


def parse_arguments() -> argparse.Namespace:
    """Read the command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            f'Overwrite the card templates, styling and media in Anki with the '
            f'{MODELS_DIRECTORY} directory. Prints the differences and changes '
            f'nothing unless --write is given.'
        )
    )
    parser.add_argument(
        'models',
        nargs='*',
        default=VERSIONED_MODEL_NAMES,
        help=f'Note types to import (default: {", ".join(VERSIONED_MODEL_NAMES)})',
    )
    parser.add_argument(
        '--write',
        action='store_true',
        help='Actually overwrite the note types in Anki',
    )
    return parser.parse_args()


def get_media_versions() -> list[tuple[str, str, str]]:
    """Read each media file as it is in Anki and in the repository."""
    versions = []
    for filename in VERSIONED_MEDIA_FILENAMES:
        anki_content, repository_content = read_media_versions(filename)
        label = f'{MEDIA_DIRECTORY}/{filename}'
        versions.append((label, anki_content, repository_content))

    return versions


def get_model_versions(model_name: str) -> list[tuple[str, str, str]]:
    """Read each file of a note type as it is in Anki and in the repository."""
    styling, templates_by_card_name = read_model(model_name)
    anki_styling = get_model_styling(model_name)
    anki_templates_by_card_name = get_model_templates(model_name)

    versions = [(f'{model_name}/styling.css', anki_styling, styling)]
    for card_name, content_by_side in templates_by_card_name.items():
        anki_content_by_side = anki_templates_by_card_name.get(
            card_name, EMPTY_CONTENT_BY_SIDE
        )
        for side, filename in FILENAMES_BY_SIDE.items():
            label = f'{model_name}/{card_name}/{filename}'
            anki_content = anki_content_by_side[side]
            repository_content = content_by_side[side]
            versions.append((label, anki_content, repository_content))

    return versions


def get_difference(label: str, anki_content: str, repository_content: str) -> str:
    """Describe what importing would change in one file, empty if it already matches."""
    lines = difflib.unified_diff(
        anki_content.splitlines(),
        repository_content.splitlines(),
        fromfile=f'anki:{label}',
        tofile=f'{MODELS_DIRECTORY}:{label}',
        lineterm='',
    )
    return '\n'.join(lines)


def get_differences(model_names: list[str]) -> list[str]:
    """Describe everything importing would change in Anki."""
    versions = get_media_versions()
    for model_name in model_names:
        versions += get_model_versions(model_name)

    differences = []
    for label, anki_content, repository_content in versions:
        difference = get_difference(label, anki_content, repository_content)
        if difference:
            differences.append(difference)

    return differences


if __name__ == '__main__':
    arguments = parse_arguments()
    if not wait_for_ankiconnect():
        raise Exception('AnkiConnect is not running. Exiting.')

    differences = get_differences(arguments.models)
    if not differences:
        print('Anki is already up to date.')
        sys.exit(0)

    print('\n\n'.join(differences))
    if not arguments.write:
        print('\nNothing was changed. Re-run with --write to apply.')
        sys.exit(0)

    print()
    import_media()
    media_filenames = ', '.join(VERSIONED_MEDIA_FILENAMES)
    print(f'Imported {media_filenames} into the media folder')

    for model_name in arguments.models:
        import_model(model_name)
        print(f'Imported {model_name} into Anki')

    print('Sync to AnkiWeb to get the changes onto the phone.')
