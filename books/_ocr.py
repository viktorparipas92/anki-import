"""Read the text off the pages of a scanned PDF, using the OCR built into macOS.

The engine is the same one Preview uses for Live Text, reached through
Vision.framework, so it needs no system packages — only the pyobjc wheels in
`requirements-ocr.txt`. It is macOS only, so the frameworks are imported inside
the functions that need them.
"""
import hashlib
import json
import os

import settings

CACHE_NAMESPACE = 'ocr'
RENDER_SCALE = 2.0
RECOGNITION_LANGUAGES = ['fr-FR', 'en-US']


def read_pages(pdf_path: str, page_numbers: list[int] | None = None) -> list[str]:
    """OCR the given pages of a PDF, or all of them, and return their text."""
    import Quartz

    document = _open_document(pdf_path)
    num_pages = Quartz.CGPDFDocumentGetNumberOfPages(document)
    if page_numbers is None:
        page_numbers = list(range(1, num_pages + 1))

    fingerprint = _get_fingerprint(pdf_path)
    texts = []
    for page_number in page_numbers:
        if not 1 <= page_number <= num_pages:
            raise ValueError(
                f'Page {page_number} is outside the {num_pages} pages of the PDF.'
            )

        texts.append(_read_page(document, page_number, fingerprint))

    return texts


def get_num_pages(pdf_path: str) -> int:
    """Return how many pages the PDF has."""
    import Quartz

    return Quartz.CGPDFDocumentGetNumberOfPages(_open_document(pdf_path))


def _open_document(pdf_path: str):
    import Quartz

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f'No such file: {pdf_path}')

    url = Quartz.CFURLCreateFromFileSystemRepresentation(
        None, pdf_path.encode('utf-8'), len(pdf_path.encode('utf-8')), False
    )
    document = Quartz.CGPDFDocumentCreateWithURL(url)
    if document is None:
        raise ValueError(f'"{pdf_path}" could not be opened as a PDF.')

    return document


def _read_page(document, page_number: int, fingerprint: str) -> str:
    cache_key = f'{fingerprint}:{page_number}:{RENDER_SCALE}'
    cached = _read_cache(cache_key)
    if cached is not None:
        return cached

    text = _recognise_text(_render_page(document, page_number))
    _write_cache(cache_key, text)
    return text


def _render_page(document, page_number: int):
    import Quartz

    page = Quartz.CGPDFDocumentGetPage(document, page_number)
    box = Quartz.CGPDFPageGetBoxRect(page, Quartz.kCGPDFCropBox)
    width = int(box.size.width * RENDER_SCALE)
    height = int(box.size.height * RENDER_SCALE)
    colour_space = Quartz.CGColorSpaceCreateDeviceRGB()
    context = Quartz.CGBitmapContextCreate(
        None, width, height, 8, 0, colour_space,
        Quartz.kCGImageAlphaNoneSkipLast,
    )
    Quartz.CGContextSetRGBFillColor(context, 1, 1, 1, 1)
    Quartz.CGContextFillRect(context, Quartz.CGRectMake(0, 0, width, height))
    Quartz.CGContextScaleCTM(context, RENDER_SCALE, RENDER_SCALE)
    Quartz.CGContextTranslateCTM(context, -box.origin.x, -box.origin.y)
    Quartz.CGContextDrawPDFPage(context, page)
    return Quartz.CGBitmapContextCreateImage(context)


def _recognise_text(image) -> str:
    import Quartz
    import Vision

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_(RECOGNITION_LANGUAGES)
    request.setUsesLanguageCorrection_(False)

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, None)
    succeeded, error = handler.performRequests_error_([request], None)
    if not succeeded:
        raise ValueError(f'OCR failed: {error}')

    observations = request.results() or []
    return '\n'.join(
        observation.topCandidates_(1)[0].string()
        for observation in observations
        if observation.topCandidates_(1)
    )


def _get_fingerprint(pdf_path: str) -> str:
    stat = os.stat(pdf_path)
    return hashlib.sha1(
        f'{os.path.abspath(pdf_path)}:{stat.st_size}:{stat.st_mtime_ns}'.encode('utf-8')
    ).hexdigest()


def _build_cache_path(cache_key: str) -> str:
    digest = hashlib.sha1(cache_key.encode('utf-8')).hexdigest()
    return os.path.join(settings.DICTIONARY_CACHE_DIR, CACHE_NAMESPACE, f'{digest}.json')


def _read_cache(cache_key: str) -> str | None:
    path = _build_cache_path(cache_key)
    if not os.path.exists(path):
        return None

    with open(path, encoding='utf-8') as cache_file:
        return json.load(cache_file)['text']


def _write_cache(cache_key: str, text: str):
    path = _build_cache_path(cache_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode='w', encoding='utf-8') as cache_file:
        json.dump({'key': cache_key, 'text': text}, cache_file, ensure_ascii=False)
