"""Run real RRC sample files through the registry. Usage: python tools/run_samples.py"""
import os, sys, json, time, tempfile, shutil, datetime, traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); os.chdir(ROOT)
from parsers import route, extract
CAT = {d['slug']: d for d in json.load(open('../datasets-catalog.json'))}
S = '../samples/'
RUNS = [
 ('fldtpe.txt', 'oil_gas_field_name_numbers'), ('api507.dbf', 'statewide_api_data_2'),
 ('well001.zip', 'well_layers_by_county'), ('surv001.zip', 'survey_layers_by_county'),
 ('maf016.cc001', 'statewide_api_data'), ('subscriptions_2026-10-28_district09.zip', 'drilling_permit_w1_imaged_files'),
 ('olf004l.ebc', 'oil_ledger_dist_4'), ('olf007l.ebc', 'oil_ledger_dist_7c'), ('gsf001l.ebc', 'gas_ledger_dist_1_2_3'),
 ('olf102.ebc', 'pr_p1_p2_gas_disposition_2'), ('gsf102.ebc', 'pr_p1_p2_gas_disposition_2'),
 ('daf420.dat', 'drilling_permit_master_and_trailer'), ('pr_production_report_20261017.txt', 'production_report_for_pending_leases'),
 ('gsf3841', 'gas_annual_report_field_table'), ('olf3341', 'oil_annual_report_field_table'),
 ('daf802_head.txt', 'drilling_permit_master_and_trailer'), ('daf318', 'horizontal_drilling_permits_permit_issue_date_permit_api_permitted_field'),
 ('pending_permits', 'drilling_permits_pending_approval_includes_latitudes_and_longitudes'),
 ('orr_og_field_001_prod.dmp', 'oil_gas_field_rules'),
 ('dbf900_head.ebc', 'full_wellbore'), ('dbf900_head.txt', 'full_wellbore_2'),
 ('ldf900ol_head.ebc', 'historical_ledger_statewide_oil'), ('wlf100_head.ebc', 'statewide_oil_well_database'),
 ('wlf100_head.ebc', 'statewide_gas_well_database'), ('og_wellbore_ewa_head.csv', 'wellbore_query_data'),
 ('uif700_head.ebc', 'uic_database'), ('uif700a_head.txt', 'uic_database_2'),
 ('gse10.ebc', 'gas_well_status_26_month_g_10'), ('oltdw.ebc', 'oil_detail_well'),
 ('wlf101_head.ebc', 'statewide_gas_well_database'), ('St1ApplicationReport.csv', 'st_1_application_report'),
 ('ngf115.txt', 'high_cost_gas'), ('ngf019.txt', 'high_cost_gas'), ('ogfpm_head.txt', 'natural_gas_policy_act'),
 ('gap7/orf850_head.ebc', 'p5_organization'), ('gap7/orf850_head.txt', 'p5_organization_2'),
 ('gap7/wlf607.ebc.gz', 'oil_well_status_26_month_w_10'), ('gap7/10-29-2026.zip', 'completion_information_in_data_format'),
 ('gap7/p18.zip', 'p_18_skim_oil_condensate_report'), ('gap7/r3_sep2026.json', 'r3_gas_processing_plants_2'),
 ('imaged_completions_slice.zip', 'imaged_completion_files'),
 ('INSPECTIONS_DIST01.txt', 'rrc_oil_ice_data'), ('VIOLATIONS_DIST01.txt', 'rrc_oil_ice_data'), ('oil_ice_dist01.zip', 'rrc_oil_ice_data'), ('dir_surveys_slice.zip', 'directional_survey_applications'),
]
only = sys.argv[1:]
res = []
for fn, slug in RUNS:
    if only and fn not in only: continue
    p = S + fn
    if not os.path.exists(p): res.append((fn, slug, 'missing', '', '')); continue
    st, f = route(CAT[slug]); out = os.path.join(ROOT, 'out', slug, datetime.datetime.now().strftime('%Y%m%d_%H%M%S_') + fn.replace('.', '_').replace('/','_'))
    os.makedirs(out, exist_ok=True); work = tempfile.mkdtemp(); t = time.time()
    try:
        cp = os.path.join(work, os.path.basename(fn)); shutil.copy(p, cp)
        counts, note = f(extract(cp, os.path.join(work, 'x')), out)
        ok = 'ok' if counts and sum(counts.values()) else 'EMPTY'
        res.append((fn, slug, ok, '; '.join(f'{k}={v}' for k, v in counts.items())[:300], (note or '')[:300] + f' [{time.time()-t:.1f}s]'))
    except Exception as e:
        res.append((fn, slug, 'FAIL', '', traceback.format_exc().strip().splitlines()[-1][:300]))
    shutil.rmtree(work, ignore_errors=True)
for r in res: print(' | '.join(r))
