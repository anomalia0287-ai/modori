# Build Week Real-Data Demo Audit

Date: 2026-07-21 KST

## Outcome

Selected the UCI Student Performance Portuguese-course table for the Build Week demo and rejected the previously considered BFI/SAPA file for new public-demo distribution. The selected source is observed social-science data with a DOI, codebook, and explicit CC BY 4.0 license. The committed demo view is 649 rows by six non-identifying variables and is byte-reproducible from the checked-in official archive.

## Fixed selection gates

A candidate had to satisfy all applicable gates before visual appeal was considered:

1. traceable primary source and codebook;
2. explicit reuse terms suitable for a public submission;
3. at least 100 complete pairs and no more than 10% missingness for the demo pair;
4. no direct identifier or unnecessary sensitive field in the demo file;
5. observation unit and dependence structure explainable without hiding a design caveat;
6. `0.25 <= |r or rho| <= 0.85`, avoiding both an invisible result and a toy-perfect result;
7. a noncausal beginner question that maps to an existing Modori capability without expanding method scope.

## Candidate comparison

| Candidate | Evidence | Decision |
| --- | --- | --- |
| BFI/SAPA personality responses from Rdatasets | 2,800 observed responses and a useful moderate E4/E5 association, but the [Rdatasets license note](https://github.com/vincentarelbundock/Rdatasets#license) says the rights to the numeric data could not be determined definitively. | Rejected at the public reuse gate. Existing test-fixture use was not treated as permission for a new marketing artifact. |
| [UCI Student Performance](https://archive.ics.uci.edu/dataset/320/student+performance) | UCI labels the subject area Social Science, documents school-report and questionnaire collection at two Portuguese schools, provides DOI `10.24432/C5TG7T` and a full codebook, and states CC BY 4.0. The Portuguese table has 649 rows, no chosen-field missingness, and weekly-study-time/final-grade Spearman `rho = 0.2747118483356099`. | Selected. It passes all fixed gates and supports a clear rank-association story. |
| [World Development Indicators](https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators) one-year country cross-section | The catalog states CC BY 4.0 and offers strong metadata. However, the unit would be country-year and the three-minute beginner story would require explicit ecological-correlation, aggregation, and indicator-provider boundaries. | Not advanced past the design gate. Retained only as a source-governance fallback if the selected UCI source failed. |

## Source verification

Accessed the official UCI page and archive on 2026-07-21. UCI's page states that the data cover student achievement in two Portuguese secondary schools, were collected with school reports and questionnaires, have 649 instances for the Portuguese table, and are licensed under CC BY 4.0. The page provides the citation `Cortez, P. (2008). Student Performance [Dataset]` and DOI `10.24432/C5TG7T`.

| Layer | SHA-256 |
| --- | --- |
| Official outer archive `student+performance.zip` | `82ae9d66437b9808df42e8c89d2bb179c46e9cfbcf06f38abc1d20b3b747e177` |
| Selected nested `student.zip` | `4f671ae4598c20bb4e64de0f65931c98a609a52e383604e2601bd8f7e3822427` |
| Selected `student-por.csv` | `a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f` |
| Derived `student-study-and-grades.csv` | `e51ebf09f537865aa7353f3b23cfa391e75767783d0061b628c1361eaef4cb0e` |

The outer archive is 40,735 bytes. The selected source member is 93,220 bytes. The derived CSV is 10,804 bytes.

## Transform and privacy minimization

The deterministic preparation keeps only:

- weekly study-time band;
- source-coded past class failures;
- absences;
- family educational support;
- intention to pursue higher education;
- final grade.

It does not retain or create an ID. It removes school, age, sex, address, family size, parental education/jobs, guardian, relationship, and alcohol-use fields. The displayed demo is therefore materially narrower than the public source and contains only fields needed to make the table credible and the chosen question reviewable.

The preparation script performs no network request. It validates all three source hashes before parsing, requires the exact 33-column source schema and 649 rows, applies a six-column allowlist, checks missingness and codebook ranges, independently recomputes the frozen Spearman value, and writes final files through temporary siblings.

## Independent numerical audit

The following values were recomputed directly from the generated CSV with pandas and SciPy, independently of the script's JSON summary:

| Check | Observed |
| --- | --- |
| Shape | 649 rows × 6 columns |
| Complete demo pair | 649 |
| Missing values | 0 in every retained column |
| Weekly study-time counts | 1: 212; 2: 305; 3: 97; 4: 35 |
| Final-grade range | 0–19 on the documented 0–20 scale |
| Final-grade mean / median | 11.906009244992296 / 12 |
| Spearman rank association | `rho = 0.2747118483356099`, two-sided `p = 1.060624038270125e-12` |
| Pearson sensitivity reference | `r = 0.24978868999886286`, two-sided `p = 1.0908085906064388e-10` |

Spearman is the demo method because study time is an ordered four-level variable. Pearson is recorded only as a preparation sensitivity reference and is not the chosen inferential framing.

## TDD and reproducibility evidence

Initial test execution failed during collection because `scripts.prepare_build_week_demo_data` did not exist. After implementing the offline integrity/transform boundary and generating the committed output, one test failed because its identifier screen incorrectly treated the legitimate `school_absences` name as the forbidden source field `school`; the assertion was corrected to compare exact forbidden source fields and ID suffixes, without relaxing the product data allowlist.

Final focused result:

```text
python -m pytest -p no:cacheprovider tests/test_prepare_build_week_demo_data.py -q
3 passed in 1.34s
exit 0

python -m ruff check scripts/prepare_build_week_demo_data.py tests/test_prepare_build_week_demo_data.py
All checks passed!
exit 0
```

Two independent preparations in temporary directories produce byte-identical CSV files and byte-identical JSON summaries; both CSV files match the committed CSV. A one-byte archive mutation is rejected before output replacement, and an existing output remains unchanged.

## Claim boundary for the demo

Allowed: within these 649 released Portuguese-course records, higher weekly study-time bands tended to accompany higher final grades; Modori reviewed the variable meanings, prepared a Spearman configuration, waited for a separate Run, calculated locally, and exported a Word report.

Not allowed: study time caused the grade difference; the result represents Portuguese students or students generally; Modori chose a universally valid method; the source authors or UCI endorse Modori; this one workflow establishes parity or superiority over another statistics package.
