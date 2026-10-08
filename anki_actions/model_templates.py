import base64

from anki_requests import make_anki_request


def get_model_templates(model_name: str) -> dict[str, dict[str, str]]:
    """Read the card templates of a note type, keyed by card name."""
    response = make_anki_request('modelTemplates', params={'modelName': model_name})
    return response['result']


def get_model_styling(model_name: str) -> str:
    """Read the styling of a note type."""
    response = make_anki_request('modelStyling', params={'modelName': model_name})
    return response['result']['css']


def get_model_names() -> list[str]:
    """Read the names of every note type in the collection."""
    response = make_anki_request('modelNames')
    return response['result']


def get_model_field_names(model_name: str) -> list[str]:
    """Read the field names of a note type, in order."""
    response = make_anki_request('modelFieldNames', params={'modelName': model_name})
    return response['result']


def create_model(
    model_name: str,
    field_names: list[str],
    css: str,
    templates_by_card_name: dict[str, dict[str, str]],
):
    """Add a note type with the given fields, styling and card templates."""
    card_templates = [
        {'Name': card_name, 'Front': content_by_side['Front'], 'Back': content_by_side['Back']}
        for card_name, content_by_side in templates_by_card_name.items()
    ]
    params = {
        'modelName': model_name,
        'inOrderFields': field_names,
        'css': css,
        'cardTemplates': card_templates,
    }
    make_anki_request('createModel', params=params)


def update_model_templates(model_name: str, templates_by_card_name: dict):
    """Overwrite the card templates of a note type."""
    model = {'name': model_name, 'templates': templates_by_card_name}
    make_anki_request('updateModelTemplates', params={'model': model})


def update_model_styling(model_name: str, css: str):
    """Overwrite the styling of a note type."""
    model = {'name': model_name, 'css': css}
    make_anki_request('updateModelStyling', params={'model': model})


def store_media_file(filename: str, content: str):
    """Write a media file through Anki, so it registers in the media database."""
    data = base64.b64encode(content.encode('utf-8')).decode('ascii')
    make_anki_request('storeMediaFile', params={'filename': filename, 'data': data})


def get_media_directory_path() -> str:
    """Read the path of Anki's media folder."""
    response = make_anki_request('getMediaDirPath')
    return response['result']
