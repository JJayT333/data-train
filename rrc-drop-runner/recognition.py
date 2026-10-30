"""Conservative local recognition. File extensions never establish a dataset match.

Names narrow candidates; the existing layout or a distinctive header validates them.
If multiple existing routes still fit, the caller must ask the user to choose.
"""
import csv
import json
import os
import re
from pathlib import Path
from parsers import ROOT, TOOLS, IMAGE_SLUGS, RETIRED

CATALOG = json.loads((Path(TOOLS) / 'datasets-catalog.json').read_text())
BY = {d['slug']: d for d in CATALOG}
LAYOUTS = {p.stem: json.loads(p.read_text()) for p in (Path(ROOT) / 'layouts').glob('*.json')}
ALIASES = {
    'full_wellbore': ['dbf900', 'wb_head'],
    'statewide_api_data': ['maf016'], 'statewide_api_data_2': ['api507'],
    'drilling_permit_master': ['daf802', 'daf800'],
    'horizontal_drilling_permits_permit_issue_date_permit_api_permitted_field': ['daf318', 'horizontal_permits'],
    'gas_annual_report_field_table': ['gsf384'], 'oil_annual_report_field_table': ['olf334'],
    'oil_gas_field_name_numbers': ['fldtpe'],
    'oil_gas_field_rules': ['og_field', 'field_rule'],
    'statewide_field_data': ['flf900'],
    'pr_p1_p2_gas_disposition': ['gsf', 'olf'],
    'pr_p1_p2_gas_disposition_2': ['gsf', 'olf'],
    'historical_ledger_statewide_gas': ['ldf900g'],
    'historical_ledger_statewide_oil': ['ldf900o'],
    'p5_organization': ['orf850'], 'p5_organization_2': ['orf850'],
    'r3_gas_processing_plants': ['grf', 'r3'],
    'full_wellbore_2': ['dbf900'],
    'statewide_oil_well_database': ['wlf100'], 'statewide_gas_well_database': ['wlf101'],
    'oil_detail_well': ['oltdw'], 'oil_well_status_26_month_w_10': ['wlf607'],
    'gas_well_status_26_month_g_10': ['gse10'],
    'high_cost_gas': ['ngf115'], 'high_cost_gas_tight_sands_only': ['ngf019'],
    'natural_gas_policy_act': ['ogfpm'],
    'statewide_production_data_oil': ['pdf100'], 'statewide_production_data_gas': ['pdf101'],
    'st_1_application_report': ['st1applicationreport', 'st_1'],
    'uic_database': ['uif700'], 'uic_database_2': ['uif700a'],
    'wellbore_query_data': ['og_wellbore_ewa'],
    'rrc_oil_ice_data': ['inspections', 'violations', 'oil_ice'],
    'certificate_of_authorization_p_4_database_oil_and_gas': ['p4', 'paf'],
}
for slug in BY:
    if slug.startswith('gas_ledger_'): ALIASES[slug] = ['gsf001', 'gsf102']
    if slug.startswith('oil_ledger_'): ALIASES[slug] = ['olf004', 'olf007', 'olf102']

def supported_catalog():
    # Keep source GIS routes intact, but this release does not offer or claim GIS conversion.
    return [dict(d, support=('Files only, no text extraction' if d['slug'] in IMAGE_SLUGS else
                            'Not yet verified' if d['slug'].startswith('drilling_permits_pending') else
                            'Supported'))
            for d in CATALOG if d['slug'] not in RETIRED and not any('shape' in f.lower() for f in d['formats'])]

def _named(slug, name):
    name = name.lower()
    return slug in name or any(a in name for a in ALIASES.get(slug, []))

def _lines(raw):
    return [l.rstrip('\r') for l in raw.decode('latin-1').split('\n')[:-1] if l.strip()][:40]

def _ebcdic(spec, raw, size):
    length = spec['reclen']
    if size < length or size % length: return False
    records = [raw[i:i+length] for i in range(0, min(len(raw)//length, 40)*length, length)]
    if not records: return False
    # Binary EBCDIC must not be mistaken for a printable ASCII download.
    if all(32 <= b < 127 or b in (9,10,13) for b in raw[:4096]): return False
    pos, width = spec['id_pos']
    if width:
        keys = [r[pos:pos+width].decode('cp037') for r in records]
        if sum(k in spec['records'] for k in keys) / len(keys) < .95: return False
    # Validate numeric fields as well as record ids, using the owning layout.
    checks = []
    for r in records:
        key = r[pos:pos+width].decode('cp037') if width else next(iter(spec['records']))
        lay = spec['records'].get(key)
        if not lay: continue
        for _, start, count, typ, _ in lay['fields']:
            if typ not in ('9', 'N') or count < 2: continue
            v = r[start:start+count].decode('cp037').strip()
            checks.append(not v or v.isdigit())
    return not checks or sum(checks)/len(checks) >= .9

def _layout_matches(slug, raw, size, named):
    spec = LAYOUTS.get(slug)
    if not spec or spec['kind'] == 'pending_multi': return False
    if spec['kind'] == 'ebcdic':
        # No-id binary layouts need a known filename; record size alone is insufficient.
        return (named or spec['id_pos'][1] > 0) and _ebcdic(spec, raw, size)
    lines = _lines(raw)
    if not lines: return False
    if spec['kind'] == 'delim':
        delimiter = spec['delim']
        if delimiter == 'auto': delimiter = max('}|\t,', key=lambda d: lines[0].count(d))
        rows = list(csv.reader(lines[:12], delimiter=delimiter))
        columns = list(spec['tables'].values())
        header = [x.strip().lower() for x in rows[0]]
        distinctive = any(header[:min(5,len(c))] == c[:min(5,len(c))] for c in columns)
        counts = {len(c) for c in columns}
        return (named or distinctive) and all(len(r) in counts or (len(r)-1 in counts and not r[-1].strip()) for r in rows)
    if not named: return False
    idlen = spec['id_len']
    good = 0
    for i, line in enumerate(lines):
        if spec.get('skip_line_prefix') and line.startswith(spec['skip_line_prefix']): good += 1; continue
        key = spec.get('first_record') if i == 0 and spec.get('first_record') else line[:idlen] if idlen else next(iter(spec['records']))
        if key not in spec['records']: continue
        minimum = max(s+l for _, s, l in spec['records'][key]['fields'])
        if len(line) >= minimum * .8 and not line.lstrip().startswith(('<', '{')): good += 1
    return good / len(lines) >= .95

def _one(path, outer_name):
    with open(path, 'rb') as f: raw = f.read(128 * 1024)
    name = os.path.basename(path).lower()
    names = name + ' ' + outer_name.lower()
    size = os.path.getsize(path)
    if not size: return {}
    stripped = raw.lstrip().lower()
    if stripped.startswith((b'<!doctype html', b'<html')):
        raise ValueError('This is a saved webpage. Download the data file from RRC and try again.')
    if b'EXPORT:V' in raw[:64]:
        raise ValueError('This is an Oracle export dump. Import it with Oracle, export its tables as text, then choose those text files here.')
    if raw.startswith((b'%PDF-', b'II*\x00', b'MM\x00*')):
        image_names = {'imaged_completion_files':['imaged_completion','imaged_completions'],
                       'directional_survey_applications':['dir_surveys','directional_survey'],
                       'drilling_permit_w1_imaged_files':['w1_imaged'],
                       'boundary_ventures_site_data':['boundary_ventures']}
        return {s:'Known archive name and image/PDF file signature (files only, no OCR)'
                for s, aliases in image_names.items() if any(a in names for a in aliases)}
    if name.endswith(('.pdf','.doc','.docx','.readme','.md')) or 'layout' in name or 'readme' in name: return {}
    matches = {}
    header = raw.splitlines()[0].decode('latin-1') if raw.splitlines() else ''
    if {'ST1_DOCKET_ID','DISTRICT_NBR','LEASE_NBR','OPERATOR_P5'}.issubset(set(header.split(','))):
        matches['st_1_application_report'] = 'Distinctive ST-1 column headers'
    if stripped.startswith(b'{'):
        if re.search(rb'"R3Report"\s*:\s*\[', raw[:2048]): matches['r3_gas_processing_plants_2'] = 'R3Report JSON signature'
        if re.search(rb'"P18SkimOilCondensateReport"\s*:\s*\[', raw[:2048]):
            slug = next((s for s in BY if 'p_18' in s or 'p18' in s), None)
            if slug: matches[slug] = 'P-18 report JSON signature'
    if name.startswith('api') and size >= 32 and raw[0] in (3, 0x83, 0x8b, 0x30, 0x31, 0xf5):
        hlen = int.from_bytes(raw[8:10], 'little'); rlen = int.from_bytes(raw[10:12], 'little')
        fields = [raw[i:i+11].split(b'\0')[0].decode('ascii', 'ignore').upper() for i in range(32,min(hlen-1,len(raw)),32)]
        if hlen > 32 and rlen > 1 and any('API' in x for x in fields) and any('QUAD' in x for x in fields):
            matches['statewide_api_data_2'] = 'API dBase field descriptors'
    lines = _lines(raw)
    if lines and any(l.startswith('PACKET{') for l in lines) and any(l.startswith(('G-1{','W-2{','P-4{')) for l in lines):
        matches['completion_information_in_data_format'] = 'Completion packet and form record tags'
    if _named('drilling_permit_master', names) and lines:
        if all(l[:2].isdigit() and 1 <= int(l[:2]) <= 15 and len(l) >= 16 for l in lines) and any(l.startswith('01') and len(l)>=200 for l in lines):
            matches['drilling_permit_master'] = 'DAF filename and W-1 record signatures'
    if _named('statewide_api_data', names) and lines and all(len(l)>=100 and l[:15].isdigit() for l in lines):
        matches['statewide_api_data'] = 'MAF016 filename and numeric API/quad prefix'
    if _named('full_wellbore', names) and size % 247 == 0 and raw[:2].decode('cp037', 'ignore').isdigit():
        blocks = [raw[i:i+247] for i in range(0,min(len(raw)//247,40)*247,247)]
        if blocks and all(b[:2].decode('cp037') in {f'{i:02}' for i in range(1,29)} for b in blocks):
            matches['full_wellbore'] = '247-byte Full Wellbore records'
    for slug in LAYOUTS:
        if slug in BY and slug != 'statewide_api_data' and _layout_matches(slug,raw,size,_named(slug,names)):
            matches[slug] = 'Known filename and validated layout' if _named(slug,names) else 'Validated record layout'
    if _named('p5_organization_2',names) and lines:
        from layouts_p5 import P5
        if all(l[:2] in P5 for l in lines): matches['p5_organization_2']='P-5 ASCII record signatures'
    pending = LAYOUTS['pending_permits_multi']['files']
    for tab, columns in pending.items():
        if name.startswith(tab) and lines and all(len(l.split('}')) in (len(columns),len(columns)+1) for l in lines):
            slug = next(s for s in BY if s.startswith('drilling_permits_pending'))
            matches[slug] = 'Pending-permit member name and field count (parser not yet verified)'
    return matches

def recognize(files, original_name=''):
    evidence = {}
    sets = []
    for path in files:
        found = _one(path, original_name)
        if found:
            sets.append(set(found))
            for slug, reason in found.items(): evidence.setdefault(slug, []).append(reason)
        elif not os.path.basename(path).lower().endswith(('.pdf','.md','.doc','.docx')) and 'readme' not in os.path.basename(path).lower() and 'layout' not in os.path.basename(path).lower():
            sets.append(set())
    # A ZIP must agree across data members. Do not confidently parse a mixed archive.
    candidates = set.intersection(*sets) if sets else set()
    items = [dict(slug=s, name=BY[s]['name'], formats=BY[s]['formats'], reasons=sorted(set(evidence[s]))) for s in sorted(candidates)]
    status = 'recognized' if len(items)==1 else 'ambiguous' if items else 'unknown'
    return dict(status=status, slug=items[0]['slug'] if len(items)==1 else None, candidates=items,
                message='Dataset recognized and its content validated.' if len(items)==1 else
                'More than one dataset fits this file. Choose its dataset before converting.' if items else
                'This file could not be identified safely. Choose its dataset to use an existing parser.')
