# Build Week Verification Record

Status: **final full gate pending after two live-path fixes**

This record distinguishes commit-bound historical evidence, incomplete observations,
fresh release-lane checks, and the one full gate still required on the final source.
An interrupted run, a check on an earlier tree, or a local package smoke is not
silently promoted to a final release pass.

## Source identities and target

| Item | Value |
| --- | --- |
| Release branch | `codex/modori-build-week-release-p0` |
| Starting integrated HEAD | `eaa0e802a0c64f6619297432f129be4d198a79ea` |
| Audited public default HEAD | `0413059b993ae5bb28190907badb7733d94f3f64` |
| Target OS | Windows 11 x64 |
| Target Python | CPython 3.12.10 |
| Dependency constraints | `constraints/build-week-windows-py312.txt` |
| Full-gate R reference runtime | R 4.5.3 (`2026-03-11 ucrt`) |
| Public binary | none |

## Initial baseline observation

The first full pytest observation used isolated cache/settings paths and the shared
Python 3.12.10 environment. The execution tool stopped it after 1,587.1 seconds at
approximately 31% completion. Four failures had appeared at 15%, so the run is
**incomplete and is not recorded as passing**.

All four failures came from `tests/test_factorial_anova_references.py`. Its R helper
did not discover the existing Rscript because this Codex worktree is nested beneath
`.codex/worktrees/<id>` rather than the older `.worktrees/<name>` layout. With
`MODORI_RSCRIPT` set to the existing runtime, that exact file completed as:

```text
15 passed in 29.79s
exit code 0
```

No test threshold, expected value, skip rule, or product code was changed to obtain
that result. The release gate sets `MODORI_RSCRIPT` explicitly.

## Fresh constrained environment

A new virtual environment at ignored path `.tmp\build-week-venv` was created with
CPython 3.12.10. The three top-level README setup commands completed, including the
editable `.[dev,packaging]` install under the committed constraints.

```text
constraint consistency problems: 0
pip check: No broken requirements found.
installed distributions counted for audit: 79, including the editable project and pip
```

The constraint set covers the runtime, development, and packaging install after
bootstrapping. It intentionally does not claim to lock `pip` itself, every isolated-
build bootstrap tool, other operating systems, or byte-identical builds.

An initial wheel metadata inspection on the pre-fix release tree found project name
`modori`, version `0.1.0`, metadata version `2.4`, `GPL-3.0-only`, the top-level README,
and license text. Its hash is intentionally omitted because source and documentation
changed afterward. The final wheel must be rebuilt and recorded below.

## Windows package and live judge-flow audit

The source was built locally with PyInstaller 6.21.0 as the ignored one-folder path
`dist\Modori\Modori.exe`. The package is unsigned, is not the public artifact, and
must remain accompanied by the rest of its one-folder payload when used locally.

The packaged application was exercised through the actual Windows UI with the public
synthetic fixture `pilot-007-correlation.csv`:

1. entry screen → `CASUAL MODE` → file-picker import and 16×2 preview;
2. Research OS noncausal boundary → linear co-movement → `stress` and
   `sleep_hours` roles → bounded clustering/independence/weight clarification;
3. experimental Pearson candidate → exact prepared-configuration review; and
4. explicit confirmation → separately enabled Run action → result and report dialog.

The first live pass found two P0 interoperability defects:

- after import, the preparation editor retained the initial pipeline-operations
  object instead of resolving the replacement import pipeline; and
- Research OS sealed an engine-supported correlation `pairs` form, while the UI run
  validator accepted only the manual `variables` form.

A regression test was first added to reproduce confirmation against a replaced
pipeline. It failed before the first fix. The test was then extended to require
`canRerun is True`; that assertion failed before the second fix. The minimal repairs
use a current-pipeline forwarding boundary and delegate correlation migration and
validation to `CorrelationStep`. The related source cohort then completed:

```text
98 passed in 9.44s
exit code 0
```

The rebuilt package completed all three isolated package smokes:

```text
package-launch-smoke-ok       7.5s
package-engine-smoke-ok      23.8s
package-public-data-smoke-ok 23.2s
all exit code 0
```

The final live pass then completed confirmation, the separate Run action, and the
result view. For the exact synthetic fixture, the UI displayed:

```text
method: Pearson
r: -0.995 (display-rounded)
p: 0.000 (display-rounded)
n: 16
excluded: 0
```

The report dialog also exposed both Korean and English output choices. This verifies
one bounded synthetic Windows path. It does not establish recommendation validity,
expert equivalence, full bilingual coverage, all-method correctness, or B5 hardware
performance.

The package produced immediately after these two fixes had a launcher-only SHA-256
of `32c6c981a4634a65a571b16890aa814ebe58e6266246ff26c14a8df2f5773924`, with
31,427,894 launcher bytes and a 4,489-file / 625,361,340-byte one-folder payload.
Those numbers are **provisional**, because the final full gate rebuild may replace
the local artifact. The final package identity below is authoritative.

## Previously accepted commit-bound evidence

These results remain bound to their recorded source and are not relabelled as fresh
final-release results.

| Evidence | Bound identity | Recorded result |
| --- | --- | --- |
| Integrated release gate | merge-tree evidence in `docs/qa/research-os-release-integration-evidence.md` | full source/package gate passed for that integration tree |
| B4-R development-PC office kit | `989d5c5829e3d3de69ebda0f4fc88e6f76d16112` | `3233 passed, 13 skipped`; 300 sealed mutations rejected; three independent kit builds byte-identical |
| B4-R kit archive | SHA-256 `6f567b327ad53c68eff5f27623e494c1273f9a424e11896e99c5d9f5a0bb8d43` | recorded candidate for a later B5 measurement |
| B5 low-cost HP laptop | none | pending; no pass claimed |

## Final release gates

The following rows remain pending until they are rerun on the final source after the
two live-path fixes. A pending row is not a pass.

| Gate | Required evidence | Status |
| --- | --- | --- |
| Final wheel metadata | exact bytes, SHA-256, metadata, README, and license | pending |
| Judge engine smoke | exit 0 and top-level `ok: true` | pending on final source |
| Judge public-data smoke | exit 0 and top-level `ok: true` | pending on final source |
| Judge Research OS cohort | exact selected count and exit 0 | pending on final source |
| Compile/Ruff/Bandit/source launch/full pytest/pip check | exact final counts, durations, and exit 0 | pending on final source |
| PyInstaller check/build and packaged smokes | exact final identity and all exit 0 | pending on final source |
| Separately marked slow statistics | all selected checks execute and pass | pending on final source |
| Documentation links, SRT/SVG syntax, claim scan, whitespace, Git state | no blocking defect | pending |

The full command uses explicit R and isolated state, temp, cache, and Matplotlib paths:

```powershell
$releaseState = (New-Item -ItemType Directory -Force .tmp\final-release-state).FullName
New-Item -ItemType Directory -Force `
  "$releaseState\local-app-data", `
  "$releaseState\temp", `
  "$releaseState\cache", `
  "$releaseState\matplotlib" | Out-Null

$env:MODORI_RSCRIPT = "C:\path\to\Rscript.exe"
$env:LOCALAPPDATA = "$releaseState\local-app-data"
$env:TEMP = "$releaseState\temp"
$env:TMP = $env:TEMP
$env:MODORI_CACHE_DIR = "$releaseState\cache"
$env:MODORI_SETTINGS_PATH = "$releaseState\settings.json"
$env:MPLCONFIGDIR = "$releaseState\matplotlib"

.\.tmp\build-week-venv\Scripts\python.exe scripts\quality_gate.py `
  --with-package-check `
  --with-package-build `
  --with-packaged-launch `
  --with-slow-stats
```

Known PyInstaller warnings from the pre-final rebuild are retained for comparison:

- the installed PySide6 tree did not contain the optional Qt Labs Asset Downloader
  plugin DLL requested by its hook; and
- hidden import `scipy.special._cdflib` was not found.

Both package smokes and the live path succeeded despite those warnings, but the final
gate must record them again rather than silently discarding them.
