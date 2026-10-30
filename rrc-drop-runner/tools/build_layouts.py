"""Regenerate layouts/*.json from the RRC manuals. Needs pdftotext (poppler).
Usage: python tools/build_layouts.py   (reads ../manuals/*.pdf)"""
import os, sys, json, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from cobol import parse
MAN = os.path.join(HERE, '..', '..', 'manuals'); OUT = os.path.join(HERE, '..', 'layouts')
def txt(name):
    return subprocess.run(['pdftotext', '-layout', os.path.join(MAN, name + '.pdf'), '-'], capture_output=True, text=True).stdout
def col(n): return n.lower().replace('-', '_')
def fx(rec, table, rec_len=None):
    f = [[col(n), s, l] for n, s, l, *_ in rec["fields"] if 'FILLER' not in n and (rec_len is None or s < rec_len)]
    return {'table': table, 'fields': f, 'length': rec['length'], 'manual_mismatches': [[col(a), b, c + 0] for a, b, c in rec["mismatches"] if 'FILLER' not in a]}
def dump(slug, spec): json.dump(spec, open(os.path.join(OUT, slug + '.json'), 'w'), indent=1)

# Statewide API (well-api-manual) - single 240-byte record
r = parse(txt('well-api-manual'), ascii=True); dump('statewide_api_data', {'kind': 'fixed', 'manual': 'well-api-manual.pdf', 'id_len': 0, 'records': {'': fx(r[0], 'api_quad_records')}})
# Field name/number (oga040) - 80 bytes
r = parse(txt('oga040'), ascii=True); dump('oil_gas_field_name_numbers', {'kind': 'fixed', 'manual': 'oga040.pdf', 'id_len': 0, 'records': {'': fx(r[0], 'field_names')}})
# P-1/P-2 gas disposition (oga0861): oil casinghead file (OLF102) vs gas-well file (GSF102)
r = parse(txt('oga0861'), ascii=True)
dump('pr_p1_p2_gas_disposition', {'kind': 'fixed', 'manual': 'oga0861.pdf', 'id_len': 0, 'by_filename': {'GSF': 'gas', 'GAS': 'gas', '': 'oil'},
      'records': {'oil': fx(r[0], 'casinghead_gas_disposition'), 'gas': fx(r[1], 'gas_well_gas_disposition')}})
# High-cost gas
r = parse(txt('highcostgasleases'), ascii=True); dump('high_cost_gas', {'kind': 'fixed', 'manual': 'highcostgasleases.pdf', 'id_len': 0, 'records': {'': fx(r[0], 'high_cost_gas_leases')}})
r = parse(txt('gasleaseswithinhighcostgas'), ascii=True); dump('high_cost_gas_tight_sands_only', {'kind': 'fixed', 'manual': 'gasleaseswithinhighcostgas.pdf', 'id_len': 0, 'records': {'': fx(r[0], 'tight_sands_leases')}})
# NGPA: record 1 is control record, rest FPM-REC
r = parse(txt('ngpausermanual'), ascii=True)
dump('natural_gas_policy_act', {'kind': 'fixed', 'manual': 'ngpausermanual.pdf', 'id_len': 0, 'first_record': 'control',
      'records': {'': fx(r[0], 'ngpa_filings'), 'control': fx(r[1], 'control_record')}})
# Full wellbore ASCII (wba091): 28 record types in manual order 01..28
r = [x for x in parse(txt('wba091_well-bore-database'), ascii=True)]
names = ['wbroot','wbcompl','wbdate','wbrmks','wbtube','wbcase','wbperf','wbline','wbform','wbsqeze','wbfresh','wboldloc','wbnewloc','wbplug','wbplrmks','wbplrec','wbplcase','wbplperf','wbplname','wbdrill','wbwellid','wb14b2','wbh15','wbh15rmk','wbsb126','wbdastat','wbw3c','wb14b2rm']
dump('full_wellbore_2', {'kind': 'fixed', 'manual': 'wba091_well-bore-database.pdf', 'id_len': 2,
      'records': {f'{i+1:02d}': fx(x, f'{i+1:02d}_{names[i]}', 247) for i, x in enumerate(r[:28])}})
# UIC ASCII: 14 tape records; 04/05 use the ASCII (non-COMP-3) appendix layouts
r = parse(txt('uic_manual_uia010_3116'), ascii=True)
unames = ['inventory_permit','permit_remarks','monitor','h10_monthly','h10h_monthly','monitor_remarks','h5_pressure_test','h5_remarks','enforcement','enforcement_action','enforcement_action_other','enforcement_remarks','h10h_annual','h10_violation']
recs = {f'{i+1:02d}': fx(x, f'{i+1:02d}_{unames[i]}', 622) for i, x in enumerate(r[:14])}
la, d2 = r[14], r[15]
recs['05'] = fx(la, '05_h10h_monthly', 622)
d = fx(d2, '04_h10_monthly'); d['fields'] = [['rrc_tape_record_id', 0, 2]] + [[n, s + 2, l] for n, s, l in d['fields']]; recs['04'] = d
dump('uic_database_2', {'kind': 'fixed', 'manual': 'uic_manual_uia010_3116.pdf', 'id_len': 2, 'records': recs})
print('ok')
# Horizontal drilling permits (DAF318) - single 360-byte record (real files ship ~355 chars + CR)
r = parse(txt('horizontaldrillingpermits'), ascii=True)
dump('horizontal_drilling_permits_permit_issue_date_permit_api_permitted_field', {'kind': 'fixed', 'manual': 'horizontaldrillingpermits.pdf', 'id_len': 0, 'records': {'': fx(r[0], 'horizontal_permits')}})
print('ok2')
