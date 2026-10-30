"""Build layouts/<slug>.json (kind=ebcdic) for every RRC EBCDIC product from the manuals."""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from cobol import parse, parse_with_ids
MAN = os.path.join(HERE, '..', '..', 'manuals'); OUT = os.path.join(HERE, '..', 'layouts')
def txt(n): return subprocess.run(['pdftotext', '-layout', os.path.join(MAN, n + '.pdf'), '-'], capture_output=True, text=True).stdout
def col(n): return n.lower().replace('-', '_')
def ftype(pic, comp3):
    p = pic.upper()
    if comp3: return 'P'
    if 'X' in p or 'A' in p: return 'X'
    return 'S' if p.startswith('S') else 'N'
def fx(rec, table, reclen):
    fl = [f for f in rec['fields'] if 'FILLER' not in f[0]]
    note = None
    if rec['length'] > reclen:  # manual PICs overflow the stated record length: trust printed positions
        note = f"computed length {rec['length']} > {reclen}; used printed positions"
        new = []
        for i, f in enumerate(fl):
            st = f[6] - 1 if f[6] else (new[-1][1] + new[-1][2] if new else f[1])
            nxt = next((g[6] - 1 for g in fl[i+1:] if g[6]), None)
            ln = f[2] if nxt is None else max(1, min(f[2], nxt - st))
            new.append((f[0], st, ln, f[3], f[4], f[5], f[6]))
        fl = new
    fields = [[col(n), s, l, ftype(p, c), d] for n, s, l, d, c, p, _ in fl if s + l <= reclen]
    out = {'table': table, 'fields': fields}
    if note: out['note'] = note
    return out
def dump(slug, manual, reclen, records, id_pos=(0, 2), **kw):
    json.dump(dict(kind='ebcdic', manual=manual + '.pdf', reclen=reclen, id_pos=list(id_pos), records=records, **kw), open(os.path.join(OUT, slug + '.json'), 'w'), indent=1)

def seq(manual, reclen, names=None, ids=None, sub=None):
    r = parse_with_ids(txt(manual))
    if sub is not None: r = [r[i] for i in sub]
    ids = ids or [x['rid'] or '01' for x in r]
    return {i: fx(x, f"{i}_{(names[n] if names else col(x['fields'][1][0] if len(x['fields']) > 1 else x['name'])[:28])}", reclen) for n, (i, x) in enumerate(zip(ids, r))}

# Statewide field data (OGA090)
fnames = 'fldroot gasseg flmktdmd oprmktdm flmktrmk flsuprmk gascycle gsfldrul gasaform gasrmrks gscounty gasafact asheet asheetmo flt3root fldt3 fldmo calc49b oilseg oilcycle olfldrul oilaform oilrmrks oilftrot oilafact olcounty assocgas fldmap gsoptrul oloptrul'.split()
dump('statewide_field_data', 'field_information_oga090', 240, seq('field_information_oga090', 240, fnames, [f'{i:02d}' for i in range(1, 31)]))
# Ledgers
r = parse(txt('ola013k'))
oil = {k: fx(x, t, 1200) for k, x, t in zip('1345', r, ['field', 'lease', 'multi_well', 'well'])}
for s in ['oil_ledger_dist_1_2', 'oil_ledger_dist_3', 'oil_ledger_dist_4', 'oil_ledger_dist_5_and_6', 'oil_ledger_dist_6e', 'oil_ledger_dist_7b', 'oil_ledger_dist_7c', 'oil_ledger_dist_8', 'oil_ledger_dist_8a', 'oil_ledger_dist_9', 'oil_ledger_dist_10']:
    dump(s, 'ola013k', 1200, oil, id_pos=(0, 1))
r = parse(txt('gsa020k'))
gas = {'1': fx(r[0], 'field', 2120), '5': fx(r[1], 'well', 2120)}
for s in ['gas_ledger_dist_1_2_3', 'gas_ledger_dist_4_5_6_6e', 'gas_ledger_dist_7b_7c_8_8a_9_10']:
    dump(s, 'gsa020k', 2120, gas, id_pos=(0, 1))
# P-1/P-2 gas disposition EBCDIC
r = parse(txt('oga0861'))
dump('pr_p1_p2_gas_disposition_2', 'oga0861', 200, {'oil': fx(r[0], 'casinghead_gas_disposition', 200), 'gas': fx(r[1], 'gas_well_gas_disposition', 200)},
     id_pos=(0, 0), by_filename={'GSF': 'gas', 'GAS': 'gas', '': 'oil'})
# Historical ledger (LAD001): 0=oil root,1=gas root, 2..8 = ids 02..08
ln = ['root', 'root', 'gsdata', 'gasdsp', 'gconds', 'gstat', 'oldata', 'oildsp', 'ocshds']
r = parse_with_ids(txt('oilandgashistoricalledger_lad001'))
dump('historical_ledger_statewide_oil', 'oilandgashistoricalledger_lad001', 160, {i: fx(r[k], f'{i}_{ln[k]}', 160) for i, k in [('01', 0), ('06', 6), ('07', 7), ('08', 8)]})
dump('historical_ledger_statewide_gas', 'oilandgashistoricalledger_lad001', 160, {i: fx(r[k], f'{i}_{ln[k]}', 160) for i, k in [('01', 1), ('02', 2), ('03', 3), ('04', 4), ('05', 5)]})
# Statewide production (PDA001)
r = parse_with_ids(txt('pda001'))
on = 'pdroot pdorptcy pdoprod pdormvds pdodsp pdocshds pdoprpv pdocmpmt pdocmprd pdocmods pdooeb pdocmpv pdoprval pdremark pdodsprk pdocmgrk'.split()
oid = ['01'] + [f'{i:02d}' for i in range(2, 14)] + ['22', '23', '24']
dump('statewide_production_data_oil', 'pda001', 102, {i: fx(r[k], f'{i}_{on[k]}', 102) for k, i in enumerate(oid)})
gn = 'pdroot pdgrptcy pdgprod pdgdsp pdgconds pdgcmpmt pdgstat pdgrein pdgprpv pdremark pdgdsprk pdcndrmk pdgsepex'.split()
gid = ['01'] + [f'{i:02d}' for i in range(14, 22)] + ['22', '25', '26', '27']
dump('statewide_production_data_gas', 'pda001', 102, {i: fx(r[16 + k], f'{i}_{gn[k]}', 102) for k, i in enumerate(gid)})
# P-4
dump('certificate_of_authorization_p_4_database_oil_and_gas', 'p4-user-manual_p4a002_feb2015', 92, seq('p4-user-manual_p4a002_feb2015', 92))
# P-5 EBCDIC
r = parse(txt('ora001_p5_manual_october-2014'))
pn = ['specialty_code_table', 'organization', 'specialty_codes', 'district_address', 'field_address', 'officers', 'remarks', 'activity_indicators', 'activity_restrictions']
dump('p5_organization', 'ora001_p5_manual_october-2014', 350, {x['ids'][0]: fx(x, pn[k], 350) for k, x in enumerate(r)})
# R-3
dump('r3_gas_processing_plants', 'gra001', 422, seq('gra001', 422))
# Well databases (WLA001): oil tape idx 0-17, gas tape idx 18-31
wo = ['01'] + [f'{i:02d}' for i in range(2, 17)] + ['28', '26']
wg = ['01', '15', '16', '28', '17', '18', '19', '20', '21', '22', '23', '24', '25', '27']
wl = parse_with_ids(txt('wla001k'))
dump('statewide_oil_well_database', 'wla001k', 228, {i: fx(wl[k], f"{i}_{wl[k]['fields'][1][0].lower().replace('-', '_')[:24]}", 228) for k, i in enumerate(wo)})
dump('statewide_gas_well_database', 'wla001k', 228, {i: fx(wl[18 + k], f"{i}_{wl[18 + k]['fields'][1][0].lower().replace('-', '_')[:24]}", 228) for k, i in enumerate(wg)})
# Single-record files
for slug, man, rl, t in [('oil_detail_well', 'ola028k', 100, 'oil_detail_well'), ('oil_well_status_26_month_w_10', 'ola001k', 110, 'w10_status'), ('gas_well_status_26_month_g_10', 'gsa018k', 130, 'g10_status')]:
    dump(slug, man, rl, {'': fx(parse(txt(man))[0], t, rl)}, id_pos=(0, 0))
# UIC EBCDIC (main COMP-3 layouts 01..14)
un = ['inventory_permit', 'permit_remarks', 'monitor', 'h10_monthly', 'h10h_monthly', 'monitor_remarks', 'h5_pressure_test', 'h5_remarks', 'enforcement', 'enforcement_action', 'enforcement_action_other', 'enforcement_remarks', 'h10h_annual', 'h10_violation']
r = parse_with_ids(txt('uic_manual_uia010_3116'))[:14]
dump('uic_database', 'uic_manual_uia010_3116', 622, {f'{k+1:02d}': fx(x, f'{k+1:02d}_{un[k]}', 622) for k, x in enumerate(r)})
print('ok')
