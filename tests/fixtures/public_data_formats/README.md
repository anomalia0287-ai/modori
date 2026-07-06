# Public Data Format Fixtures

Minimal checked-in fixtures distilled from the D1 Korean public-data corpus.

These files are intentionally small. They are not source datasets; they preserve
the table-layout patterns that must stay stable in release gates:

- KOSIS-style two-row statistical CSV headers.
- CP949-encoded Korean CSV files.
- MOLIT-style CSV downloads with a long search-condition preamble.
- Weather-style tab-delimited text using an `.xls` extension.
- Merged multi-row XLSX headers and notice-only XLSX downloads.
- Aggregate rows labeled like `합 계`, which must warn by default and be
  removable by explicit import option.
- KOSIS nationwide total rows shaped like `전국 / 전체 / 계`, which must warn
  by default and be removable by explicit import option.
