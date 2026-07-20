# Third-Party Notices

This notice accompanies the Modori source repository. Modori-authored source is
licensed under `GPL-3.0-only`; see `LICENSE`. Third-party components and data keep
their own copyrights and license terms.

The OpenAI Build Week submission is source-only. It does not publish a prebuilt
Python, Qt, or PyInstaller dependency bundle. The packages below are installed by
the recipient from their package indexes. If someone later redistributes a frozen
executable, that distributor must repeat the audit for the exact frozen inventory,
include the applicable license texts and notices, and provide corresponding source
where required.

This inventory is an engineering attribution record, not legal advice.

## Direct runtime dependencies

| Component | Use in Modori | Upstream license declaration | Upstream |
| --- | --- | --- | --- |
| defusedxml | Defensive XML parsing | Python Software Foundation License (`PSF-2.0` family) | <https://github.com/tiran/defusedxml> |
| factor_analyzer | Factor-analysis calculations | GNU GPL version 2 or later (`GPL-2.0-or-later`) | <https://github.com/EducationalTestingService/factor_analyzer> |
| matplotlib | Figures and plotting | Matplotlib project license (`LicenseRef-Matplotlib`) | <https://matplotlib.org/> |
| openpyxl | XLSX import/export support | MIT | <https://openpyxl.readthedocs.io/> |
| pandas | Tabular data operations | BSD-3-Clause | <https://pandas.pydata.org/> |
| Pingouin | Selected statistical calculations and post-hoc paths | Upstream declares `GPL-3.0`; Modori treats the combination conservatively as GPL version 3 only | <https://github.com/raphaelvallat/pingouin> |
| pyreadstat | SPSS SAV import | Apache-2.0 | <https://github.com/Roche/pyreadstat> |
| PyYAML | Knowledge and configuration resource parsing | MIT | <https://pyyaml.org/> |
| PySide6, PySide6 Addons, PySide6 Essentials, Shiboken6 | Qt desktop UI and bindings | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`; the current GPL combination uses the GPL-3.0-only option | <https://doc.qt.io/qtforpython-6/> |
| python-docx | DOCX report generation | MIT | <https://python-docx.readthedocs.io/> |
| scikit-learn | Statistical and preprocessing utilities | BSD-3-Clause | <https://scikit-learn.org/> |
| SciPy | Statistical and numerical routines | BSD-3-Clause plus separately licensed bundled components | <https://scipy.org/> |
| statsmodels | Statistical model and comparison paths | BSD-3-Clause | <https://www.statsmodels.org/> |
| xlrd | Legacy XLS reading | BSD | <https://xlrd.readthedocs.io/> |

The runtime, development, and packaging dependency versions used after environment
bootstrapping are constrained in `constraints/build-week-windows-py312.txt`. The file
does not constrain `pip` itself or every isolated-build bootstrap tool. Each installed
distribution's metadata and license files remain authoritative for that version.
Transitive packages are not relicensed by Modori.

## Build and test tools

PyInstaller 6.21.0 is used only to create a local one-folder Windows build. It is
distributed under GPL-2.0-or-later with a special exception for generated bundles.
That exception does not override the licenses of bundled dependencies. Official
terms: <https://pyinstaller.org/en/stable/license.html>.

R/Rscript is an optional external reference runtime for selected cross-engine tests;
it is not part of the Modori application runtime or source distribution. Ruff,
pytest, Bandit, pip-audit, and other development dependencies are listed in the
constraint file and retain their upstream terms.

## Font

`src/modori/ui/qml/assets/fonts/Parisienne-Regular.ttf` is Parisienne by Brian J.
Bonislawsky DBA Astigmatic. It is distributed under the SIL Open Font License 1.1
(`OFL-1.1`) with the Reserved Font Name "Parisienne". The font is unmodified. The
copyright notice and complete license text are preserved in:

`src/modori/ui/qml/assets/fonts/OFL.txt`

## Icons

The SVG icons under `src/modori/ui/qml/assets/icons/` are from Lucide Icons and,
for the identified derived icons, Feather. Lucide material is ISC-licensed and the
identified Feather-derived material is MIT-licensed. Copyright notices and complete
license texts are preserved in:

`src/modori/ui/qml/assets/icons/LUCIDE-LICENSE.txt`

## Synthetic Modori fixtures

The recommendation benchmark files beneath
`tests/fixtures/recommendation_benchmark/public/` are deterministic synthetic data.
They contain no real respondent records or real personally identifying information
and use `LicenseRef-Modori-Synthetic-Benchmark-1.0`. Their complete terms are in:

`tests/fixtures/recommendation_benchmark/public/LICENSE-TERMS.md`

Other fixtures described as deterministic or synthetic in
`tests/fixtures/README.md` were created for Modori and are covered by the repository
license unless a more specific notice is present.

## UCI Student Performance demo data

`examples/build-week-demo/source/uci-student-performance.zip` is the official
Student Performance archive published by the UCI Machine Learning Repository.
`examples/build-week-demo/student-study-and-grades.csv` is a deterministic
six-column view derived from the Portuguese-course table for the Build Week demo.

- Citation: Cortez, P. (2008). *Student Performance* [Dataset]. UCI Machine
  Learning Repository.
- DOI: <https://doi.org/10.24432/C5TG7T>
- Dataset page and codebook:
  <https://archive.ics.uci.edu/dataset/320/student+performance>
- License: Creative Commons Attribution 4.0 International (`CC-BY-4.0`),
  <https://creativecommons.org/licenses/by/4.0/>

The derived view retains weekly study-time band, past class failures, absences,
family educational support, plans for higher education, and final grade. It removes
the source demographic, family-background, relationship, health, and alcohol-use
fields and contains no direct identifier. Full source and transform hashes are
recorded in `examples/build-week-demo/README.md`.

## R psych / Rdatasets BFI fixture

`tests/fixtures/psych_bfi.csv` is a test-only copy of the `bfi` dataset distributed
with the R `psych` package and obtained through the Rdatasets mirror.

- psych package: William Revelle, *Procedures for Psychological, Psychometric, and
  Personality Research*, licensed GNU GPL version 2 or later.
- source CSV: <https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/psych/bfi.csv>
- dataset documentation: <https://vincentarelbundock.github.io/Rdatasets/doc/psych/bfi.html>

Rdatasets explicitly states that it could not determine definitive standalone
copyright terms for every dataset row collection. Modori therefore does not use this
file as the Build Week judge sample, does not claim ownership of it, and does not
recommend extracting or republishing it independently. It remains only to preserve
the existing public-fixture and cross-engine regression evidence. The repository
treats the copy under the psych package's GPL-compatible terms, but the standalone
dataset-rights uncertainty remains disclosed rather than presented as resolved.

## NIST Statistical Reference Datasets

Files under `tests/fixtures/nist/` reproduce selected NIST/ITL Statistical Reference
Datasets and certified values for numerical regression tests. NIST is the source and
does not endorse Modori or conclusions drawn from Modori. Source and certified-value
URLs are recorded per fixture and in `tests/fixtures/README.md`.

NIST's copyright, fair-use, licensing, warranty, and attribution statement applies:
<https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications>.

Modified or reformatted fixture material must not be represented as an official NIST
version. Modori's fixture metadata records the source, and the values are used only
for software numerical-reference tests.

## Names and trademarks

Python, Qt, PySide, Microsoft Windows, SPSS, R, jamovi, JASP, and other names belong
to their respective owners. Their mention identifies compatibility, comparison, or
test context and does not imply sponsorship or endorsement.
