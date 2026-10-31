"""Drilling permits pending approval: preserve RRC's supplied column headings."""
import csv, json, os, sys

ROOT = os.path.join(sys._MEIPASS, 'rrc-drop-runner') if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
LAY = json.load(open(os.path.join(ROOT, 'layouts', 'pending_permits_multi.json')))

def p_pending(files, out, save, pd, os_):
    t, notes = {}, []
    names = sorted(LAY['files'], key=len, reverse=True)
    for f in files:
        b = os.path.basename(f).lower()
        tab = next((n for n in names if b.startswith(n)), None)
        if not tab: notes.append(f'skipped {b} (not a dp_*_pending file)'); continue
        cols = LAY['files'][tab]; good, bad = [], []
        with open(f, encoding='latin-1', errors='ignore') as source:
            lines = enumerate(source, start=1)
            first = next(lines, None)
            if first is None:
                continue
            first_no, first_text = first
            header = first_text.rstrip('\r\n')
            if [p.strip().upper() for p in header.split('}')[:3]] == cols[:3]:
                # Some RRC headings span multiple physical lines, even in the
                # middle of a column name. The final name is stable per table.
                def headings(value):
                    parts = [p.strip() for p in value.split('}')]
                    if parts and not parts[-1]: parts.pop()
                    return parts
                while not headings(header) or headings(header)[-1].upper() != cols[-1]:
                    continuation = next(lines, None)
                    if continuation is None or not continuation[1].strip():
                        raise ValueError(f'{b}: incomplete column headings in the original file.')
                    header += continuation[1].rstrip('\r\n')
                cols = headings(header)
                if not all(cols) or len(set(cols)) != len(cols):
                    raise ValueError(f'{b}: invalid or duplicate column headings.')
            else:
                from itertools import chain
                lines = chain([first], lines)
            for ln, line in lines:
                line = line.rstrip('\r\n')
                if not line.strip(): continue
                try:
                    parts = next(csv.reader([line], delimiter='}', skipinitialspace=True, strict=True))
                except csv.Error as exc:
                    bad.append({'file': b, 'line_no': ln, 'n_fields': None, 'expected': len(cols),
                                'raw': line, 'parse_error': str(exc)})
                    continue
                if len(parts) == len(cols) + 1 and not parts[-1].strip(): parts = parts[:-1]
                if len(parts) == len(cols): good.append(dict(zip(cols, parts)))
                else: bad.append({'file': b, 'line_no': ln, 'n_fields': len(parts), 'expected': len(cols), 'raw': line})
        t[tab] = pd.concat([t[tab], pd.DataFrame(good, columns=cols)]) if tab in t else pd.DataFrame(good, columns=cols)
        if bad:
            key = tab + '_mismatch'
            t[key] = pd.concat([t[key], pd.DataFrame(bad)]) if key in t else pd.DataFrame(bad)
            notes.append(f'{b}: {len(bad)} lines had a field count different from the file headings')
    if not t: raise ValueError('No dp_*_pending_*.txt files found. Expected files like dp_drilling_permit_pending_yyyymmddhhmmss.txt (if you got an .html file, the download link saved a web page instead of data).')
    return save(t, out), 'Pending permits: original file headings used when supplied; otherwise manual v2.2. ' + '; '.join(notes)
