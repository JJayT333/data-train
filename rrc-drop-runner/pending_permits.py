"""Drilling Permits Pending Approval (+lat/long): 11 '}'-delimited files, column order from
manual v2.2 section 4.0. NOT yet verified on a real RRC file (none available) - rows whose
field count differs from the manual are kept raw in <table>_mismatch so nothing is silently lost."""
import json, os, re
LAY = json.load(open(os.path.join(os.path.dirname(__file__), 'layouts', 'pending_permits_multi.json')))

def p_pending(files, out, save, pd, os_):
    t, notes = {}, []
    names = sorted(LAY['files'], key=len, reverse=True)
    for f in files:
        b = os.path.basename(f).lower()
        tab = next((n for n in names if b.startswith(n)), None)
        if not tab: notes.append(f'skipped {b} (not a dp_*_pending file)'); continue
        cols = LAY['files'][tab]; good, bad = [], []
        for ln, line in enumerate(open(f, encoding='latin-1', errors='ignore')):
            line = line.rstrip('\r\n')
            if not line.strip(): continue
            parts = line.split('}')
            if len(parts) == len(cols) + 1 and not parts[-1].strip(): parts = parts[:-1]
            if ln == 0 and [p.strip().upper() for p in parts] == cols: continue  # header row
            if len(parts) == len(cols): good.append(dict(zip(cols, (p.strip() for p in parts))))
            else: bad.append({'line_no': ln + 1, 'n_fields': len(parts), 'expected': len(cols), 'raw': line})
        t[tab] = pd.concat([t[tab], pd.DataFrame(good, columns=cols)]) if tab in t else pd.DataFrame(good, columns=cols)
        if bad: t[tab + '_mismatch'] = pd.DataFrame(bad); notes.append(f'{tab}: {len(bad)} lines had a field count different from the manual')
    if not t: raise ValueError('No dp_*_pending_*.txt files found. Expected files like dp_drilling_permit_pending_yyyymmddhhmmss.txt (if you got an .html file, the download link saved a web page instead of data).')
    return save(t, out), 'Pending permits: column order from manual v2.2 (unverified against a real file). ' + '; '.join(notes)
