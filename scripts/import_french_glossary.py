import argparse
import sys

import settings
from books.french_glossary import (
    DEFAULT_CHAPTER,
    DEFAULT_TAG,
    import_french_glossary,
)


def parse_arguments() -> argparse.Namespace:
    """Read the command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            'Go through the words in the index of Vocabulaire Progressif du '
            'Français and add the ones the French vocabulary sheet does not have '
            'yet. Existing rows are never touched.'
        )
    )
    parser.add_argument('pdf', help='Path to the book as a PDF')
    parser.add_argument(
        '--spreadsheet',
        default='FRA',
        help=(
            'A key from settings.SPREADSHEETS '
            f'({"|".join(sorted(settings.SPREADSHEETS))}) or a spreadsheet title '
            '(default: %(default)s)'
        ),
    )
    parser.add_argument(
        '--sheet',
        default='Collection',
        help='The name of the sheet (tab) to add to (default: %(default)s)',
    )
    parser.add_argument(
        '--from',
        dest='start_from',
        default='',
        help='Only consider words at or after this one, alphabetically',
    )
    parser.add_argument(
        '--through-page',
        type=int,
        help='Only consider words the book prints on this page or an earlier one',
    )
    parser.add_argument(
        '--chapter',
        default=DEFAULT_CHAPTER,
        help='The chapter to file the new words under (default: %(default)s)',
    )
    parser.add_argument(
        '--tag', default=DEFAULT_TAG, help='The tag to give them (default: %(default)s)'
    )
    parser.add_argument(
        '--pages',
        default='',
        help=(
            'The pages the glossary is printed on, as "190-210" or "190,192". '
            'Found automatically when left out.'
        ),
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print the words that would be added without writing them',
    )
    parser.add_argument(
        '--limit', type=int, help='Only add the first N missing words'
    )
    return parser.parse_args()


if __name__ == '__main__':
    arguments = parse_arguments()
    try:
        import_french_glossary(
            arguments.pdf,
            arguments.spreadsheet,
            arguments.sheet,
            start_from=arguments.start_from,
            through_page=arguments.through_page,
            chapter=arguments.chapter,
            tag=arguments.tag,
            pages=arguments.pages,
            dry_run=arguments.dry_run,
            limit=arguments.limit,
        )
    except (ValueError, FileNotFoundError) as error:
        print(error)
        sys.exit(1)
