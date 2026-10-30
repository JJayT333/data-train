import os, sys, io, json, zipfile, sqlite3, subprocess, csv, tempfile
import pandas as pd
ROOT = os.path.join(sys._MEIPASS, 'rrc-drop-runner') if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(ROOT)
HARVEST = os.path.join(TOOLS, 'TXRRC_data_harvest')
W1 = os.path.join(TOOLS, 'w1-data-parser')

def extract(path, work):
    """Unzip if needed; return list of member files."""
    head = open(path, 'rb').read(512).lstrip().lower()
    if head.startswith((b'<?xml', b'<!doctype html', b'<html')) and b'<html' in head:
        raise ValueError('This file is a saved web page (HTML), not RRC data. Re-download it with the file link on the RRC page, not "Save page as".')
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            base = os.path.realpath(work)
            for member in z.infolist():
                target = os.path.realpath(os.path.join(work, member.filename))
                if os.path.commonpath([base, target]) != base:
                    raise ValueError('This ZIP contains an unsafe member path. Choose the original RRC download.')
            z.extractall(work)
        files = []
        for d, _, fs in os.walk(work):
            for f in fs:
                p = os.path.join(d, f)
                if zipfile.is_zipfile(p):  # nested zips
                    files += extract(p, os.path.splitext(p)[0] + '_unzipped')
                else: files += _gunzip(p)
        return files
    return _gunzip(path)

def _gunzip(p):
    """RRC ships many files as .gz (e.g. orf850.ebc.gz, wlf607.ebc.gz); decompress so fixed-width parsers see raw records."""
    import gzip, shutil as _sh
    with open(p, 'rb') as fh: magic = fh.read(2)
    if magic != b'\x1f\x8b': return [p]
    dst = p[:-3] if p.lower().endswith('.gz') else p + '.raw'
    with gzip.open(p, 'rb') as src, open(dst, 'wb') as d: _sh.copyfileobj(src, d, 1 << 20)
    return [dst]

def save(tables, out):
    """tables: {name: DataFrame} -> CSV + one SQLite db. Returns {name: rows}."""
    db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
    counts = {}
    for n, df in tables.items():
        df = df.copy(); df.columns = [str(c) for c in df.columns]
        df.to_csv(os.path.join(out, f'{n}.csv'), index=False)
        df.astype(str).to_sql(n, db, if_exists='replace', index=False)
        counts[n] = len(df)
    db.close(); return counts

def safe(n): return ''.join(c if c.isalnum() else '_' for c in os.path.basename(n))[:60]

# ---- generic loaders ----
def p_csv(files, out):
    t = {}
    for f in files:
        if not f.lower().endswith(('.pdf', '.md', '.doc', '.docx')):
            with open(f, encoding='latin-1', newline='') as fh:
                first = fh.readline()
                try: sep = '}' if first.count('}') > 2 else csv.Sniffer().sniff(first).delimiter
                except csv.Error:
                    raise ValueError(f'{os.path.basename(f)}: could not identify the column separator. Choose the original RRC text download.')
                fh.seek(0); reader = csv.reader(fh, delimiter=sep)
                columns = next(reader, [])
                rows = []
                for row in reader:
                    if not row: continue
                    if len(row) > len(columns):
                        if any(value != '' for value in row[len(columns):]):
                            raise ValueError(f'{os.path.basename(f)}, line {reader.line_num}: found {len(row)} fields for {len(columns)} headings, including nonempty extra fields. Check the original download and delimiter; no records were converted.')
                        row = row[:len(columns)]  # RRC can append empty trailing delimiters.
                    rows.append(row + [''] * (len(columns) - len(row)))
                t[safe(f)] = pd.DataFrame(rows, columns=columns, dtype=str)
    return save(t, out), None

def _load_json(f):
    raw = open(f, 'rb').read()
    try: return json.loads(raw.decode('utf-8-sig'))
    except UnicodeDecodeError: return json.loads(raw.decode('cp1252', errors='replace'))  # RRC P-18 has stray 0xA0 bytes

def p_json(files, out):
    """Top-level records -> one table; nested lists of objects (e.g. R-3 'Section VIII ...') -> child
    tables keyed by parent_row (and the parent's first column) instead of being stuffed into one cell."""
    t = {}
    for f in files:
        if not f.lower().endswith('.json'): continue
        data = _load_json(f)
        if isinstance(data, dict):
            lists = {k: v for k, v in data.items() if isinstance(v, list)}
            data = next(iter(lists.values())) if lists else [data]
        base = safe(f); rows = []; kids = {}
        for i, rec in enumerate(data):
            if not isinstance(rec, dict): rows.append({'value': rec}); continue
            flat = {}; key = next(iter(rec.items()), (None, None))
            for k, v in rec.items():
                if isinstance(v, list) and any(isinstance(x, dict) for x in v):
                    for j, x in enumerate(v):
                        kids.setdefault(k, []).append({'parent_row': i, key[0]: key[1], 'row_no': j + 1, **(x if isinstance(x, dict) else {'value': x})})
                    flat[k + ' (rows)'] = len(v)
                else: flat[k] = v
            rows.append(flat)
        t[base] = pd.json_normalize(rows)
        for k, v in kids.items(): t[(base + '__' + safe(k))[:60]] = pd.json_normalize(v)
    return save(t, out), None

def p_dbf(files, out):
    import shapefile  # pyshp has a DBF reader via shapefile.Reader(dbf=...)
    t = {}
    for f in files:
        if f.lower().endswith('.dbf'):
            r = shapefile.Reader(dbf=open(f, 'rb'))
            t[safe(f)] = pd.DataFrame(r.records(), columns=[x[0] for x in r.fields[1:]])
    return save(t, out), None

def p_shape(files, out):
    import shapefile
    t = {}
    for f in files:
        if f.lower().endswith('.shp'):
            r = shapefile.Reader(f)
            df = pd.DataFrame(r.records(), columns=[x[0] for x in r.fields[1:]])
            df['shape_type'] = r.shapeTypeName
            if r.shapeType in (1, 11, 21):
                pts = [s.points[0] if s.points else (None, None) for s in r.shapes()]
                df['x'] = [p[0] for p in pts]; df['y'] = [p[1] for p in pts]
            t[safe(f)] = df
    return save(t, out), None

def p_raw_lines(files, out, note):
    """Best-effort for fixed-width ASCII without a coded layout: split by record type (first 2 chars)."""
    rows = []
    for f in files:
        with open(f, 'r', encoding='latin-1', errors='ignore') as fh:
            for i, line in enumerate(fh):
                line = line.rstrip('\r\n')
                rows.append({'file': os.path.basename(f), 'line_no': i, 'rec_type': line[:2], 'length': len(line), 'raw': line})
    df = pd.DataFrame(rows)
    t = {'raw_lines': df}
    if len(df): t['record_type_summary'] = df.groupby(['rec_type', 'length']).size().reset_index(name='count')
    return save(t, out), note

def p_stub(files, out, note):
    info = [{'file': os.path.basename(f), 'bytes': os.path.getsize(f)} for f in files]
    open(os.path.join(out, 'TODO.md'), 'w').write('# Not parsed yet\n\n' + note + '\n\nFiles received:\n' + '\n'.join(f"- {i['file']} ({i['bytes']} bytes)" for i in info))
    return save({'files_received': pd.DataFrame(info)}, out), note

# ---- real wired parsers ----
def sniff_reclen(path, cands=(102, 110, 130, 160, 247, 1200, 2120)):
    """Best fixed record length: share of records starting with two EBCDIC digits."""
    b = open(path, 'rb').read(2_000_000); sc = {}
    for L in cands:
        n = min(len(b) // L, 3000)
        if n: sc[L] = sum(1 for i in range(n) if 0xf0 <= b[i*L] <= 0xf9 and 0xf0 <= b[i*L+1] <= 0xf9) / n
    return sc

HINT = {102: 'Statewide Production Data (PDF100 oil / PDF101 gas)', 160: 'Historical Ledger (LDF900)', 1200: 'Statewide Field Data (FLF900) or an Oil ledger', 2120: 'Gas ledger'}

def p_wellbore_ebcdic(files, out):
    for f in files:
        sc = sniff_reclen(f)
        if sc and sc.get(247, 0) < 0.95:
            best = max(sc, key=sc.get)
            raise ValueError(f'{os.path.basename(f)} does not look like Full Wellbore (247-byte records fit only {sc.get(247,0):.0%}); {best}-byte records fit {sc[best]:.0%} - try {HINT.get(best, "another EBCDIC dataset")}.')
    sys.path.insert(0, HARVEST)
    from ebcdic_main import yield_blocks, parse_record
    from layouts_wells_dbf900 import dbf900_layout
    from ebcdic_formats import pic_any
    recs = {}
    for f in files:
        with open(f, 'rb') as fh:
            api = None
            for block in yield_blocks(fh, 247):
                sv = pic_any(block[0:2])
                if sv == '01': api = '42' + pic_any(block[2:10])
                lay = dbf900_layout(sv)
                if not lay: continue
                v = parse_record(block, lay['layout']); v['API'] = api
                recs.setdefault(f'rec{sv}', []).append(v)
    return save({k: pd.DataFrame(v) for k, v in recs.items()}, out), None

W1_JS = r"""
const {W1Parser}=require(process.argv[2]);
(async()=>{const g=await new W1Parser().parseFile(process.argv[3],undefined,true);
const fs=require('fs');const o=fs.createWriteStream(process.argv[4]);
for(const x of g)o.write(JSON.stringify(x)+'\n');o.end();})().catch(e=>{console.error(e);process.exit(1)});
"""
def p_w1(files, out):
    js = os.path.join(out, '_w1.js'); open(js, 'w').write(W1_JS)
    if not os.path.exists(os.path.join(W1, 'dist', 'index.js')):
        raise ValueError('The bundled W-1 parser is missing. Extract the complete application ZIP again.')
    node = os.path.join(TOOLS, 'runtime', 'node.exe')
    if not os.path.isfile(node):
        if getattr(sys, 'frozen', False):
            raise ValueError('The bundled W-1 runtime is missing. Extract the complete application ZIP again.')
        from shutil import which
        node = which('node')
        if not node: raise ValueError('Node is required for source execution. Use the Windows release for a bundled runtime.')
    tables = {}
    for f in files:
        nd = os.path.join(out, safe(f) + '.ndjson')
        subprocess.run([node, js, os.path.join(W1, 'dist', 'index.js'), f, nd], check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        for gi, line in enumerate(open(nd)):
            g = json.loads(line)
            for seg, val in g.items():
                for v in (val if isinstance(val, list) else [val]):
                    if isinstance(v, dict):
                        tables.setdefault(f'seg{seg}', []).append({'group': gi, **{k: (json.dumps(x) if isinstance(x, (dict, list)) else x) for k, x in v.items()}})
    return save({k: pd.DataFrame(v) for k, v in tables.items()}, out), 'Grouped JSON also saved as .ndjson'

def route(ds):
    if ds.get('slug','').startswith('drilling_permits_pending'):
        from pending_permits import p_pending
        return 'wired:unverified', lambda files, out: p_pending(files, out, save, pd, os)
    s, fmts = ds['slug'], ' '.join(ds['formats']).lower()
    if s in ('full_wellbore',): return 'wired', p_wellbore_ebcdic
    if s in IMAGE_SLUGS: return 'wired:image-unpack', p_images
    if s in RETIRED: return 'retired', p_retired
    if s == 'statewide_api_data':
        from api_compressed import p_api_compressed
        return 'wired', lambda f, o: p_api_compressed(f, o, save, pd, os)
    if s == 'p5_organization_2': return 'wired', p_p5_ascii
    if s in LAYOUT_SLUGS:
        k = _layout(s)['kind']
        return 'wired', {'fixed': p_fixed, 'delim': p_delim, 'ebcdic': p_ebcdic}[k](s)
    if s == 'completion_information_in_data_format': return 'wired', p_completions
    if s.startswith('drilling_permit_master_and_trailer') or s == 'drilling_permit_master' or s.startswith('drilling_permits_pending') or s.startswith('horizontal_drilling'):
        return 'wired', p_w1
    if 'shape' in fmts: return 'wired', p_shape
    if 'dbase' in fmts: return 'wired', p_dbf
    if 'csv' in fmts: return 'wired', p_csv
    if 'json' in fmts: return 'wired', p_json
    man = ', '.join(ds['manual_local_paths']) or 'none listed'
    if 'ascii' in fmts or 'txt' in fmts:
        return 'best-effort', lambda f, o: p_raw_lines(f, o, f'Raw lines split by record type; field-level layout still TODO from manual: {man}')
    if 'ebcdic' in fmts:
        return 'stub', lambda f, o: p_stub(f, o, f'EBCDIC layout not coded yet. Build a layout from {man} (pattern: TXRRC_data_harvest/layouts_*.py).')
    return 'stub', lambda f, o: p_stub(f, o, f'{fmts or "no data file"}: PDF/image or no download — stored only.')

# ---- named-field parsers (P-5 ASCII, Completions) ----
def p_p5_ascii(files, out):
    from layouts_p5 import P5
    t, unk = {}, 0
    for f in files:
        for line in open(f, encoding='latin-1', errors='ignore'):
            line = line.rstrip('\r\n')
            if not line.strip(): continue
            lay = P5.get(line[:2])
            if not lay: unk += 1; continue
            name, flds = lay
            t.setdefault(name, []).append({n: line[s-1:s-1+l].strip() for n, s, l in flds})
    note = f'{unk} lines had an unknown record id' if unk else None
    return save({k: pd.DataFrame(v) for k, v in t.items()}, out), note

def p_completions(files, out):
    import json as _j
    L = _j.load(open(os.path.join(ROOT, 'layout_completions.json')))
    norm = {k.upper(): v for k, v in L.items()}
    t = {}
    for f in files:
        for i, line in enumerate(_completion_records(f, norm)):
            parts = line.split('{')
            tag = parts[0].strip().upper()
            key = tag if tag in norm else re_sub_prefix(tag)
            cols = norm.get(key)
            if i == 0 and cols is None and parts[0].strip().isdigit():
                t.setdefault('header', []).append({'file': os.path.basename(f), 'TRACKING_NO': parts[0], 'FORM_LISTING': parts[1] if len(parts) > 1 else '', 'ATTACHMENT_LISTING': '{'.join(parts[2:])}); continue
            if cols is None:
                cols = ['TAG']; key = 'unknown_' + safe(tag)
            row = {'file': os.path.basename(f)}
            for j, v in enumerate(parts):
                row[cols[j] if j < len(cols) else f'extra_{j}'] = v.strip()
            t.setdefault(safe(key).lower(), []).append(row)
    return save({k: pd.DataFrame(v) for k, v in t.items()}, out), 'Tables named by line tag; G-1/W-2 shared sub-tables keep the original tag in TAG.'

def _completion_records(f, norm):
    """Yield logical records: free-text remarks can contain line breaks, so a line whose
    tag is not a known record tag is a continuation of the previous record."""
    prev, gap = None, 0
    for i, line in enumerate(open(f, encoding='latin-1', errors='ignore')):
        line = line.rstrip('\r\n')
        if not line.strip(): gap += 1; continue
        tag = line.split('{')[0].strip().upper()
        known = i == 0 or tag in norm or re_sub_prefix(tag) in norm
        if prev is not None and not known:
            prev += '\n' * (gap + 1) + line; gap = 0; continue
        if prev is not None: yield prev
        prev, gap = line, 0
    if prev is not None: yield prev

def re_sub_prefix(tag):
    import re
    return re.sub(r'^(G-1|W-2)\s+', '', tag)

# ---- manual-derived layouts (layouts/<slug>.json, built by tools/build_layouts.py) ----
def _layout(slug): return json.load(open(os.path.join(ROOT, 'layouts', slug + '.json')))

def _pick(spec, fname):
    up = os.path.basename(fname).upper()
    for k, v in spec.get('by_filename', {}).items():
        if k and k in up: return v
    return spec.get('by_filename', {}).get('')

def p_fixed(slug):
    spec = _layout(slug)
    def run(files, out):
        t, unk = {}, {}
        for f in files:
            if f.lower().endswith(('.pdf', '.doc', '.docx')): continue
            default = _pick(spec, f) if 'by_filename' in spec else ''
            with open(f, 'r', encoding='latin-1', errors='ignore', newline='') as fh:
                for i, line in enumerate(fh):
                    line = line.rstrip('\r\n')
                    if not line.strip(): continue
                    if spec.get('skip_line_prefix') and line.startswith(spec['skip_line_prefix']): continue  # column-title row
                    if i == 0 and spec.get('first_record'): key = spec['first_record']
                    elif spec['id_len']: key = line[:spec['id_len']]
                    else: key = default
                    rec = spec['records'].get(key)
                    if not rec: unk[key] = unk.get(key, 0) + 1; continue
                    t.setdefault(rec['table'], []).append({n: line[s:s+l].strip() for n, s, l in rec['fields']})
        note = f"Layout from manuals/{spec['manual']}."
        if unk: note += ' Unknown record ids skipped: ' + ', '.join(f'{k!r}×{v}' for k, v in unk.items())
        return save({k: pd.DataFrame(v) for k, v in t.items()}, out), note
    return run

def p_delim(slug):
    spec = _layout(slug)
    def run(files, out):
        t = {}; notes = []
        for f in files:
            raw = open(f, 'rb').read(4096)
            if f.lower().endswith('.dmp') or b'EXPORT:V' in raw[:64]:
                notes.append(f'{os.path.basename(f)} is an Oracle export (.dmp); open it with Oracle imp/impdp, then export the tables as text and drop them here.'); continue
            text = raw.decode('latin-1')
            d = spec['delim']
            if d == 'auto': d = max(['}', '|', '\t', ','], key=lambda x: text.count(x))
            tabs = spec['tables']
            name = _pick(spec, f) if 'by_filename' in spec else next(iter(tabs))
            rows = []
            with open(f, 'r', encoding='latin-1', errors='ignore', newline='') as fh:
                rd = csv.reader(fh, delimiter=d) if spec.get('csv_quoting') else (l.rstrip('\r\n').split(d) for l in fh)
                for row in rd:
                    if not any(x.strip() for x in row): continue
                    rows.append([x.strip() for x in row])
            if not rows: continue
            if spec.get('by_count'):
                n = len(rows[0]); m = [k for k, v in tabs.items() if len(v) == n]
                if m and (name is None or len(tabs[name]) != n): name = m[0]
            cols = tabs[name]
            if [x.lower() for x in rows[0]][:3] == cols[:3]: rows = rows[1:]  # header row
            recs = [{(cols[j] if j < len(cols) else f'extra_{j+1}'): v for j, v in enumerate(r)} for r in rows]
            t.setdefault(name, []).extend(recs)
        notes.insert(0, f"Columns from manuals/{spec['manual']}.")
        return save({k: pd.DataFrame(v) for k, v in t.items()}, out), ' '.join(notes)
    return run

LAYOUT_SLUGS = {os.path.splitext(x)[0] for x in os.listdir(os.path.join(ROOT, 'layouts'))}

# ---- EBCDIC (fixed-length binary records, cp037/cp1140 text, zoned + COMP-3 numbers) ----
def _ebc_helpers():
    sys.path.insert(0, HARVEST)
    from ebcdic_formats import comp3, pic_signed, ebc_decode
    return comp3, pic_signed, ebc_decode

def _decode(b, typ, dec, name, H):
    comp3, pic_signed, ebc = H
    try:
        if typ == 'X': return ebc(b).strip()
        if typ == 'P':
            if not any(b): return None
            return comp3(b, dec)
        if typ == 'S': return pic_signed(b, name.upper(), dec)
        s = ebc(b).strip()
        if s.isdigit(): return int(s) / 10**dec if dec else int(s)
        return s or None
    except Exception:
        return b.hex()

def p_ebcdic(slug):
    spec = _layout(slug)
    def run(files, out):
        H = _ebc_helpers(); rl = spec['reclen']; a, n = spec['id_pos']
        t, unk, notes = {}, {}, []
        for f in files:
            if f.lower().endswith(('.pdf', '.txt')) and os.path.getsize(f) < 1: continue
            data = open(f, 'rb').read()
            if len(data) % rl: notes.append(f'{os.path.basename(f)}: {len(data) % rl} trailing bytes ignored (size not a multiple of {rl})')
            fixed = _pick(spec, f) if 'by_filename' in spec else ''
            for o in range(0, len(data) - rl + 1, rl):
                rec = data[o:o+rl]
                key = H[2](rec[a:a+n]) if n else fixed
                lay = spec['records'].get(key)
                if not lay: unk[key] = unk.get(key, 0) + 1; continue
                t.setdefault(lay['table'], []).append({fn: _decode(rec[s:s+l], ty, d, fn, H) for fn, s, l, ty, d in lay['fields']})
        note = f"Layout from manuals/{spec['manual']}."
        if unk: note += ' Unknown record ids skipped: ' + ', '.join(f'{k!r}x{v}' for k, v in list(unk.items())[:10])
        return save({k: pd.DataFrame(v) for k, v in t.items()}, out), ' '.join([note] + notes)
    return run

# ---- imaged products: unpack + organize + index (no OCR) ----
IMAGE_SLUGS = {'drilling_permit_w1_imaged_files', 'directional_survey_applications', 'imaged_completion_files', 'boundary_ventures_site_data'}
RETIRED = {'3_month_wellbore', '3_month_wellbore_2'}

def _ids_from_name(rel):
    import re
    name = rel.replace('\\', '/')
    g = lambda p: (re.search(p, name, re.I).group(1) if re.search(p, name, re.I) else '')
    return {
        'api_no': g(r'(?<!\d)(42\d{8}|\d{3}-\d{5}|\d{8})(?!\d)'),
        'tracking_no': g(r'trackingNo_(\d+)'),
        'packet_id': g(r'packet(?:Data)?_(\d+)'),
        'permit_no': g(r'(?:permit|w1|dp)[_\- ]?(\d{6})(?!\d)'),
        'district': g(r'(?:dist(?:rict)?[_\- ]?|^)(0[1-9]|10|6E|7B|7C|8A)(?:\b|/)'),
        'date': g(r'(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2}|\d{8})'),
        'status': g(r'_(approved|submitted)'),
    }

def p_images(files, out):
    import shutil, re
    root = os.path.commonpath([os.path.dirname(f) for f in files]) if files else ''
    if re.fullmatch(r'(0[1-9]|10|6E|7B|7C|8A)', os.path.basename(root), re.I): root = os.path.dirname(root)  # keep district folder
    rows = []
    for f in files:
        rel = os.path.relpath(f, root)
        dest = os.path.join(out, 'files', rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.copy2(f, dest)
        rows.append({'path': os.path.relpath(dest, out), 'folder': os.path.dirname(rel), 'file': os.path.basename(f),
                     'extension': os.path.splitext(f)[1].lower().lstrip('.'), 'bytes': os.path.getsize(f), **_ids_from_name(rel)})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out, 'index.csv'), index=False)
    counts = save({'image_index': df}, out)
    return counts, 'Image unpack only (no OCR): files copied under files/ keeping the zip folder structure; index.csv lists each file with IDs parsed from names.'

def p_retired(files, out):
    return p_stub(files, out, 'RRC retired this dataset ("no longer available"); the same data is in Full Wellbore. Use the full_wellbore (EBCDIC) or full_wellbore_2 (ASCII) option.')
