# Modori

Modori is a Windows-first desktop application for making a limited set of
statistical research decisions visible, reviewable, and replayable before a
calculation runs. It is designed for learners and researchers who need more
structure than a blank statistics dialog, without sending their study data to a
model or a hosted service.

This repository is the source submission for the OpenAI Build Week Education
track. Modori existed before the event. The eligible work is documented
separately from the pre-existing statistical engine in
[`docs/build-week/BUILD_WEEK_DELTA.md`](docs/build-week/BUILD_WEEK_DELTA.md).

## What the current Build Week work adds

The local Research OS flow supports exactly six bounded P1 research tasks:

1. Pearson product-moment correlation;
2. Spearman rank correlation;
3. paired-sample mean change;
4. Welch two-group mean difference;
5. descriptive summary; and
6. frequency distribution.

For those tasks, Modori can collect a research intent and variable roles over
multiple rounds, record the decisions locally, create an AnalysisPassport bound
to the current data, show the proposed method and interpretation boundary, and
prepare the existing deterministic calculation path. A calculation still starts
only after a separate user action.

The eligible work also includes the revised Windows research surface, authority
and recovery hardening, and release-path integration. A final packaged-app audit
found and closed two execution blockers: imported data now keeps Research OS bound
to the current pipeline, and Research OS correlation preparations are validated by
the same parameter contract as the calculation engine. Both fixes have regression
coverage and are included in the fresh release gate below.

The candidate and clarification logic is deterministic. Recommendation evidence
is labelled `EXPERIMENTAL`, candidate order is not an accuracy ranking, and no
candidate is selected or executed automatically. The current method space has no
verified external route.

## Local and privacy boundary

The current application has no configured runtime network client, hosted model,
telemetry path, or cloud analysis route. Statistical calculations and the six-task
Research OS flow run locally. GPT-5.6 and Codex were used to build and audit the
project; they are not runtime dependencies and do not receive or calculate over
the user's dataset.

On Windows, Modori can write application-owned state beneath
`%LOCALAPPDATA%\Modori`, including caches, UI settings, recent-file paths, a local
research-task index, and per-project SQLite decision ledgers. Recent-file storage
is enabled by default and can be disabled in Settings. Exported reports are
written only to a path chosen by the user. Operating-system logs, antivirus
history, backup software, and cloud-synced folders remain outside Modori's
control, so this is a code-path description rather than a privacy certification.

## Verified target

- Windows 11 x64
- CPython 3.12.10
- source execution and a local PyInstaller 6.21.0 one-folder build

The package metadata permits Python 3.11 or newer, but the Build Week release is
verified only on Python 3.12.10 and Windows 11 x64. No macOS, Linux, or low-cost HP
laptop pass is claimed. The separate B5 HP measurement is still pending.

No prebuilt executable is published for this submission. The documented
PyInstaller output is unsigned and intended for local verification only.

## Setup on Windows

From a PowerShell prompt at the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -c constraints\build-week-windows-py312.txt -e ".[dev,packaging]"
```

The constraints file records the dependency versions used by the verified
Windows environment. It is a Windows/Python 3.12 release constraint set, not a
claim that every dependency builds identically on every platform.

Run the application:

```powershell
.\.venv\Scripts\python.exe -m modori.app
```

The main application shell is currently Korean-first. On the entry screen,
choose `CASUAL MODE` or `PRO MODE`, then use `데이터 열기` (Open data). The import
dialog confirms the detected table before the data enters the workspace.

Supported import paths are CSV, XLSX, legacy XLS, and SPSS SAV. Some public-data
CSV layouts with preambles, multi-row headers, aggregate rows, or Korean legacy
encodings have additional bounded import handling. Unsupported or ambiguous
layouts fail with a visible message or require explicit review.

## Synthetic sample

Use this small deterministic, synthetic correlation fixture:

```text
tests\fixtures\recommendation_benchmark\public\pilot\data\pilot-007-correlation.csv
```

It contains only two generated columns, `stress` and `sleep_hours`. It has no real
respondent records or real personally identifying information. Its terms are in
[`tests/fixtures/recommendation_benchmark/public/LICENSE-TERMS.md`](tests/fixtures/recommendation_benchmark/public/LICENSE-TERMS.md).

For a GUI walkthrough:

1. launch Modori and select `CASUAL MODE`;
2. open the synthetic CSV above and review the import preview;
3. confirm the import;
4. open the Research OS panel and accept the noncausal interpretation boundary;
5. choose the linear co-movement task and assign `stress` and `sleep_hours` to
   the two variable roles;
6. answer the bounded clarification prompts about clustering, independence, and
   weights for this synthetic sample;
7. review the experimental Pearson candidate and open its prepared configuration;
8. confirm the method, roles, missing-data policy, and noncausal boundary; and
9. start the calculation with the separately enabled Run action.

For this fixture, the packaged-app audit displayed Pearson `r = -0.995` after
rounding, `p = 0.000` after display rounding, `n = 16`, and zero excluded rows.
Those values demonstrate this exact synthetic path; they are not recommendation-
validity or general statistical-accuracy claims.

The demo packet uses the same fixture and is kept in
[`docs/build-week/DEMO_SCRIPT.md`](docs/build-week/DEMO_SCRIPT.md).

## Judge smoke path

These commands do not require R and avoid changing user data. They write only
under the repository's ignored `.tmp` directory.

```powershell
New-Item -ItemType Directory -Force .tmp\judge-smoke | Out-Null
$env:MODORI_CACHE_DIR = (Resolve-Path .tmp\judge-smoke).Path + "\cache"
$env:MODORI_SETTINGS_PATH = (Resolve-Path .tmp\judge-smoke).Path + "\settings.json"
$env:MPLCONFIGDIR = (Resolve-Path .tmp\judge-smoke).Path + "\matplotlib"

.\.venv\Scripts\python.exe -m modori.app --engine-smoke `
  tests\fixtures\recommendation_benchmark\public\pilot\data\pilot-007-correlation.csv `
  .tmp\judge-smoke\engine.json

.\.venv\Scripts\python.exe -m modori.app --public-data-smoke `
  tests\fixtures\public_data_formats `
  .tmp\judge-smoke\public-data.json

.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider `
  tests\test_research_os_p1_catalog.py `
  tests\test_research_flow_coordinator.py `
  tests\ui\test_research_flow_presenter.py
```

Success is an exit code of `0`; the two JSON files must contain top-level
`"ok": true` values. This is a bounded judge path, not the complete release gate.

## Full local verification

The full suite contains independent Base R reference anchors. For the release
gate, install R 4.5.x separately and point Modori at its executable:

```powershell
$releaseState = (New-Item -ItemType Directory -Force .tmp\release-state).FullName
New-Item -ItemType Directory -Force `
  "$releaseState\local-app-data", `
  "$releaseState\temp", `
  "$releaseState\cache", `
  "$releaseState\matplotlib" | Out-Null

$env:MODORI_RSCRIPT = "C:\path\to\R\bin\Rscript.exe"
$env:LOCALAPPDATA = "$releaseState\local-app-data"
$env:TEMP = "$releaseState\temp"
$env:TMP = $env:TEMP
$env:MODORI_CACHE_DIR = "$releaseState\cache"
$env:MODORI_SETTINGS_PATH = "$releaseState\settings.json"
$env:MPLCONFIGDIR = "$releaseState\matplotlib"

.\.venv\Scripts\python.exe scripts\quality_gate.py `
  --with-package-check `
  --with-package-build `
  --with-packaged-launch `
  --with-slow-stats
```

This runs bytecode compilation, Ruff, Bandit, the source launch smoke, the full
pytest suite, dependency checks, a local PyInstaller build, packaged launch,
packaged engine and public-data smokes, and the separately marked slow statistical
checks. Missing R is not treated as statistical reference evidence. The fresh
Build Week result and exact environment are recorded in
[`docs/build-week/VERIFICATION.md`](docs/build-week/VERIFICATION.md).

## Optional local Windows package

To build only the unsigned one-folder package:

```powershell
.\.venv\Scripts\python.exe scripts\package_windows.py
.\.venv\Scripts\python.exe scripts\package_launch_smoke.py
.\.venv\Scripts\python.exe scripts\package_engine_smoke.py
.\.venv\Scripts\python.exe scripts\package_public_data_smoke.py
```

The executable is created at:

```text
dist\Modori\Modori.exe
```

`dist` is ignored by Git and no executable from it is part of the public Build
Week submission. Anyone who redistributes a binary must independently satisfy the
GPL and all third-party binary-distribution obligations; see
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## How Codex and GPT-5.6 were used

Modori is an existing project, so the repository does not present the whole
application as Build Week work. During the eligible period, Codex with GPT-5.6 was
used as an engineering collaborator to inspect the existing repository, implement
and test the bounded deterministic multi-round Research OS flow, challenge data and
authority boundaries, integrate independently developed histories, harden the
local benchmark kit, conduct a real packaged-app release-path audit, close two
contract mismatches exposed by that audit, and audit this submission. The owner retained product,
licensing, claim, hardware-operation, and release decisions.

Commit timestamps demonstrate when repository changes were made; they do not by
themselves prove which model was used. The required `/feedback` Session ID from the
primary build thread is therefore supplied separately in the Devpost submission.
The exact cutoff, pre-existing work, eligible commit groups, and evidence limits
are in the Build Week delta document.

Codex accelerated repository-wide contract searches, adversarial test construction,
history-preserving integration analysis, and the repeated comparison of UI wording
against executable behavior. The consequential decisions were not delegated to the
tool: the owner chose the closed six-task scope, local deterministic runtime, explicit
confirmation and no-auto-run boundaries, experimental wording, GPL-3.0-only
source-only release, and deferral of the unmeasured B5 hardware claim.

The prepared Devpost technical copy, screenshot plan, and final owner checklist are
kept in [`docs/build-week/DEVPOST_SUBMISSION.md`](docs/build-week/DEVPOST_SUBMISSION.md)
and [`docs/build-week/RELEASE_CHECKLIST.md`](docs/build-week/RELEASE_CHECKLIST.md).

## Known limitations and non-claims

- Research OS P1 covers only the six tasks listed above.
- There are zero verified external routes.
- Recommendation validity and expert equivalence have not been established.
- Modori has not been shown to outperform SPSS, a qualified researcher, or any
  other statistics package.
- The product is not evidence of complete statistical-method coverage or complete
  numerical correctness for every possible dataset.
- The full application UI is not completely bilingual. The main shell is
  Korean-first; English exists for report output and selected Research OS
  presentation contracts.
- Complete accessibility conformance has not been established.
- B4-R development-PC evidence does not establish a B5 low-cost HP laptop pass.
- Local execution does not establish research-design validity, causal validity,
  or suitability for a particular real study.
- No prebuilt or code-signed public binary is provided.

The canonical cross-surface wording is maintained in
[`docs/build-week/CLAIM_MATRIX.md`](docs/build-week/CLAIM_MATRIX.md).

## License and third-party material

Modori-authored source code is licensed under the GNU General Public License v3.0
only (`GPL-3.0-only`). See [`LICENSE`](LICENSE).

Dependencies, fonts, icons, and third-party test data retain their own terms and
attributions. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). The source
submission does not include a prebuilt dependency bundle.
