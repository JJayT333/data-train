"""Synthetic round-trip test for every layouts/*.json (ASCII fixed, delimited, EBCDIC)."""
import os, sys, json, tempfile, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); os.chdir(ROOT)
import pandas as pd
from parsers import p_fixed, p_delim, p_ebcdic, _layout
def enc_field(ty, l, d):
    if ty == 'X': return ('A' * l).encode('cp037')
    if ty == 'N': return ('0' * (l - 1) + '7').encode('cp037')
    if ty == 'S': return ('0' * (l - 1)).encode('cp037') + bytes([0xC7])
    return bytes(l - 1) + bytes([0x7C])  # packed +7
def expect(ty, d):
    return {'X': 'A', 'N': 7 / 10**d if d else 7, 'S': 7 / 10**d, 'P': 7 / 10**d if d else 7}[ty]
bad = 0
for f in sorted(glob.glob('layouts/*.json')):
    slug = os.path.basename(f)[:-5]; sp = _layout(slug); d = tempfile.mkdtemp(); o = tempfile.mkdtemp()
    if sp['kind'] != 'ebcdic': continue
    rl = sp['reclen']; a, n = sp['id_pos']; files = []; blob = b''
    for key, rec in sp['records'].items():
        b = bytearray(' '.encode('cp037') * rl)
        for fn, s, l, ty, dc in rec['fields']: b[s:s+l] = enc_field(ty, l, dc)
        if n: b[a:a+n] = key.encode('cp037')
        if 'by_filename' in sp:
            p = os.path.join(d, ('GSF102.ebc' if key == 'gas' else 'OLF102.ebc')); open(p, 'wb').write(bytes(b)); files.append(p)
        else: blob += bytes(b)
    if blob: p = os.path.join(d, 'in.ebc'); open(p, 'wb').write(blob); files = [p]
    counts, note = p_ebcdic(slug)(files, o)
    ok = len(counts) == len(sp['records']) and all(v == 1 for v in counts.values())
    # check one non-id field of each record decodes as expected
    for key, rec in sp['records'].items():
        fl = [x for x in rec['fields'] if not (n and x[1] < a + n)]
        if not fl: continue
        fn, s, l, ty, dc = fl[-1]
        e = 'A' * l if ty == 'X' else expect(ty, dc)
        df = pd.read_csv(os.path.join(o, rec['table'] + '.csv'))
        v = df[fn].iloc[0]
        if (str(v) != str(e)) and not (isinstance(e, (int, float)) and abs(float(v) - e) < 1e-9): ok = False; print('  mismatch', slug, rec['table'], fn, ty, v, e)
    bad += not ok; print('OK ' if ok else 'BAD', slug, sum(counts.values()), 'tables:', len(counts))
print('BAD', bad)
