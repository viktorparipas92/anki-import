import sys

from anki_requests import make_anki_request


def get_model_id(model_name):
    response = make_anki_request('modelNamesAndIds')
    return response['result'].get(model_name)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python get_model_id.py <model_name>')
        sys.exit(1)

    model_name = sys.argv[1]
    model_id = get_model_id(model_name)
    print(model_id)
