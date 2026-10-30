# Data Train application source

Use the Windows release ZIP for a ready-to-run app: extract the whole folder and double-click Data Train.exe. See the root README for downloads, build instructions and source execution. The sibling upstream source directories are included.

Choose an RRC file, confirm its detected dataset, convert, then download CSV tables and SQLite. Existing parser routes/layouts remain authoritative. Supplied RRC headings and CSV text values are retained; headerless formats use existing RRC manual-derived field names.

The release offers 61 non-shapefile, non-retired choices: 56 parser routes, 4 image organization/index routes with no OCR, and 1 pending-permits route marked not yet verified. These categories do not establish independent validation of every field. Original GIS/retired parser source remains outside the release choices.

Results persist under %LOCALAPPDATA%\Texas RRC Data Converter\Results. This internal storage name and RRC_ configuration names remain for compatibility. Use Quit app to stop it; closing a tab alone leaves it available. Repeat launch reopens it; an occupied default port causes another local port to be selected.

Layouts live in layouts/*.json, layout_completions.json and layouts_p5.py. Original layout-generation utilities remain under tools and need development tools such as pdftotext. Built W-1 JavaScript is included in the sibling directory; no runtime npm install/build is performed.

Read the root LICENSE, ATTRIBUTION.md, THIRD-PARTY-NOTICES.txt and W1-ISC-NOTICE.txt. Data Train is independent of RRC.
