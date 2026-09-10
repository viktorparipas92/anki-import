import argparse

from anki_requests import wait_for_ankiconnect
from model_files import (
    MEDIA_DIRECTORY,
    MODELS_DIRECTORY,
    VERSIONED_MEDIA_FILENAMES,
    VERSIONED_MODEL_NAMES,
    export_media,
    export_model,
)


def parse_arguments() -> argparse.Namespace:
    """Read the command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            f'Write the card templates, styling and media from Anki into the '
            f'{MODELS_DIRECTORY} directory, so they can be committed.'
        )
    )
    parser.add_argument(
        'models',
        nargs='*',
        default=VERSIONED_MODEL_NAMES,
        help=f'Note types to export (default: {", ".join(VERSIONED_MODEL_NAMES)})',
    )
    return parser.parse_args()


if __name__ == '__main__':
    arguments = parse_arguments()
    if not wait_for_ankiconnect():
        raise Exception('AnkiConnect is not running. Exiting.')

    for model_name in arguments.models:
        export_model(model_name)
        print(f'Exported {model_name} to {MODELS_DIRECTORY / model_name}')

    export_media()
    media_filenames = ', '.join(VERSIONED_MEDIA_FILENAMES)
    print(f'Exported {media_filenames} to {MEDIA_DIRECTORY}')
