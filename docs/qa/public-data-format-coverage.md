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

## Still Needed

- A small real CSV captured from a public portal download.
- A small real XLSX captured from a public portal download.
- HWP/PDF table extraction is explicitly out of current table-import scope.
