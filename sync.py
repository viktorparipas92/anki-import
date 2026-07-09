from anki_requests import make_anki_request


def sync():
    """Trigger a sync of the local collection to AnkiWeb."""
    make_anki_request('sync')


if __name__ == '__main__':
    print('Syncing to AnkiWeb...')
    sync()
    print('Sync completed successfully.')
