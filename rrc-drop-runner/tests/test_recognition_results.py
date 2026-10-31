"""Regression checks for result archives and failed format probes."""
import csv
from contextlib import closing
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import recognition


class RecognitionResultsTest(unittest.TestCase):
    def test_failed_csv_probe_is_only_a_nonmatch(self):
        slug = next(s for s, spec in recognition.LAYOUTS.items() if spec['kind'] == 'delim')
        raw = b'one,two\rthree,four\n'
        with self.assertRaises(csv.Error):
            list(csv.reader(recognition._lines(raw), delimiter=','))
        self.assertFalse(recognition._layout_matches(slug, raw, len(raw), True))

    def test_results_archive_members_get_clear_message(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = root / 'data.sqlite'
            with closing(sqlite3.connect(database)) as db:
                db.execute('create table example (value text)')
            manifest = root / 'conversion.json'
            manifest.write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Data Train results ZIP'):
                recognition.recognize([os.fspath(manifest), os.fspath(database)])
            with self.assertRaisesRegex(ValueError, 'SQLite database'):
                recognition.recognize([os.fspath(database)])


if __name__ == '__main__':
    unittest.main()
