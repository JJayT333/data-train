# Attribution

This project uses, but does not own, these upstream tools (clone them next to `rrc-drop-runner/`):

| Project | Author | License | Used for |
|---|---|---|---|
| [TXRRC_data_harvest](https://github.com/mlbelobraydi/TXRRC_data_harvest) | M. Belobraydic and contributors | Unlicense (public domain) | Full Wellbore EBCDIC (dbf900) layouts and decoding |
| [w1-data-parser](https://github.com/jippylong12/w1-data-parser) | Marcus Salinas | ISC (stated in package.json; no LICENSE file in repo) | W-1 drilling permit files |

Data and layout manuals in `manuals/` are published by the Railroad Commission of Texas and belong to them:
https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/
- w1-data-parser src/parser.ts patched locally (rrc-tools): record types 03/04/05 are collected as lists, because real DAF802 files carry several permitted-field records per permit; upstream kept only the last one.

- 2026-10-30: high_cost_gas (NGF115) — skip the `O/G}DST}...` column-title row (was parsed as a data row). Image unpack — keep a leading district folder (e.g. `01/`) instead of stripping it as the common root, and fill `district` from it. Verified on real uif700/uif700a (UIC), gse10 (G-10), oltdw (oil detail), wlf101 (gas well DB), St-1 CSV, ngf115/ngf019, ogfpm (NGPA master), imaged completions and directional survey zips.
- 2026-10-30: Gzip input — `extract()` now gunzips `.gz` members/drops (RRC ships orf850/wlf607 etc. as `.ebc.gz`); before, raw gzip bytes were decoded as EBCDIC (W-10 gave 33,780 junk rows; now 319,484 real records from wlf607.ebc.gz). Completion Information in Data Format — rebuilt missing columns in `layout_completions.json` from RRC's `cmpldatasubscriptions_usermanual_20171101.pdf` (now in manuals/): FORMATION/DEPTH (formation), ROW_NO/DIFF/VOLUME (G-1 measurement), FROM/TO (amount & material, production interval), liner SIZE/TOP/BOTTOM/SCREEN, ELEVATION/REMARKS/COMMINGLED (G-1/W-2), CLASSIFICATION (P-4), GATHERER/PURCHASER (P-4 gas gatherer), G-5 RESIDUE/LOSS/PVT, W-12 REMARKS, packet DISTRICT/COUNTY/SURVEY/LAT/LONG. Remarks containing line breaks are re-joined to their record (were split into junk "unknown_" tables). JSON — nested lists of objects (R-3 Sections I–XI, P-18 well/gatherer/allocation lists) become child tables keyed by parent_row + record key; cp1252 fallback for stray 0xA0 bytes in P-18. Verified on real orf850 (EBCDIC + ASCII), wlf607, 10-29-2026 nightly completions packet zip, P18 August 2026, R3 September 2026.

## Windows release packaging, 2026-10-30

The sibling source directories are bundled rather than requiring end-user clones. The TXRRC numeric/text decoder helpers are reused across EBCDIC layouts, in addition to Full Wellbore. W-1 built JavaScript and a compatible official Node runtime are included; runtime npm install/build has been removed. See THIRD-PARTY-NOTICES.txt and W1-ISC-NOTICE.txt for retained provenance and applicable notices. The published upstream npm 1.0.3 package also declares ISC without including a separate LICENSE file or copyright year.
