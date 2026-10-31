import csv
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parsers import p_csv, p_ebcdic, p_fixed, p_pdq, p_p5_bundle, save
from pending_permits import p_pending, LAY
import pandas as pd
from recognition import recognize


class RealInputShapesTest(unittest.TestCase):
    def test_pending_decodes_quoted_fields_and_embedded_delimiters(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'dp_latlongs_pending_20261030.txt'
            source.write_text('API_SEQUENCE_NUMBER}LATITUDE}LONGITUDE}LOCATION_TYPE\n"07735430"}"34.00395188"}"-98.18595132"}"SURFACE}TEST"}\n', encoding='ascii')
            out = root / 'out'; out.mkdir()
            counts, _ = p_pending([str(source)], str(out), save, pd, os)
            self.assertEqual(counts, {'dp_latlongs_pending': 1})
            with closing(sqlite3.connect(out / 'data.sqlite')) as db:
                row = db.execute('SELECT API_SEQUENCE_NUMBER, LOCATION_TYPE FROM dp_latlongs_pending').fetchone()
            self.assertEqual(row, ('07735430', 'SURFACE}TEST'))

    def test_ebcdic_missing_value_remains_null_in_sqlite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = bytearray(('01G01000017' + ' ' * 149).encode('cp037'))
            record[11:26] = b'\0' * 15
            source = root / 'ldf900gs.ebc'; source.write_bytes(record)
            out = root / 'out'; out.mkdir()
            counts, _ = p_ebcdic('historical_ledger_statewide_gas')([str(source)], str(out))
            self.assertEqual(counts, {'01_root': 1})
            with closing(sqlite3.connect(out / 'data.sqlite')) as db:
                value = db.execute('SELECT ld_gas_oldest_eom_balance FROM "01_root"').fetchone()[0]
            self.assertIsNone(value)

    def test_pending_production_and_directional_survey_are_recognized(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            production = root / 'pr_production_report_20261017.txt'
            production.write_text('PRODUCTION_REPORT_ID}PROD_CYCLE_YYYYMM}CRCTD_FILING_FLAG}CMGL_LEASE_TOT_FLAG}CURRENT_MONTH_FLAG\n1}202601}N}N}Y\n', encoding='ascii')
            self.assertEqual(recognize([str(production)], production.name)['slug'], 'production_report_for_pending_leases')
            survey = root / 'dir_survey_123.pdf'; survey.write_bytes(b'%PDF-1.7\n')
            index = root / 'directional_surveys_10-28-2026_1.csv'
            index.write_text('API_NO,EXTERNAL_ATTACHMENT_ID,ATTACHMENT_TYPE_CODE,FROM_DEPTH,TO_DEPTH\n00123456,123,Gyro,0,100\n', encoding='ascii')
            self.assertEqual(recognize([str(survey), str(index)], '10-28-2026.zip')['slug'], 'directional_survey_applications')

    def test_ebcdic_preserves_zero_padded_gas_well_identifier(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = list(' ' * 200)
            record[2:8] = '000017'
            source = root / 'gsf102.ebc'
            source.write_bytes(''.join(record).encode('cp037'))
            out = root / 'out'; out.mkdir()
            counts, _ = p_ebcdic('pr_p1_p2_gas_disposition_2')([str(source)], str(out))
            self.assertEqual(counts, {'gas_well_gas_disposition': 1})
            with closing(sqlite3.connect(out / 'data.sqlite')) as db:
                actual = db.execute('SELECT gd_pr_gas_well_gas_rrcid FROM gas_well_gas_disposition').fetchone()[0]
            self.assertEqual(actual, '000017')

    def test_gas_disposition_preserves_distinct_source_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = list(' ' * 200)
            fields = {
                'gd_pr_gas_well_gas_rrcid': (2, '123456'),
                'gd_pr_gas_well_gas_balancing_code': (14, 'B'),
                'gd_pr_gas_well_gas_number': (102, '654321'),
                'gd_pr_gas_well_gas_lift': (137, '0000123'),
                'gd_pr_gas_well_gas_production': (172, '0000456'),
                'gd_pr_gas_well_gas_lift_injected': (179, '0000789'),
            }
            for start, value in fields.values():
                record[start:start + len(value)] = value
            source = root / 'gsf102.txt'
            source.write_text(''.join(record) + '\n', encoding='ascii')
            out = root / 'out'; out.mkdir()
            counts, _ = p_fixed('pr_p1_p2_gas_disposition')([str(source)], str(out))
            self.assertEqual(counts, {'gas_well_gas_disposition': 1})
            with closing(sqlite3.connect(out / 'data.sqlite')) as db:
                columns = ', '.join(fields)
                actual = db.execute(f'SELECT {columns} FROM gas_well_gas_disposition').fetchone()
            self.assertEqual(actual, tuple(value for _, value in fields.values()))

    def test_pending_retains_mismatches_from_each_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); files = []
            for suffix in ('one', 'two'):
                source = root / f'dp_latlongs_pending_{suffix}.txt'
                source.write_text('API_SEQUENCE_NUMBER}LATITUDE}LONGITUDE}LOCATION_TYPE\n123}30}\n', encoding='ascii')
                files.append(str(source))
            out = root / 'out'; out.mkdir()
            counts, _ = p_pending(files, str(out), save, pd, os)
            self.assertEqual(counts['dp_latlongs_pending_mismatch'], 2)
            with closing(sqlite3.connect(out / 'data.sqlite')) as db:
                names = {row[0] for row in db.execute('SELECT file FROM dp_latlongs_pending_mismatch')}
            self.assertEqual(names, {Path(f).name for f in files})

    def test_pending_uses_wrapped_original_headings_and_new_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'dp_drilling_permit_pending_20261030.txt'
            columns = list(LAY['files']['dp_drilling_permit_pending'])
            columns.insert(-1, 'NEW_RRC_FIELD')
            header = '}'.join(columns) + '}'
            row = [''] * len(columns); row[columns.index('NEW_RRC_FIELD')] = 'new value'
            source.write_text(header[:120] + '\n' + header[120:] + '\n\n' + '}'.join(row) + '}\n', encoding='ascii')
            self.assertEqual(recognize([str(source)], source.name)['slug'], 'drilling_permits_pending_approval_includes_latitudes_and_longitudes')
            out = root / 'out'; out.mkdir()
            counts, _ = p_pending([str(source)], str(out), save, pd, os)
            self.assertEqual(counts, {'dp_drilling_permit_pending': 1})
            with closing(sqlite3.connect(out / 'data.sqlite')) as db:
                self.assertEqual(db.execute('SELECT NEW_RRC_FIELD FROM dp_drilling_permit_pending').fetchone()[0], 'new value')

    def test_pdq_table_recognizes_and_preserves_identifiers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'OG_COUNTY_CYCLE_DATA_TABLE.dsv'
            source.write_text('COUNTY_NO}DISTRICT_NO}CYCLE_YEAR\n001}05}1993\n', encoding='ascii')
            self.assertEqual(recognize([str(source)], source.name)['slug'], 'production_data_query_dump')
            out = root / 'out'; out.mkdir()
            counts, _ = p_pdq([str(source)], str(out))
            self.assertEqual(counts['OG_COUNTY_CYCLE_DATA_TABLE_dsv'], 1)
            with closing(sqlite3.connect(out / 'data.sqlite')) as db:
                self.assertEqual(db.execute('SELECT COUNTY_NO, DISTRICT_NO FROM OG_COUNTY_CYCLE_DATA_TABLE_dsv').fetchone(), ('001', '05'))

    def test_pdq_preserves_literal_quotes_and_csv_still_decodes_quoted_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'OG_COUNTY_LEASE_CYCLE_DATA_TABLE.dsv'
            source.write_text('LEASE_NAME}OPERATOR\n"Q" MADDOX}A, B\n', encoding='ascii')
            out = root / 'pdq'; out.mkdir()
            p_pdq([str(source)], str(out))
            with closing(sqlite3.connect(out / 'data.sqlite')) as db:
                self.assertEqual(db.execute('SELECT LEASE_NAME, OPERATOR FROM OG_COUNTY_LEASE_CYCLE_DATA_TABLE_dsv').fetchone(), ('"Q" MADDOX', 'A, B'))
            with (out / 'OG_COUNTY_LEASE_CYCLE_DATA_TABLE_dsv.csv').open(newline='', encoding='utf-8') as f:
                self.assertEqual(list(csv.reader(f))[1], ['"Q" MADDOX', 'A, B'])
            source = root / 'regular.csv'
            source.write_text('NAME,OPERATOR\n"A, B","""Q"" MADDOX"\n', encoding='ascii')
            out = root / 'csv'; out.mkdir()
            p_csv([str(source)], str(out))
            with closing(sqlite3.connect(out / 'data.sqlite')) as db:
                self.assertEqual(db.execute('SELECT NAME, OPERATOR FROM regular_csv').fetchone(), ('A, B', '"Q" MADDOX'))

    def test_mixed_p5_archive_keeps_both_formats_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = ('1T' + 'CODE01' + 'SR' + 'A test specialty').ljust(350)
            text = root / 'orf850.txt'; text.write_text(record.rstrip() + '\n', encoding='ascii')
            binary = root / 'orf850.ebc'; binary.write_bytes(record.encode('cp037'))
            files = [str(text), str(binary)]
            self.assertEqual(recognize(files, 'P5.zip')['slug'], 'p5_organization')
            out = root / 'out'; out.mkdir()
            counts, note = p_p5_bundle(files, str(out))
            self.assertEqual(counts, {'ascii_specialty_code_table': 1, 'ebcdic_specialty_code_table': 1})
            self.assertIn('separately', note)
            self.assertIn('1 ASCII rows + 1 EBCDIC rows', note)
            self.assertIn('not a count of unique records', note)
            with closing(sqlite3.connect(out / 'data.sqlite')) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM ascii_specialty_code_table').fetchone()[0], 1)
                self.assertEqual(db.execute('SELECT count(*) FROM ebcdic_specialty_code_table').fetchone()[0], 1)
            with patch.dict(os.environ, {'RRC_DATA_DIR': str(root / 'service-data')}):
                import service
                item = dict(files=files, filename='P5.zip', detection={'slug': 'p5_organization'}, result=None)
                with patch.object(service, 'OUT', root), patch.dict(service.UPLOADS, {'p5-test': item}):
                    result = service.convert('p5-test')
                    self.assertEqual(result['records'], 2)
                    self.assertEqual(result['record_unit'], 'output rows')
                    self.assertIn('1 ASCII rows + 1 EBCDIC rows', result['note'])


if __name__ == '__main__':
    unittest.main()
