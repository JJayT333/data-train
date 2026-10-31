import os, sys, io, json, zipfile, sqlite3, subprocess, csv, tempfile
import pandas as pd
ROOT = os.path.join(sys._MEIPASS, 'rrc-drop-runner') if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(ROOT)
HARVEST = os.path.join(TOOLS, 'TXRRC_data_harvest')
W1 = os.path.join(TOOLS, 'w1-data-parser')

def extract(path, work, notes=None):
    """Unzip if needed; return list of member files."""
    with open(path, 'rb') as source:
        head = source.read(512).lstrip().lower()
    if head.startswith((b'<?xml', b'<!doctype html', b'<html')) and b'<html' in head:
        raise ValueError('This file is a saved web page (HTML), not RRC data. Re-download it with the file link on the RRC page, not "Save page as".')
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            base = os.path.realpath(work)
            members = []
            destinations = set()
            for member in z.infolist():
                target = os.path.realpath(os.path.join(work, member.filename))
                if os.path.commonpath([base, target]) != base:
                    raise ValueError('This ZIP contains an unsafe member path. Choose the original RRC download.')
                if not member.is_dir():
                    key = os.path.normcase(target)
                    if key in destinations:
                        raise ValueError('This ZIP contains multiple files with the same path. Choose the original RRC download.')
                    destinations.add(key)
                    members.append((member, target))
            z.extractall(work)
        files = []
        by_path = {os.path.normcase(p): (member, p) for member, p in members}
        skip = set()
        compressed_output = {}
        for member, p in members:
            if not p.lower().endswith('.gz'):
                continue
            other = by_path.get(os.path.normcase(p[:-3]))
            if not other:
                continue
            raw_member, raw_path = other
            import gzip
            with gzip.open(p, 'rb') as gz, open(raw_path, 'rb') as raw:
                while True:
                    a, b = gz.read(1 << 20), raw.read(1 << 20)
                    if a != b:
                        identical = False
                        break
                    if not a:
                        identical = True
                        break
            if identical:
                skip.add(p)
                if notes is not None: notes.append(f'{member.filename}: identical compressed copy skipped.')
            elif member.date_time > raw_member.date_time:
                skip.add(raw_path)
                compressed_output[p] = os.path.join(tempfile.mkdtemp(prefix='rrc-gzip-', dir=work), os.path.basename(raw_path))
                if notes is not None: notes.append(f'{member.filename}: selected the newer compressed version; the uncompressed version has different contents.')
            elif raw_member.date_time > member.date_time:
                skip.add(p)
                if notes is not None: notes.append(f'{raw_member.filename}: selected the newer uncompressed version; the compressed version has different contents.')
            else:
                raise ValueError(f'{member.filename} and {raw_member.filename} contain different data with the same timestamp. Extract the archive and choose the intended version.')
        # Walk only the original archive members. Walking the extraction tree
        # also visits newly unpacked nested archives a second time.
        for member, p in members:
            if p in skip:
                continue
            if zipfile.is_zipfile(p):
                files += extract(p, os.path.splitext(p)[0] + '_unzipped', notes)
            else:
                files += _gunzip(p, compressed_output.get(p))
        return _coalesce_disposition(files, notes)
    return _gunzip(path)

def _gunzip(p, destination=None):
    """RRC ships many files as .gz (e.g. orf850.ebc.gz, wlf607.ebc.gz); decompress so fixed-width parsers see raw records."""
    import gzip, shutil as _sh
    with open(p, 'rb') as fh: magic = fh.read(2)
    if magic != b'\x1f\x8b': return [p]
    dst = destination or (p[:-3] if p.lower().endswith('.gz') else p + '.raw')
    if os.path.exists(dst):
        # Many RRC archives contain both file and file.gz. Never overwrite the
        # original or count the same records twice, and do not silently discard
        # a compressed member whose contents differ.
        with gzip.open(p, 'rb') as src, open(dst, 'rb') as existing:
            while True:
                a, b = src.read(1 << 20), existing.read(1 << 20)
                if a != b:
                    raise ValueError(f'{os.path.basename(p)} and {os.path.basename(dst)} contain different data. Extract the archive and choose the intended file.')
                if not a: break
        return []
    with gzip.open(p, 'rb') as src, open(dst, 'wb') as d: _sh.copyfileobj(src, d, 1 << 20)
    return [dst]

def _coalesce_disposition(files, notes):
    """RRC's PR download can contain the same records in ASCII and EBCDIC."""
    names = {os.path.basename(p).lower(): p for p in files}
    known = {'gsf102', 'olf102', 'gsf102.ebc', 'olf102.ebc', 'record.counts'}
    if len(names) != len(files) or not set(names).issubset(known):
        return files
    pairs = [(names[n], names[n + '.ebc']) for n in ('gsf102', 'olf102') if n in names and n + '.ebc' in names]
    if not pairs:
        return files
    # No mixed archive is silently reduced unless every EBCDIC product has an
    # ASCII counterpart and all 200-byte records agree after EBCDIC decoding.
    if any(n in names and n[:-4] not in names for n in ('gsf102.ebc', 'olf102.ebc')):
        raise ValueError('This gas-disposition ZIP has mixed formats without matching copies. Extract it and choose the individual files.')
    translation = bytes(range(256)).decode('cp037').encode('latin-1')
    for ascii_path, ebc_path in pairs:
        with open(ascii_path, 'rb') as text, open(ebc_path, 'rb') as binary:
            for line in text:
                record = binary.read(200)
                if line.rstrip(b'\r\n') != record.translate(translation):
                    raise ValueError(f'{os.path.basename(ascii_path)} and its EBCDIC copy differ. Extract the archive and choose the intended version.')
            if binary.read(1):
                raise ValueError(f'{os.path.basename(ascii_path)} and its EBCDIC copy have different record counts.')
        if notes is not None:
            notes.append(f'{os.path.basename(ascii_path)}: matching EBCDIC copy checked and omitted; ASCII records retained.')
    omitted = {ebc for _, ebc in pairs}
    if 'record.counts' in names:
        omitted.add(names['record.counts'])
    return [p for p in files if p not in omitted]

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
    return p_pdq(files, out)

def p_pdq(files, out):
    """Stream each production-query table to CSV and SQLite in bounded batches."""
    from contextlib import closing
    counts = {}
    with closing(sqlite3.connect(os.path.join(out, 'data.sqlite'))) as db:
        for f in files:
            if f.lower().endswith(('.pdf', '.md', '.doc', '.docx')):
                continue
            name = safe(f)
            if name in counts:
                raise ValueError(f'Two input files have the same output table name: {name}.')
            with open(f, encoding='latin-1', newline='') as source, open(os.path.join(out, name + '.csv'), 'w', encoding='utf-8', newline='') as dest:
                first = source.readline()
                if not first:
                    continue
                try:
                    sep = '}' if '}' in first else csv.Sniffer().sniff(first).delimiter
                except csv.Error:
                    raise ValueError(f'{os.path.basename(f)}: could not identify the column separator.')
                source.seek(0)
                # PDQ DSV uses literal quotes in data; ordinary CSV uses CSV quoting.
                quoting = csv.QUOTE_NONE if f.lower().endswith('.dsv') and sep == '}' else csv.QUOTE_MINIMAL
                reader = csv.reader(source, delimiter=sep, quoting=quoting)
                columns = next(reader, [])
                if not columns or len({c.casefold() for c in columns}) != len(columns) or any(not c for c in columns):
                    raise ValueError(f'{os.path.basename(f)}: missing or duplicate column headings.')
                quote = lambda value: '"' + value.replace('"', '""') + '"'
                db.execute(f'CREATE TABLE {quote(name)} (' + ', '.join(quote(c) + ' TEXT' for c in columns) + ')')
                insert = f'INSERT INTO {quote(name)} VALUES (' + ','.join('?' for _ in columns) + ')'
                writer = csv.writer(dest)
                writer.writerow(columns)
                count = 0
                batch = []
                for row in reader:
                    if not row: continue
                    if len(row) > len(columns):
                        if any(value != '' for value in row[len(columns):]):
                            raise ValueError(f'{os.path.basename(f)}, line {reader.line_num}: extra nonempty fields.')
                        row = row[:len(columns)]
                    row += [''] * (len(columns) - len(row))
                    writer.writerow(row)
                    batch.append(row)
                    count += 1
                    if len(batch) >= 5000:
                        db.executemany(insert, batch)
                        batch.clear()
                if batch: db.executemany(insert, batch)
                db.commit()
                counts[name] = count
    return counts, None

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
    counts = {}
    quote = lambda value: '"' + value.replace('"', '""') + '"'
    db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
    try:
        for f in files:
            if not f.lower().endswith('.dbf'): continue
            name = safe(f)
            if name in counts: raise ValueError(f'Two dBase files have the same output table name: {name}.')
            with open(f, 'rb') as source:
                reader = shapefile.Reader(dbf=source)
                try:
                    cols = [x[0] for x in reader.fields[1:]]
                    db.execute(f'CREATE TABLE {quote(name)} (' + ', '.join(quote(c) + ' TEXT' for c in cols) + ')')
                    insert = f'INSERT INTO {quote(name)} VALUES (' + ','.join('?' for _ in cols) + ')'
                    count, batch = 0, []
                    with open(os.path.join(out, name + '.csv'), 'w', encoding='utf-8', newline='') as dest:
                        writer = csv.writer(dest); writer.writerow(cols)
                        for row in reader.iterRecords():
                            writer.writerow(row); batch.append([None if v is None else str(v) for v in row]); count += 1
                            if len(batch) >= 5000:
                                db.executemany(insert, batch); batch.clear()
                    if batch: db.executemany(insert, batch)
                    counts[name] = count
                finally:
                    reader.close()
        db.commit()
    finally:
        db.close()
    return counts, None

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
    with open(path, 'rb') as source:
        b = source.read(2_000_000)
    sc = {}
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
    tables = {}
    quote = lambda value: '"' + value.replace('"', '""') + '"'
    db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
    try:
        for f in files:
            with open(f, 'rb') as fh:
                api = None
                for block in yield_blocks(fh, 247):
                    if len(block) != 247:
                        raise ValueError(f'{os.path.basename(f)} ends with an incomplete wellbore record.')
                    sv = pic_any(block[0:2])
                    if sv == '01': api = '42' + pic_any(block[2:10])
                    lay = dbf900_layout(sv)
                    if not lay: continue
                    values = parse_record(block, lay['layout']); values['API'] = api
                    name = f'rec{sv}'
                    if name not in tables:
                        columns = list(values)
                        db.execute(f'CREATE TABLE {quote(name)} (' + ', '.join(quote(c) + ' TEXT' for c in columns) + ')')
                        dest = open(os.path.join(out, name + '.csv'), 'w', encoding='utf-8', newline='')
                        writer = csv.writer(dest); writer.writerow(columns)
                        tables[name] = dict(dest=dest, writer=writer, columns=columns, batch=[], count=0,
                                            insert=f'INSERT INTO {quote(name)} VALUES (' + ','.join('?' for _ in columns) + ')')
                    table = tables[name]; row = [values.get(c) for c in table['columns']]
                    table['writer'].writerow(row); table['batch'].append([None if v is None else str(v) for v in row]); table['count'] += 1
                    if len(table['batch']) >= 5000:
                        db.executemany(table['insert'], table['batch']); table['batch'].clear()
        for table in tables.values():
            if table['batch']: db.executemany(table['insert'], table['batch'])
        db.commit()
    finally:
        for table in tables.values(): table['dest'].close()
        db.close()
    return {name: table['count'] for name, table in tables.items()}, None

W1_JS = r"""
const {W1Parser}=require(process.argv[2]);
(async()=>{const fs=require('fs');const o=fs.openSync(process.argv[4],'w');
try { for await(const x of new W1Parser().iterateFile(process.argv[3],undefined,true)) fs.writeSync(o,JSON.stringify(x)+'\n'); }
finally { fs.closeSync(o); }})().catch(e=>{console.error(e);process.exit(1)});
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
    ndjson = []
    for f in files:
        nd = os.path.join(out, safe(f) + '.ndjson')
        if any(nd == existing for existing, _ in ndjson):
            raise ValueError(f'Multiple W-1 input files would produce the same output name: {os.path.basename(f)}')
        subprocess.run([node, js, os.path.join(W1, 'dist', 'index.js'), f, nd], check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        ndjson.append((nd, os.path.basename(f)))
    def rows():
        group_offset = 0
        for nd, filename in ndjson:
            groups = 0
            with open(nd, encoding='utf-8') as source:
                for gi, line in enumerate(source):
                    groups += 1
                    group = json.loads(line)
                    for seg, val in group.items():
                        for value in (val if isinstance(val, list) else [val]):
                            if isinstance(value, dict):
                                row = {'group': group_offset + gi}
                                if len(ndjson) > 1: row['source_file'] = filename
                                row.update({k: (json.dumps(x) if isinstance(x, (dict, list)) else x) for k, x in value.items()})
                                yield f'seg{seg}', row
            group_offset += groups
    columns = {}
    for name, row in rows():
        known = columns.setdefault(name, [])
        for key in row:
            if key not in known: known.append(key)
    tables = {}
    quote = lambda value: '"' + value.replace('"', '""') + '"'
    db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
    try:
        for name, cols in columns.items():
            db.execute(f'CREATE TABLE {quote(name)} (' + ', '.join(quote(c) + ' TEXT' for c in cols) + ')')
            dest = open(os.path.join(out, name + '.csv'), 'w', encoding='utf-8', newline='')
            writer = csv.writer(dest); writer.writerow(cols)
            tables[name] = dict(dest=dest, writer=writer, cols=cols, batch=[], count=0,
                                insert=f'INSERT INTO {quote(name)} VALUES (' + ','.join('?' for _ in cols) + ')')
        for name, row in rows():
            table = tables[name]; values = [row.get(c, '') for c in table['cols']]
            table['writer'].writerow(values); table['batch'].append([str(v) for v in values]); table['count'] += 1
            if len(table['batch']) >= 5000:
                db.executemany(table['insert'], table['batch']); table['batch'].clear()
        for table in tables.values():
            if table['batch']: db.executemany(table['insert'], table['batch'])
        db.commit()
    finally:
        for table in tables.values(): table['dest'].close()
        db.close()
    return {name: table['count'] for name, table in tables.items()}, 'Grouped JSON also saved as .ndjson'

MASTER_JS = r"""
const fs=require('fs'), readline=require('readline');
const {W1Parser}=require(process.argv[1]);
const parser=new W1Parser();
(async()=>{
  for(const filename of process.argv.slice(2)) {
    for await(const line of readline.createInterface({input:fs.createReadStream(filename,{encoding:'latin1'}),crlfDelay:Infinity})) {
      if(!line.trim()) continue;
      if(!line.startsWith('02') || line.length < 500) throw new Error('Unexpected drilling-permit master record in '+filename);
      const record=parser._parseDaPermit(line); parser._applyTransformations(record);
      if(!process.stdout.write(JSON.stringify(record)+'\n')) await new Promise(resolve=>process.stdout.once('drain',resolve));
    }
  }
})().catch(e=>{console.error(e);process.exit(1)});
"""

def p_drilling_master(files, out):
    """Use the existing W-1 permit schema for the standalone DAF804 master."""
    with open(files[0], 'rb') as source:
        head = source.read(512)
    if not head.startswith(b'02'):
        return p_w1(files, out)
    node = os.path.join(TOOLS, 'runtime', 'node.exe')
    if not os.path.isfile(node):
        if getattr(sys, 'frozen', False):
            raise ValueError('The bundled W-1 runtime is missing. Extract the complete application ZIP again.')
        from shutil import which
        node = which('node')
        if not node: raise ValueError('Node is required for source execution. Use the Windows release for a bundled runtime.')
    parser = os.path.join(W1, 'dist', 'index.js')
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
    dest = None
    proc = None
    count, batch = 0, []
    try:
        with tempfile.TemporaryFile(mode='w+t', encoding='utf-8') as errors:
            proc = subprocess.Popen([node, '-e', MASTER_JS, parser, *files], stdout=subprocess.PIPE,
                                    stderr=errors, text=True, encoding='utf-8', creationflags=flags)
            for line in proc.stdout:
                record = json.loads(line)
                if dest is None:
                    columns = list(record)
                    quote = lambda value: '"' + value.replace('"', '""') + '"'
                    db.execute('CREATE TABLE drilling_permits (' + ', '.join(quote(c) + ' TEXT' for c in columns) + ')')
                    insert = 'INSERT INTO drilling_permits VALUES (' + ','.join('?' for _ in columns) + ')'
                    dest = open(os.path.join(out, 'drilling_permits.csv'), 'w', encoding='utf-8', newline='')
                    writer = csv.writer(dest)
                    writer.writerow(columns)
                row = [record.get(c, '') for c in columns]
                writer.writerow(row)
                batch.append([None if v is None else str(v) for v in row])
                count += 1
                if len(batch) >= 5000:
                    db.executemany(insert, batch)
                    batch.clear()
            code = proc.wait()
            if code:
                errors.seek(0)
                raise ValueError('Could not parse the drilling-permit master: ' + errors.read()[-1000:])
        if batch: db.executemany(insert, batch)
        db.commit()
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait()
        if proc and proc.stdout: proc.stdout.close()
        if dest: dest.close()
        db.close()
    return ({'drilling_permits': count} if count else {}), 'Standalone permit records parsed with the bundled W-1 schema.'

def route(ds):
    if ds.get('slug','').startswith('drilling_permits_pending'):
        from pending_permits import p_pending
        return 'wired:unverified', lambda files, out: p_pending(files, out, save, pd, os)
    s, fmts = ds['slug'], ' '.join(ds['formats']).lower()
    if s == 'production_data_query_dump': return 'wired', p_pdq
    if s == 'drilling_permit_master': return 'wired', p_drilling_master
    if s in ('p5_organization', 'p5_organization_2'): return 'wired', p_p5_bundle
    if s in ('uic_database', 'uic_database_2'): return 'wired', p_uic_bundle
    if s in ('full_wellbore', 'full_wellbore_2'): return 'wired', p_wellbore_bundle
    if s in IMAGE_SLUGS: return 'wired:image-unpack', p_images
    if s in RETIRED: return 'retired', p_retired
    if s == 'statewide_api_data':
        from api_compressed import p_api_compressed
        return 'wired', lambda f, o: p_api_compressed(f, o, save, pd, os)
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
    tables, unknown = {}, 0
    quote = lambda value: '"' + value.replace('"', '""') + '"'
    db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
    try:
        for f in files:
            with open(f, encoding='latin-1', errors='ignore') as source:
                for line in source:
                    line = line.rstrip('\r\n')
                    if not line.strip(): continue
                    layout = P5.get(line[:2])
                    if not layout:
                        unknown += 1
                        continue
                    name, fields = layout
                    values = {n: line[s-1:s-1+l].strip() for n, s, l in fields}
                    if name not in tables:
                        columns = list(values)
                        db.execute(f'CREATE TABLE {quote(name)} (' + ', '.join(quote(c) + ' TEXT' for c in columns) + ')')
                        dest = open(os.path.join(out, name + '.csv'), 'w', encoding='utf-8', newline='')
                        writer = csv.writer(dest); writer.writerow(columns)
                        tables[name] = dict(dest=dest, writer=writer, columns=columns, batch=[], count=0,
                                            insert=f'INSERT INTO {quote(name)} VALUES (' + ','.join('?' for _ in columns) + ')')
                    table = tables[name]
                    row = [values.get(c, '') for c in table['columns']]
                    table['writer'].writerow(row); table['batch'].append(row); table['count'] += 1
                    if len(table['batch']) >= 5000:
                        db.executemany(table['insert'], table['batch']); table['batch'].clear()
        for table in tables.values():
            if table['batch']: db.executemany(table['insert'], table['batch'])
        db.commit()
    finally:
        for table in tables.values(): table['dest'].close()
        db.close()
    note = f'{unknown} lines had an unknown record id' if unknown else None
    return {name: table['count'] for name, table in tables.items()}, note

def p_p5_bundle(files, out):
    names = {os.path.basename(p).lower(): p for p in files}
    if len(names) != len(files): raise ValueError('This archive contains same-named P-5 files in different folders. Choose the intended files separately.')
    if set(names) != {'orf850.ebc', 'orf850.txt'}:
        if all(name.endswith('.ebc') for name in names): return p_ebcdic('p5_organization')(files, out)
        if all(name.endswith('.txt') for name in names): return p_p5_ascii(files, out)
        raise ValueError('Choose the original P-5 ASCII or EBCDIC file, or an archive containing both.')
    return _combine_variants([('ascii', names['orf850.txt'], p_p5_ascii),
                              ('ebcdic', names['orf850.ebc'], p_ebcdic('p5_organization'))], out, 'P-5')

def p_uic_bundle(files, out):
    names = {os.path.basename(p).lower(): p for p in files}
    if len(names) != len(files): raise ValueError('This archive contains same-named UIC files in different folders. Choose the intended files separately.')
    data = {'uif700.ebc', 'uif700a.txt'}
    support = {'uif700a.readme.txt', 'uif700a.uimnh10_layout', 'uif700a.uimnh10h_layout', 'uiw700l2.txt'}
    if data.issubset(names) and set(names).issubset(data | support):
        return _combine_variants([('ascii', names['uif700a.txt'], p_fixed('uic_database_2')),
                                  ('ebcdic', names['uif700.ebc'], p_ebcdic('uic_database'))], out, 'UIC')
    if len(files) == 1 and next(iter(names)).endswith('.ebc'): return p_ebcdic('uic_database')(files, out)
    if len(files) == 1 and next(iter(names)).endswith('.txt'): return p_fixed('uic_database_2')(files, out)
    raise ValueError('Choose the original UIC ASCII or EBCDIC file, or an archive containing both.')

def p_wellbore_bundle(files, out):
    names = {os.path.basename(p).lower(): p for p in files}
    if len(names) != len(files): raise ValueError('This archive contains same-named Full Wellbore files in different folders. Choose the intended files separately.')
    if set(names) == {'dbf900.ebc', 'dbf900.txt'}:
        return _combine_variants([('ascii', names['dbf900.txt'], p_fixed('full_wellbore_2')),
                                  ('ebcdic', names['dbf900.ebc'], p_wellbore_ebcdic)], out, 'Full Wellbore')
    if len(files) == 1 and next(iter(names)).endswith('.ebc'): return p_wellbore_ebcdic(files, out)
    if len(files) == 1 and next(iter(names)).endswith('.txt'): return p_fixed('full_wellbore_2')(files, out)
    raise ValueError('Choose the original Full Wellbore ASCII or EBCDIC file, or an archive containing both.')

def _combine_variants(variants, out, label):
    import shutil
    counts, notes = {}, []
    quote = lambda value: '"' + value.replace('"', '""') + '"'
    db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
    try:
        with tempfile.TemporaryDirectory(prefix='p5-variants-', dir=out) as folder:
            for prefix, path, convert in variants:
                variant = os.path.join(folder, prefix); os.mkdir(variant)
                subcounts, subnote = convert([path], variant)
                db.execute('ATTACH DATABASE ? AS source_db', (os.path.join(variant, 'data.sqlite'),))
                for name, count in subcounts.items():
                    dest = prefix + '_' + name
                    db.execute(f'CREATE TABLE {quote(dest)} AS SELECT * FROM source_db.{quote(name)}')
                    shutil.move(os.path.join(variant, name + '.csv'), os.path.join(out, dest + '.csv'))
                    counts[dest] = count
                db.commit(); db.execute('DETACH DATABASE source_db')
                if subnote: notes.append(prefix + ': ' + subnote)
    finally:
        db.close()
    totals = {prefix: sum(count for name, count in counts.items() if name.startswith(prefix + '_'))
              for prefix, _, _ in variants}
    detail = ' + '.join(f'{total:,} {prefix.upper()} rows' for prefix, total in totals.items())
    return counts, f'Both supplied {label} formats are kept in separately named tables: {detail}. These are output rows, not a count of unique records. ' + ' '.join(notes)

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
def _layout(slug):
    with open(os.path.join(ROOT, 'layouts', slug + '.json')) as source:
        return json.load(source)

def _pick(spec, fname):
    up = os.path.basename(fname).upper()
    for k, v in spec.get('by_filename', {}).items():
        if k and k in up: return v
    return spec.get('by_filename', {}).get('')

def p_fixed(slug):
    spec = _layout(slug)
    def run(files, out):
        tables, unk = {}, {}
        quote = lambda value: '"' + value.replace('"', '""') + '"'
        db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
        try:
            for f in files:
                if f.lower().endswith(('.pdf', '.doc', '.docx')): continue
                default = _pick(spec, f) if 'by_filename' in spec else ''
                with open(f, 'r', encoding='latin-1', errors='ignore', newline='') as fh:
                    for i, line in enumerate(fh):
                        line = line.rstrip('\r\n')
                        if not line.strip(): continue
                        if spec.get('skip_line_prefix') and line.startswith(spec['skip_line_prefix']): continue
                        if i == 0 and spec.get('first_record'): key = spec['first_record']
                        elif spec['id_len']: key = line[:spec['id_len']]
                        else: key = default
                        rec = spec['records'].get(key)
                        if not rec: unk[key] = unk.get(key, 0) + 1; continue
                        name = rec['table']
                        values = {n: line[s:s+l].strip() for n, s, l in rec['fields']}
                        if name not in tables:
                            columns = list(values)
                            db.execute(f'CREATE TABLE {quote(name)} (' + ', '.join(quote(c) + ' TEXT' for c in columns) + ')')
                            dest = open(os.path.join(out, name + '.csv'), 'w', encoding='utf-8', newline='')
                            writer = csv.writer(dest); writer.writerow(columns)
                            tables[name] = dict(dest=dest, writer=writer, columns=columns, batch=[], count=0,
                                                insert=f'INSERT INTO {quote(name)} VALUES (' + ','.join('?' for _ in columns) + ')')
                        table = tables[name]; row = [values.get(c, '') for c in table['columns']]
                        table['writer'].writerow(row); table['batch'].append(row); table['count'] += 1
                        if len(table['batch']) >= 5000:
                            db.executemany(table['insert'], table['batch']); table['batch'].clear()
            for table in tables.values():
                if table['batch']: db.executemany(table['insert'], table['batch'])
            db.commit()
        finally:
            for table in tables.values(): table['dest'].close()
            db.close()
        note = f"Layout from manuals/{spec['manual']}."
        if unk: note += ' Unknown record ids skipped: ' + ', '.join(f'{k!r}×{v}' for k, v in unk.items())
        return {name: table['count'] for name, table in tables.items()}, note
    return run

def p_delim(slug):
    spec = _layout(slug)
    def run(files, out):
        plans, widths, notes = [], {}, []
        for f in files:
            with open(f, 'rb') as source:
                raw = source.read(4096)
            if f.lower().endswith('.dmp') or b'EXPORT:V' in raw[:64]:
                notes.append(f'{os.path.basename(f)} is an Oracle export (.dmp); open it with Oracle imp/impdp, then export the tables as text and drop them here.'); continue
            text = raw.decode('latin-1')
            d = spec['delim']
            if d == 'auto': d = max(['}', '|', '\t', ','], key=lambda x: text.count(x))
            tabs = spec['tables']
            name = _pick(spec, f) if 'by_filename' in spec else next(iter(tabs))
            with open(f, 'r', encoding='latin-1', errors='ignore', newline='') as fh:
                rd = csv.reader(fh, delimiter=d) if spec.get('csv_quoting') else (l.rstrip('\r\n').split(d) for l in fh)
                first = None; width = 0
                for row in rd:
                    if not any(x.strip() for x in row): continue
                    row = [x.strip() for x in row]
                    if first is None: first = row
                    width = max(width, len(row))
            if first is None: continue
            if spec.get('by_count'):
                n = len(first); m = [k for k, v in tabs.items() if len(v) == n]
                if m and (name is None or len(tabs[name]) != n): name = m[0]
            if name not in tabs:
                raise ValueError(f'{os.path.basename(f)} does not match a known {slug} table.')
            cols = tabs[name]
            plans.append((f, d, name, [x.lower() for x in first][:3] == cols[:3]))
            widths[name] = max(widths.get(name, 0), width)
        counts, outputs = {}, {}
        quote = lambda value: '"' + value.replace('"', '""') + '"'
        db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
        try:
            for name, width in widths.items():
                base = spec['tables'][name]
                cols = [base[j] if j < len(base) else f'extra_{j+1}' for j in range(width)]
                db.execute(f'CREATE TABLE {quote(name)} (' + ', '.join(quote(c) + ' TEXT' for c in cols) + ')')
                dest = open(os.path.join(out, name + '.csv'), 'w', encoding='utf-8', newline='')
                writer = csv.writer(dest); writer.writerow(cols)
                outputs[name] = dict(dest=dest, writer=writer, batch=[], count=0, width=width,
                                     insert=f'INSERT INTO {quote(name)} VALUES (' + ','.join('?' for _ in cols) + ')')
            for f, d, name, skip_header in plans:
                state = outputs[name]
                with open(f, 'r', encoding='latin-1', errors='ignore', newline='') as fh:
                    rd = csv.reader(fh, delimiter=d) if spec.get('csv_quoting') else (l.rstrip('\r\n').split(d) for l in fh)
                    for row in rd:
                        if not any(x.strip() for x in row): continue
                        if skip_header:
                            skip_header = False
                            continue
                        row = [x.strip() for x in row]
                        row += [''] * (state['width'] - len(row))
                        state['writer'].writerow(row); state['batch'].append(row); state['count'] += 1
                        if len(state['batch']) >= 5000:
                            db.executemany(state['insert'], state['batch']); state['batch'].clear()
            for name, state in outputs.items():
                if state['batch']: db.executemany(state['insert'], state['batch'])
                counts[name] = state['count']
            db.commit()
        finally:
            for state in outputs.values(): state['dest'].close()
            db.close()
        notes.insert(0, f"Columns from manuals/{spec['manual']}.")
        return counts, ' '.join(notes)
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
        # Keep the source width for unsigned integer fields. RRC uses these
        # fields for identifiers as well as quantities, so converting them to
        # int silently removes significant leading zeroes from identifiers.
        if s.isdigit(): return int(s) / 10**dec if dec else s
        return s or None
    except Exception:
        return b.hex()

def p_ebcdic(slug):
    spec = _layout(slug)
    return lambda files, out: _stream_ebcdic(files, out, spec)

def _stream_ebcdic(files, out, spec):
    """Convert historical ledger records without keeping the dataset in RAM."""
    helpers = _ebc_helpers()
    length = spec['reclen']
    start, width = spec['id_pos']
    unknown, notes, tables = {}, [], {}
    quote = lambda value: '"' + value.replace('"', '""') + '"'
    db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
    try:
        for f in files:
            if not os.path.getsize(f):
                continue
            fixed = _pick(spec, f) if 'by_filename' in spec else ''
            with open(f, 'rb') as source:
                while True:
                    record = source.read(length)
                    if not record: break
                    if len(record) != length:
                        notes.append(f'{os.path.basename(f)}: {len(record)} trailing bytes ignored (size not a multiple of {length})')
                        break
                    key = helpers[2](record[start:start+width]) if width else fixed
                    layout = spec['records'].get(key)
                    if not layout:
                        unknown[key] = unknown.get(key, 0) + 1
                        continue
                    name = layout['table']
                    values = {fn: _decode(record[s:s+l], typ, dec, fn, helpers) for fn, s, l, typ, dec in layout['fields']}
                    if name not in tables:
                        columns = list(values)
                        db.execute(f'CREATE TABLE {quote(name)} (' + ', '.join(quote(c) + ' TEXT' for c in columns) + ')')
                        dest = open(os.path.join(out, name + '.csv'), 'w', encoding='utf-8', newline='')
                        writer = csv.writer(dest)
                        writer.writerow(columns)
                        tables[name] = dict(dest=dest, writer=writer, columns=columns, batch=[], count=0,
                                            insert=f'INSERT INTO {quote(name)} VALUES (' + ','.join('?' for _ in columns) + ')')
                    table = tables[name]
                    row = [values.get(c) for c in table['columns']]
                    table['writer'].writerow(row)
                    table['batch'].append([None if v is None else str(v) for v in row])
                    table['count'] += 1
                    if len(table['batch']) >= 5000:
                        db.executemany(table['insert'], table['batch'])
                        table['batch'].clear()
        for table in tables.values():
            if table['batch']: db.executemany(table['insert'], table['batch'])
        db.commit()
    finally:
        for table in tables.values(): table['dest'].close()
        db.close()
    note = f"Layout from manuals/{spec['manual']}."
    if unknown: note += ' Unknown record ids skipped: ' + ', '.join(f'{k!r}x{v}' for k, v in list(unknown.items())[:10])
    return {name: table['count'] for name, table in tables.items()}, ' '.join([note] + notes)

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
