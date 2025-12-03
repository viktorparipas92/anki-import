import argparse
import csv
import os

import polib


def po_to_csv(input_path, output_path):
    po = polib.pofile(input_path) if input_path.endswith('.po') else polib.mofile(input_path)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['msgid', 'msgstr'])

        for entry in po:
            if entry.msgid:  # Skip metadata entries
                writer.writerow([entry.msgid, entry.msgstr])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('target')
    args = parser.parse_args()

    input_path = os.path.expanduser(args.source)
    po_to_csv(input_path=input_path, output_path=args.target)
