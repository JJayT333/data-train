"""Statewide API ASCII (MAF016) as RRC actually ships it: PIC X fields that are blank are
left out of the record and everything after shifts left. PIC 9 fields are always present.
We rebuild each record by trying 'present/absent' for every X field and keeping the split
where every numeric field holds digits/spaces and the record ends in blanks."""
import re
FIELDS = [('quad_num', 7, '9'), ('api_num', 8, '9'), ('_sep', 1, 's'), ('survey', 55, 'X'), ('block', 10, 'X'),
          ('section', 8, 'X'), ('abstract', 6, 'X'), ('operator', 32, 'X'), ('total_depth', 5, '9'),
          ('well_number', 6, 'X'), ('lease_name', 32, 'X'), ('permit_num', 6, '9'), ('gas_rrcid', 6, '9'), ('oil_lease_num', 6, '9'),
          ('field_name', 32, 'X'), ('completion_date', 8, '9'), ('plug_date', 8, '9'), ('refer_to_api', 8, '9'),
          ('on_off_schedule', 1, 'X'), ('oil_gas_code', 1, 'X')]
NUM = re.compile(r'^(\d[\d ]*|\s*)$')

def parse_line(line, cap=20000):
    sols = []
    def go(i, pos, acc):
        if len(sols) >= cap: return
        if i == len(FIELDS):
            if not line[pos:].strip(): sols.append(dict(acc))
            return
        name, n, t = FIELDS[i]; seg = line[pos:pos+n]
        if t == 's': go(i + 1, pos + n, acc); return
        if t == '9':
            if len(seg) == n and NUM.match(seg): acc[name] = seg.strip(); go(i + 1, pos + n, acc)
            return
        if n == 1:
            if seg.isalpha(): acc[name] = seg; go(i + 1, pos + 1, acc)
            acc[name] = ''; go(i + 1, pos, acc); return
        if len(seg) == n and seg.strip():
            acc[name] = seg.strip(); acc['_split_' + name] = int(seg[-1] != ' ' and line[pos+n:pos+n+1] not in ('', ' ')) + int(pos > 0 and line[pos-1] != ' ' and seg[0] != ' ' and FIELDS[i-1][2] == 'X'); go(i + 1, pos + n, acc)
            acc.pop('_split_' + name, None)
        acc[name] = ''; go(i + 1, pos, acc)
    go(0, 0, {})
    if not sols: return None
    def score(r):
        gaps = sum(1 for k, v in r.items() if FIELDS_T.get(k) == 'X' and re.search(r'\S\s{3,}\S', v))
        lead = sum(1 for k, v in r.items() if FIELDS_T.get(k) == 'X' and v and re.match(r'^\d+$', v) and k in ('operator', 'lease_name', 'field_name', 'survey'))
        absent = sum(1 for k, v in r.items() if FIELDS_T.get(k) == 'X' and not v)
        splits = sum(v for k, v in r.items() if k.startswith('_split_'))
        gaps += sum(1 for k, v in r.items() if FIELDS_T.get(k) == 'X' and re.search(r'\s{2,}\d+$', v))
        return (splits + gaps, lead, absent)
    return min(sols, key=score)

FIELDS_T = {n: t for n, _, t in FIELDS}

def p_api_compressed(files, out, save, pd, os):
    import csv, sqlite3
    db = sqlite3.connect(os.path.join(out, 'data.sqlite'))
    tables = {}
    columns = [name for name, _, _ in FIELDS if not name.startswith('_')]
    def write(table, names, row):
        if table not in tables:
            quoted = ['"' + name.replace('"', '""') + '"' for name in names]
            db.execute(f'CREATE TABLE "{table}" (' + ', '.join(name + ' TEXT' for name in quoted) + ')')
            dest = open(os.path.join(out, table + '.csv'), 'w', encoding='utf-8', newline='')
            writer = csv.writer(dest); writer.writerow(names)
            tables[table] = dict(dest=dest, writer=writer, rows=[], count=0,
                                 insert=f'INSERT INTO "{table}" VALUES (' + ','.join('?' for _ in names) + ')')
        state = tables[table]
        state['writer'].writerow(row); state['rows'].append([None if v is None else str(v) for v in row]); state['count'] += 1
        if len(state['rows']) >= 5000:
            db.executemany(state['insert'], state['rows']); state['rows'].clear()
    try:
        for f in files:
            with open(f, encoding='latin-1', errors='ignore') as source:
                for ln, line in enumerate(source, start=1):
                    line = line.rstrip('\r\n')
                    if not line.strip(): continue
                    record = parse_line(line)
                    if record is None:
                        write('unparsed_lines', ['file', 'line_no', 'raw'], [os.path.basename(f), ln, line])
                    else:
                        write('api_quad_records', columns, [record.get(name, '') for name in columns])
        for state in tables.values():
            if state['rows']: db.executemany(state['insert'], state['rows'])
        db.commit()
    finally:
        for state in tables.values(): state['dest'].close()
        db.close()
    counts = {name: state['count'] for name, state in tables.items()}
    return counts, f"Compressed MAF016 layout (blank text fields omitted). {counts.get('unparsed_lines', 0)} lines could not be split and are in unparsed_lines."
