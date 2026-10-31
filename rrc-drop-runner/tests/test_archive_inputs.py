import gzip
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parsers import extract


def info(name, year):
    entry = zipfile.ZipInfo(name, date_time=(year, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    return entry


class ArchiveInputsTest(unittest.TestCase):
    def archive(self, folder, raw, compressed, raw_year, gzip_year):
        archive = Path(folder) / 'input.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr(info('data.txt', raw_year), raw)
            z.writestr(info('data.txt.gz', gzip_year), gzip.compress(compressed))
        return archive

    def test_identical_compressed_copy_is_processed_once(self):
        with tempfile.TemporaryDirectory() as t:
            notes = []
            files = extract(str(self.archive(t, b'one\n', b'one\n', 2020, 2026)), str(Path(t) / 'work'), notes)
            self.assertEqual([Path(f).read_bytes() for f in files], [b'one\n'])
            self.assertIn('identical', notes[0])

    def test_newer_compressed_version_wins_without_overwriting_original(self):
        with tempfile.TemporaryDirectory() as t:
            notes = []
            files = extract(str(self.archive(t, b'old\n', b'new\n', 2020, 2026)), str(Path(t) / 'work'), notes)
            self.assertEqual([Path(f).read_bytes() for f in files], [b'new\n'])
            self.assertEqual((Path(t) / 'work' / 'data.txt').read_bytes(), b'old\n')
            self.assertIn('newer compressed', notes[0])

    def test_different_versions_with_equal_timestamps_do_not_get_guessed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, 'same timestamp'):
                extract(str(self.archive(t, b'one\n', b'two\n', 2026, 2026)), str(Path(t) / 'work'))


if __name__ == '__main__':
    unittest.main()
