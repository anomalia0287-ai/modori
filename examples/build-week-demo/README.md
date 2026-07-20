# Modori Build Week real-data demo

## What this example is

`student-study-and-grades.csv` is a six-variable, non-identifying view of 649 records from the Portuguese-language-course table in the UCI Student Performance dataset. It supports this beginner-facing question:

> Do weekly study-time bands and final grades tend to move together in these records?

The appropriate demo calculation is a Spearman rank correlation because weekly study time is recorded as ordered bands. The observed result is an association within the released records, not evidence that study time causes grades and not an estimate for students outside the two source schools.

## Source, citation, and license

- Dataset page and codebook: <https://archive.ics.uci.edu/dataset/320/student+performance>
- Dataset DOI: <https://doi.org/10.24432/C5TG7T>
- Official archive URL: <https://archive.ics.uci.edu/static/public/320/student%2Bperformance.zip>
- Associated paper: Paulo Cortez and Alice Silva, *Using Data Mining to Predict Secondary School Student Performance* (2008), <http://hdl.handle.net/1822/8024>
- License stated by UCI: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)

Required attribution:

> Cortez, P. (2008). Student Performance [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5TG7T. Licensed under CC BY 4.0.

Modori's CSV is an adaptation: it selects and renames six columns from `student-por.csv`. The source authors and UCI do not endorse Modori.

## Observation unit and fields

Each row is one record in the source Portuguese-language course table. The source documentation says the full dataset was collected from school reports and questionnaires at two Portuguese secondary schools. The demo view retains no direct identifier and removes the source's school, age, sex, address, parent, guardian, relationship, and alcohol-use fields.

| Demo field | Source field | Meaning |
| --- | --- | --- |
| `weekly_study_time_band` | `studytime` | 1: under 2 hours/week; 2: 2–5; 3: 5–10; 4: over 10 |
| `past_class_failures` | `failures` | Source-coded number of past class failures; observed values 0–3 |
| `school_absences` | `absences` | Recorded school absences; observed values 0–32 |
| `family_educational_support` | `famsup` | `yes` or `no` |
| `plans_higher_education` | `higher` | `yes` or `no` |
| `final_grade` | `G3` | Portuguese-course final grade on the documented 0–20 scale; observed values 0–19 |

The separate mathematics table is not joined or used. The source notes that some students occur in both source tables, which does not create repeated rows within this one-table demo.

## Integrity and regeneration

The exact checked-in official archive has SHA-256:

```text
82ae9d66437b9808df42e8c89d2bb179c46e9cfbcf06f38abc1d20b3b747e177
```

The preparation command is offline and rejects any different archive, inner archive, member, schema, row count, or value range.

```powershell
python scripts/prepare_build_week_demo_data.py `
  --source examples/build-week-demo/source/uci-student-performance.zip `
  --output examples/build-week-demo/student-study-and-grades.csv `
  --summary .visual-qa/build-week-demo-summary.json

Get-FileHash -Algorithm SHA256 `
  examples/build-week-demo/student-study-and-grades.csv

python -m pytest -p no:cacheprovider `
  tests/test_prepare_build_week_demo_data.py -q
```

Expected derived CSV SHA-256:

```text
e51ebf09f537865aa7353f3b23cfa391e75767783d0061b628c1361eaef4cb0e
```

Independent frozen references for `weekly_study_time_band` versus `final_grade` are:

- rows and complete pairs: 649;
- Spearman `rho = 0.2747118483356099`, two-sided `p = 1.060624038270125e-12`;
- Pearson `r = 0.24978868999886286`, two-sided `p = 1.0908085906064388e-10`.

These numerical references verify preparation and calculation consistency. They do not validate a causal or population-level claim.
