"""Tiny COBOL copybook -> fixed-width layout extractor for RRC manuals (pdftotext -layout output)."""
import re
LINE = re.compile(r'^\s*(\d{2})\s+([A-Z0-9][A-Z0-9\-]*)(.*)$')
def pic_size(p):
    p = p.upper().replace('S', '')
    n = 0
    for ch, cnt in re.findall(r'([X9AZ])(?:\((\d+)\))?', p.split('V')[0] if False else p.replace('V', '')):
        n += int(cnt) if cnt else 1
    return n
def pic_dec(p):
    p = p.upper()
    if 'V' not in p: return 0
    t = p.split('V', 1)[1]; m = re.findall(r'9(?:\((\d+)\))?', t)
    return sum(int(x) if x else 1 for x in m)

def parse(text, ascii=False):
    """Returns list of records: {'name','fields':[(name,start0,len,dec,comp3)], 'ids':[values], 'length'}"""
    items = []
    buf = ''
    for raw in text.split('\n'):
        l = raw.split('*')[0] if raw.strip().startswith('*') else raw
        if not l.strip() or re.match(r'^\s*([IVX]+\.\d+|page\s+\S+|\d+-\d+|\d+)\s*$', l, re.I): continue
        m = LINE.match(l)
        l = re.sub(r'\)(VALUE|COMP)', r') \1', l)
        if buf.endswith('-') and not m:
            buf += l.strip(); continue
        if m:
            if buf: items.append(buf)
            buf = l.strip()
        elif buf and not buf.rstrip().endswith('.') and re.match(r'^\s+(PIC|VALUE|OCCURS|COMP|REDEFINES)', l):
            buf += ' ' + l.strip()
    if buf: items.append(buf)
    recs, stack = [], []
    def node(s):
        m = re.match(r'(\d{2})\s+([A-Z0-9\-]+)\s*(.*)', s)
        lvl, name, rest = int(m.group(1)), m.group(2), m.group(3)
        while True:
            mm = re.match(r'\s+([A-Z][A-Z0-9\-]*)(.*)', rest)
            if mm and mm.group(1) not in ('PIC', 'PICTURE', 'VALUE', 'OCCURS', 'REDEFINES', 'COMP', 'COMP-3', 'SPACE', 'TIMES') and not rest.strip().startswith('.'):
                name += '-' + mm.group(1); rest = mm.group(2)
            else: break
        pic = re.search(r'PIC(?:TURE)?\s+(?:IS\s+)?([SX9AVZ()\d]+)', rest)
        occ = re.search(r'OCCURS\s+(\d+)', rest)
        val = re.search(r"VALUE\s+(?:IS\s+)?'([^']*)'", rest) or re.search(r'VALUE\s+(?:IS\s+)?(\d+)', rest)
        return dict(lvl=lvl, name=name, pic=pic.group(1) if pic else None, occ=int(occ.group(1)) if occ else 1,
                    redef='REDEFINES' in rest, comp3='COMP-3' in rest or 'COMP3' in rest, val=val.group(1) if val else None, kids=[], pos=(int(re.search(r'\.?\s+(\d{1,4})\s*$', s).group(1)) if re.search(r'PIC.*\s(\d{1,4})\s*$', s) else None))
    root = None
    for s in items:
        if not re.match(r'\d{2}\s', s): continue
        n = node(s)
        if n['lvl'] == 88:
            if stack: stack[-1].setdefault('vals', []).append(n['val'])
            continue
        if n['lvl'] in (66, 77): continue
        if n['lvl'] == 1:
            root = n; recs.append(n); stack = [n]; continue
        if root is None: continue
        while stack and stack[-1]['lvl'] >= n['lvl']: stack.pop()
        if not stack: continue
        stack[-1]['kids'].append(n); stack.append(n)
    out = []
    for r in recs:
        fields = []; ids = []; mism = []
        def size(n):
            if n['pic']:
                s = pic_size(n['pic'])
                if n['comp3'] and not ascii: s = s // 2 + 1
                return s * n['occ']
            return sum(size(k) for k in n['kids'] if not k['redef']) * n['occ']
        def walk(n, off, suffix=''):
            for k in n['kids']:
                if k['redef']: continue
                one = size(k) // k['occ'] if k['occ'] else 0
                for i in range(k['occ']):
                    sfx = suffix + (f'_{i+1}' if k['occ'] > 1 else '')
                    if k['pic']:
                        if k['name'] != 'FILLER':
                            fields.append((k['name'] + sfx, off, one, pic_dec(k['pic']), k['comp3'], k['pic'], k['pos'] if not suffix and i == 0 else None))
                            if k['pos'] and i == 0 and not suffix and k['pos'] != off + 1: mism.append((k['name'], k['pos'], off + 1))
                        if k.get('vals') and off == 0: ids.extend(k['vals'])
                    else:
                        walk(k, off, sfx)
                    off += one
            return off
        length = walk(r, 0)
        if fields: out.append(dict(name=r['name'], fields=fields, ids=ids, length=length, mismatches=mism))
    return out

def parse_with_ids(text, ascii=False):
    """Parse each 01-level chunk separately and guess its record id from the
    'RRC ID / VALUE / Tape Record Description' block that follows it."""
    starts = [m.start() for m in re.finditer(r'(?m)^\s*01\s+[A-Z]', text)]
    starts.append(len(text)); out = []
    for a, b in zip(starts, starts[1:]):
        chunk = text[a:b]
        recs = parse(chunk, ascii)
        if not recs: continue
        rec = recs[0]
        rid = None
        m = re.search(r'(?is)(?:REC(?:ORD)?[ -]?ID|RRC ID)[^\n]*\n(?:[^\n]*\n){0,4}?[\s*]*(?:VALUE[^\n]*\n)?(?:[^\n]*\n){0,3}?[\s*]*(\d{2})\s+(?:-+>?\s*|=\s*)?[A-Za-z]', chunk[200:] if len(chunk) > 200 else chunk)
        if m: rid = m.group(1)
        rec['rid'] = rid; out.append(rec)
    return out
