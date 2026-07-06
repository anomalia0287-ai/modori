# Public Data Format Coverage

Last updated: 2026-07-06

## Scope

This note tracks the first compatibility pass for Korean public-agency table files.
The product should not silently analyze a table when the real header is hidden by
title, source, date, or unit rows, or when a CSV uses a Korean legacy encoding.

## Sources Checked

- Public Data Portal: https://www.data.go.kr/
  - The portal exposes download service types and file extensions including CSV,
    XLS, and XLSX.
- Seoul Open Data Plaza: https://data.seoul.go.kr/
  - The portal lists public data service families including SHEET and FILE.
- Seoul subway monthly ridership dataset:
  https://data.seoul.go.kr/dataList/OA-12914/S/1/datasetView.do
  - The page lists many CSV file downloads and notes that the sheet preview is
    capped while full data is available from CSV files.
- Seoul Fun Station facility dataset:
  https://data.seoul.go.kr/dataList/OA-23023/S/1/datasetView.do
  - The page lists an XLSX file download and a public-use license.

## Download Status

Direct static CSV/XLSX URLs were not exposed in the HTML returned to the agent.
The Seoul OpenAPI sample endpoint was reachable over HTTP, but the tested CSV
sample path returned an API error and the JSON sample path returned no rows for
the tested request. Treat portal downloads as user-assisted or browser-assisted
until a stable no-session URL is captured.

## Regression Coverage Added

- CP949 CSV decoding.
- CSV files with leading title/date/unit rows before the real header.
- XLSX files with leading title/date/unit rows before the real header.
- XLSX files with blank and duplicate headers.
- UI preview text, data notice, and import-step notes surface loader warnings.
- Two-row Korean statistical-table headers are flattened into unique column
  names for CSV and legacy XLS files.
- Three-row merged XLSX headers are flattened into unique column names.
- Files with an `.xls` extension but tabular text content are read as delimited
  text and surfaced with a warning.
- Legacy binary `.xls` files are supported through `xlrd`.
- One-cell or header-only XLSX downloads are rejected with a specific "no table
  data" message instead of being treated as a successful import.
- CSV/XLS/XLSX previews now expose an inference report with header-row count,
  data-start row, confidence, and Korean reason messages. The import preview UI
  shows a compact inference summary so users can see why rows were skipped or
  merged.
- The import dialog now has manual layout controls for sheet name, header row,
  header row count, and data-start row. Confirming the import reuses the same
  override that was used for the refreshed preview.

## D1 Local Corpus Check

Local corpus path checked on 2026-07-06:
`C:\Users\V\Desktop\D1`

Corpus shape:

- 40 files, about 62.7 MB.
- 15 CSV, 14 XLSX, 11 XLS.
- Sources include KOSIS-style statistical tables, MOLIT real-estate transaction
  downloads, KMA weather exports, university status tables, and library
  statistics.

Current loader result after the hardening pass:

- 27 of 40 files preview successfully.
- Among successful previews, 17 report `high` inference confidence and 10
  report `medium` confidence. The medium cases are long-preamble MOLIT
  transaction CSV files where 15 leading search-condition rows are skipped.
- The 13 failures are deliberate no-table XLSX downloads that contain only a
  single notice/header cell. They now fail with a user-facing instruction to
  reacquire CSV or a sheet containing a real table.
- KOSIS-style CSV/XLS two-row headers now flatten into columns such as
  `2025 계 (%)` and `2025 매우 만족`.
- Weather `.xls` files that are actually tab-delimited CP949 text now open with
  an explicit text-fallback warning.
- The 부산대학교 XLSX merged three-row header now flattens into columns such as
  `재학생(A) 계 정원내`.
- Successful previews include an explainable inference summary such as
  "header 2 rows, data starts at row 3, confidence high" plus the warning/reason
  that justified the automatic choice.
- A checked-in minimal corpus now lives under
  `tests/fixtures/public_data_formats`, with a default-gate regression test in
  `tests/test_public_data_corpus.py`. It fixes representative KOSIS two-row CSV,
  MOLIT long-preamble CSV, weather text-as-XLS, merged XLSX header, and
  notice-only XLSX patterns without depending on the local desktop D1 folder.
- The same corpus is now exercised by `--public-data-smoke`, the packaged
  `scripts/package_public_data_smoke.py` gate, and the clean-VM payload batch
  `Run-Public-Data-Smoke.bat`. This smoke does not merely check that files open;
  it asserts header inference, column names, sample cell values, warnings,
  aggregate-row drop behavior, and expected notice-only rejection.
- Rows whose first non-empty cell is a strong aggregate label such as `합 계`,
  `합계`, `총계`, or `소계` are detected conservatively. They are kept by
  default with a visible warning, and the import dialog lets users exclude them
  before confirming the import.

## Still Needed

- Improve the manual import-adjustment UI with stronger affordances for
  low-confidence imports: suggested defaults from the inference report,
  validation feedback, and clearer row-number labeling.
- HWP/PDF table extraction is explicitly out of current table-import scope.
