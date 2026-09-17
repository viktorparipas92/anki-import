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
        '--word-pages',
        default='',
        help=(
            'Only add words the index lists under these pages of the book, as '
            '"12-15" or "12,14". This is the chapter you are importing'
        ),
    )
    parser.add_argument(
        '--from-word',
        '--from',
        dest='start_from',
        default='',
        help=(
            'Only add words at or after this letter or word, alphabetically, '
            'as "p" or "parapluie"'
        ),
    )
    parser.add_argument(
        '--through-page',
        type=int,
        help='Older form of --word-pages, meaning every page up to this one',
    )
    parser.add_argument(
        '--chapter',
        type=int,
        default=DEFAULT_CHAPTER,
        help='The chapter to file the new words under (default: %(default)s)',
    )
    parser.add_argument(
        '--tag', default=DEFAULT_TAG, help='The tag to give them (default: %(default)s)'
    )
    parser.add_argument(
        '--index-pages',
        '--pages',
        dest='index_pages',
        default='',
        help=(
            'Where the index itself is printed in the PDF, as "187-208" or '
            '"187,189". Not the pages of the words; found automatically when '
            'left out'
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
            word_pages=arguments.word_pages,
            through_page=arguments.through_page,
            chapter=arguments.chapter,
            tag=arguments.tag,
            index_pages=arguments.index_pages,
            dry_run=arguments.dry_run,
            limit=arguments.limit,
        )
    except (ValueError, FileNotFoundError) as error:
        print(error)
        sys.exit(1)
