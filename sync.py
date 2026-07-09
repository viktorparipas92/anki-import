from anki_requests import make_anki_request, wait_for_ankiconnect


def sync():
    """Trigger a sync of the local collection to AnkiWeb."""
    make_anki_request('sync')


if __name__ == '__main__':
    if not wait_for_ankiconnect():
        raise Exception('AnkiConnect is not running. Exiting.')

    print('Syncing to AnkiWeb...')
    sync()
    print('Sync completed successfully.')
