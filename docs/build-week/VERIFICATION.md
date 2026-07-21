# Build Week Verification Record

Status: **final claim-fidelity source and isolated package candidate verified; cold visual performance remains uncharacterized**

This record distinguishes commit-bound historical evidence, incomplete or failed
observations, fresh release-lane checks, and the final claim-fidelity source gate. An
interrupted run, a check on an earlier tree, a load-sensitive visual pass, or a local
package smoke is not silently promoted to a broader release claim.

## Source identities and target

| Item | Value |
| --- | --- |
| Release branch | `codex/modori-build-week-release-p0` |
| Starting integrated HEAD | `eaa0e802a0c64f6619297432f129be4d198a79ea` |
| Sealed source-release baseline | `616955232d91aa322da66cb21a8865ec686ba87f` |
| Functional-usability candidate | `b368cdcf208d04509717826bc6b0ab7e7b72ba7e` |
| Local two-parent integration | `4260ed862a74fee094b9a94c42ffe95fd7fe4c64` |
| Historical immutable P0 functional freeze | `b2235dabbe01258ae68be4f49bcbb974777a9578` |
| Direct documentation audit correction | `8e4e6f91cd05e51fcb5d0f3b0fbd4c0b3ff235bc` |
| Final source-under-test / claim-fidelity fix | `42538443501b817cedd25f858224499f4a97322e` |
| Package-metadata README child | `35e5d706861a0a4a8d8333c97df5d21a95a52e38` |
| Audited public default HEAD | `0413059b993ae5bb28190907badb7733d94f3f64` |
| Target OS | Windows 11 x64 |
| Target Python | CPython 3.12.10 |
| Dependency constraints | `constraints/build-week-windows-py312.txt` |
| Full-gate R reference runtime | R 4.5.3 (`2026-03-11 ucrt`) |
| Public binary | none |

The `b223` commit remains an immutable historical functional freeze. Its direct child
`8e4e6f91` corrected evidence attribution without changing `src/` or `tests/`.
`4253844` then made one bounded claim-fidelity correction: ResultsPanel Cronbach's
alpha help is exposed only when an actual reliability `DisplayResult` exists, while
empty, correlation, and unsupported result states fail closed. It did not create or
infer a passport- or ledger-backed reason for selecting an analysis. `35e5d70` changes
only the top-level README used as package metadata; its `src/` and `tests/` trees are
identical to `4253844`. The documentation-only child produced by this evidence freeze
must retain the `35e5d70` README, `src/`, and `tests/` tree identities exactly.

## Initial baseline observation

The first full pytest observation used isolated cache/settings paths and the shared
Python 3.12.10 environment. The execution tool stopped it after 1,587.1 seconds at
approximately 31% completion. Four failures had appeared at 15%, so the run is
**incomplete and is not recorded as passing**.

All four failures came from `tests/test_factorial_anova_references.py`. Its R helper
did not discover the existing Rscript because this Codex worktree is nested beneath
an alternate linked-worktree layout rather than the older expected layout. With
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
changed afterward. The rebuilt final wheel is recorded below.

## Historical pre-integration Windows package and live judge-flow audit

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
`canRerun is True`; that assertion failed before the second fix. The sealed source
baseline first used a current-pipeline forwarding boundary and delegated correlation
migration and validation to `CorrelationStep`. The related source cohort then
completed:

```text
98 passed in 9.44s
exit code 0
```

That pre-integration rebuilt package completed a packaged QML/library payload-load
smoke plus two real executable subprocess smokes:

```text
packaged QML/library payload-load smoke  7.5s
actual executable engine smoke          23.8s
actual executable public-data smoke     23.2s
all exit code 0
```

The payload-load script did not start the packaged executable, so its duration is not
an executable launch or cold-start measurement.

That historical live pass then completed confirmation, the separate Run action, and
the result view. For the exact synthetic fixture, the UI displayed:

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
Those numbers are historical and were replaced by the final local package identity
below.

## Functional-usability candidate and local integration

The later functional-usability candidate replaced the forwarding adapter with the
direct live provider
`pipeline_ops_provider=lambda: owner._services.pipeline_ops` and retained a broader
real import-to-Word-export regression. It also integrated the Royal Blue entry and
workspace, session-level Korean/English controls across the reviewed workflow, and a
dataset-bound Variable Meaning Gate before the first durable Research OS request.

One automated actual-QML Korean beginner E2E exercised a one-column synthetic numeric-
distribution path through import, metadata review, the meaning gate, three bounded
clarifications, exact configuration confirmation without calculation, a separate Run,
Word export, metadata drift, blocked rerun, and explicit replan. That E2E is not
evidence that all six tasks, both languages, or arbitrary datasets completed the same
live path.

Candidate-bound results at
`b368cdcf208d04509717826bc6b0ab7e7b72ba7e` were:

```text
final non-gallery suite: 3289 passed, 5 skipped in 485.87s
Ruff: passed
compileall: passed
source launch smoke: passed
```

The broader candidate-bound visual matrix at `b368cdc` passed structural,
localization, privacy, response, and image-digest checks, but cold `state_render_ms`
was load-sensitive. Independent observations included roughly 200–217 ms passes and
roughly 292–303 ms failures against the unchanged 250 ms threshold; the broader
recorded range was 209.77–306.15 ms. This is not a stable performance
characterization and is not recorded as a pass. Neither the threshold nor the
measurement code was relaxed.

The release-side work was first preserved at `6169552`. A local `--no-ff --no-commit`
merge then reported exactly the two predicted conflicts. Both were resolved by meaning
in favor of the direct provider and broader E2E, with the superseded adapter and test
remaining recoverable in `6169552`. Before the merge commit, the affected integration
cohort completed:

```text
57 passed in 11.31s
exit code 0
```

The resulting merge commit is
`4260ed862a74fee094b9a94c42ffe95fd7fe4c64`, with parents `6169552` and
`b368cdc`. These are integration checks, not the final merged-source non-gallery gate.

### Historical `b223` integrated Windows UI audit boundary

A real packaged Windows session on the final integrated source, before the last
correlation-prose wording-only patch, directly observed all of the following:

- the Royal Blue entry and work surfaces;
- the 16×2 synthetic import work surface and its read-only source notice;
- a recovered experimental `stats.correlation` candidate for outcome `stress`,
  predictor `sleep_hours`, Pearson correlation, pairwise missingness,
  `experimental: true`, and `automatic_run: false`;
- confirmation producing no result while enabling the separate Run action;
- the Run result with display-rounded `r = -0.995`, `p = 0.000`, `n = 16`, and
  `excluded = 0`, plus the same values in `Open wide table`; and
- the report dialog with English selectable and `Save to Word` enabled. The OS save
  dialog was not opened and no Word file was written during this manual session.

That session inherited a recorded local Research OS transaction and recovered
directly to the candidate. It therefore did **not** directly re-observe task
selection → Variable Meaning Gate → bounded clarification → candidate on the final
integrated package. That fresh sequence, the corrected import-preview evidence line,
and actual Word-file creation are supported by the exact QML/unit/integration tests,
not by this final manual session. The last wording-only patch changed the English
correlation prose to begin `This result summarizes ...`; its focused red/green tests
and adjacent cohort were rerun, but the GUI was not manually reopened afterward.
The package was then rebuilt from that source and covered by the three final package
smokes recorded below. This boundary prevents the manual audit from being promoted
to an all-screen, all-language, or all-export claim.

## Failed all-tests observation and resolution

One all-tests observation on the merged pre-final tree was allowed to finish. It is
recorded as a **failed observation**, not rewritten as a pass:

```text
6 failed, 3290 passed, 5 skipped, 4 errors in 499.87s
exit code 1
```

That command accidentally selected installed R 4.6.1 instead of the pinned R 4.5.3
reference runtime and ran inside the Codex filesystem sandbox with its temporary
directory beneath the worktree. The ten non-passing outcomes were separated rather
than hidden or made green by relaxing a threshold:

| Outcome | Root cause and bounded recheck |
| --- | --- |
| One factorial-reference failure | Wrong R runtime selected. The exact test passed with workspace-local R 4.5.3: `1 passed in 3.64s`. Reference metadata was not changed. |
| Three Office-kit verifier failures | Python-created private temporary directories became inaccessible to the sandbox token. The same three tests passed under normal Windows permissions: `1 passed in 0.81s`, then `2 passed in 0.94s`. |
| One native entry-capture timeout | The loaded all-tests process exceeded its 60-second subprocess limit. The exact 1366×768 six-state test passed under normal Windows permissions: `1 passed in 4.87s`. |
| One session-localization failure | Real source regression: the new correlation-validation message lacked an English session copy. The existing test failed with that one literal, the minimal mapping was added, and the exact test passed in 3.81s; the adjacent localization/validation cohort then reported `41 passed in 4.73s`. |
| Four visual-gallery setup errors | The module-scoped pytest temporary directory hit the same sandbox permission boundary before capture. One representative full 30-item gallery contract test passed under normal Windows permissions in 42.53s. Its single-run state-render p95 was 241.961 ms and maximum was 304.838 ms; this does not override the mixed historical observations or establish stable performance. |

After that source fix and environment correction, a pre-demo-polish merged-source
**non-gallery** suite completed under normal Windows permissions with the pinned R
runtime and isolated application state:

```text
3289 passed, 5 skipped in 370.22s (0:06:10)
exit code 0
```

A subsequent packaged Windows UI audit of the exact synthetic demo path found three
visible English-session defects: the import evidence remained Korean, the
configuration-confirmed status remained Korean, and correlation prose prefixed an
English sentence with the Korean title. Three focused tests reproduced those defects
before the fixes (`3 failed`). Exact message mappings and the correlation English
title were then corrected without changing workflow or statistical behavior. The
focused tests passed (`3 passed in 3.57s`), and the adjacent import, localization,
correlation-reporting, and actual-QML novice E2E cohort reported `30 passed in 6.67s`.

The historical `b223` release-tree **non-gallery** suite was then run once more with
R 4.5.3, isolated application state, and normal Windows permissions:

```text
3290 passed, 5 skipped in 425.65s (0:07:05)
exit code 0
```

The gallery file was deliberately excluded from this broad count and remains covered
by the separate evidence above. No repeat capture was selected merely for being fast,
and the unchanged 250 ms cold-render threshold remains in the test.

## Final claim-fidelity source gate

The ResultsPanel affordance audit found that a valid Cronbach's alpha explanation was
labelled as though it could explain why any analysis had been selected. No such
generic selection provenance existed. The correction at
`42538443501b817cedd25f858224499f4a97322e` added a typed controller property and
made the QML button visible only when explain mode is active and at least one actual
reliability `DisplayResult` exists. Empty, correlation, and unsupported result states
hide it. The Korean and English labels now describe Cronbach's alpha itself. This is
removal of a misleading affordance, not a new selection-rationale feature.

The first exact non-gallery run on that working tree, before its integration-ledger
binding was updated, was allowed to finish and is retained as a failed observation:

```text
2 failed, 3290 passed, 5 skipped in 390.26s
exit code 1
```

One failure was the intentionally stale shared-path blob binding in the committed
integration ledger. The other was a Word publish exception that appeared only in that
full-suite process. After the ledger was rebound to the actual controller and strings
blobs, the actual-QML novice E2E completed in ten separate processes with `10/10`
exit-code-zero results. The Word exception did not recur in that sequence or the fresh
full run below. No claim is made that the exception was impossible, or that load was
its cause.

A new isolated state was then used for the exact non-gallery command with pinned
R 4.5.3 and normal Windows permissions:

```text
3292 passed, 5 skipped in 367.62s
exit code 0
```

`compileall`, Ruff, Bandit, the source launch smoke, and `pip check` all returned exit
code `0`. A separately run representative visual-gallery contract reported
`1 passed in 39.19s` against the unchanged 250 ms gate. That single pass does not
override the historical 292–303 ms failures or establish stable cold-render
performance.

| Tree at `4253844` | Git tree OID |
| --- | --- |
| `src/` | `6491c3d59435fd042001b0c866d2ee87bfdf5247` |
| `tests/` | `2eb3c18d7532d225559756fc3f119a0f36d88d5b` |

The README-only child `35e5d706861a0a4a8d8333c97df5d21a95a52e38` retains both
tree OIDs.

## Final isolated package candidate and fresh English GUI audit

The clean `35e5d70` tree was used to build an ignored, local-only wheel and unsigned
PyInstaller one-folder candidate. Neither artifact is published by the source-only
submission.

| Artifact | Final local identity |
| --- | --- |
| Wheel | `modori-0.1.0-py3-none-any.whl`; 652,603 bytes; SHA-256 `4cbfa9b7f82e3245b3c2ad2d44ddffdfe87b376cf3fa972d1b100961935b3be1` |
| Wheel metadata | Metadata 2.4; `modori` 0.1.0; `GPL-3.0-only`; LICENSE member byte-equivalent after newline normalization; long description equal to the normalized `35e5d70` README |
| Executable | `Modori.exe`; 31,469,864 bytes; SHA-256 `81b76763dcff2faa4f33ea8ec838a3ca6b3492ab7fa2664f984b01edbab2c6b1` |
| One-folder payload | 4,491 files; 625,438,455 bytes |
| ResultsPanel source/package binding | byte-identical; SHA-256 `d1d899f9f2bd3b496361f12c8348fa07ab64743dcd1efad7c8f1fef34510dc72` |
| Pre-existing `dist` | unchanged at 4,491 files; 625,437,998 bytes; tree SHA-256 `86f8174c19d3679726067d6820f65b442951f7bde444ebfd87b17d7dc05aa5f9` |

Two failed build observations are retained separately from the successful candidate.
The first wheel attempt stopped with a sandbox build-tracker `PermissionError`. The
first PyInstaller attempt relocated the spec while leaving add-data sources relative,
so PyInstaller resolved them below the spec directory and failed. The successful
fresh build used the same hidden imports, data destinations, and environment boundary,
with absolute source paths for the relocated spec. No product threshold or dependency
claim was changed.

The successful PyInstaller build retained two known warnings: its installed PySide6
tree did not contain the optional Qt Labs Asset Downloader plugin DLL requested by a
hook, and hidden import `scipy.special._cdflib` was not found.

| Candidate smoke | Process boundary | Result |
| --- | --- | --- |
| `package_launch_smoke.py` | packaged QML/library payload loaded by the current source Python process; packaged executable not started | exit 0 in 7.525s |
| `Modori.exe --engine-smoke` | actual executable subprocess | exit 0 in 24.230s; 22 checks |
| `Modori.exe --public-data-smoke` | actual executable subprocess | exit 0 in 3.615s; 10 cases |

The first row is not an executable launch or cold-start measurement.

The actual final executable was then opened with a fresh isolated application state,
English session language, `CASUAL MODE`, and a neutral Public copy of
`pilot-007-correlation.csv`. The following sequence was directly observed:

1. English import evidence, a 16×2 preview, and the read-only source notice;
2. Research OS noncausal boundary → linear co-movement, with `stress` and
   `sleep_hours` drafted before the Variable Meaning Gate;
3. explicit meaning confirmation, followed by all three bounded clarifications:
   no cluster, independent observations, and no weight;
4. an experimental Pearson candidate with `pairwise`, `p_adjust: none`,
   `automatic_run: false`, and the exact two roles;
5. configuration confirmation leaving the result empty and Word disabled while
   enabling a separate Run action; and
6. after Run, display-rounded `r = -0.995`, `p = 0.000`, `n = 16`, and
   `excluded = 0`, including the full wide table.

The misleading `Why this analysis was selected` affordance and the Cronbach
ResultsPanel help were absent both before and after the correlation result. The local
decision ledger contained eight hash-chained events. Its final passport recorded
`auto_selected: false`, required explicit configure-confirm-run, permitted an
association claim, and contained no external route.

The same session selected English in the report dialog and actually wrote:

```text
C:\Users\Public\Documents\ModoriDemo\P0Final-35e5d70-003\modori-output\report.docx
37,106 bytes
SHA-256 ae45cff0b3ffd2779455d4278de2cad4976cd342763c3f2c12208c6c7e435562
```

Visible paragraphs and table cells were English, included the Research OS
experimental-candidate limitation and the correlation result, and contained no
personal path. The only Hangul code points anywhere in the DOCX XML were the Office
theme font name `맑은 고딕` in `word/theme/theme1.xml`; they were not report prose.

The native input picker exposed a personal OneDrive label during selection. The
entire picker must therefore be removed from the video by a jump cut, and no picker
screenshot is submission evidence. Positive reliability-help visibility remains
attributed to the source actual-QML test plus the byte-identical packaged QML, not to
this manual correlation flow. Metadata-drift recovery remains attributed to the
existing numeric-distribution E2E, not to this manual flow.

Finally, `scripts/slow_stats_gate.py` was run exactly once on the `35e5d70` source
tree with pinned R 4.5.3, fresh state, and normal Windows permissions:

```text
4 passed, 3304 deselected in 34.77s
exit code 0
```

This result is separate from the exact-`b223` result with 3302 deselections.

## Previously accepted commit-bound evidence

These results remain bound to their recorded source and are not relabelled as fresh
final-release results.

| Evidence | Bound identity | Recorded result |
| --- | --- | --- |
| Integrated release gate | merge-tree evidence in `docs/qa/research-os-release-integration-evidence.md` | full source/package gate passed for that integration tree |
| Functional-usability candidate | `b368cdcf208d04509717826bc6b0ab7e7b72ba7e` | `3289 passed, 5 skipped`; Ruff, compileall, and source launch passed; cold render not stably characterized |
| Historical immutable functional freeze | `b2235dabbe01258ae68be4f49bcbb974777a9578` | non-gallery `3290 passed, 5 skipped`; historical wheel, package, GUI, and slow-statistics evidence retained below |
| Documentation attribution correction | `8e4e6f91cd05e51fcb5d0f3b0fbd4c0b3ff235bc` | direct `b223` child; README/evidence-only changes; `src/` and `tests/` unchanged |
| Final claim-fidelity source | `42538443501b817cedd25f858224499f4a97322e` | non-gallery `3292 passed, 5 skipped`; Cronbach help gated to actual reliability results; no generic selection rationale added |
| Package-metadata child | `35e5d706861a0a4a8d8333c97df5d21a95a52e38` | README-only child; `src/` and `tests/` identical to `4253844`; final candidate artifacts and fresh GUI audit bound here |
| Pre-final slow-statistics selection | pre-final release tree; not `b223` | `4 passed, 3301 deselected in 28.05s`; historical only and not a final-tree result |
| B4-R development-PC office kit | `989d5c5829e3d3de69ebda0f4fc88e6f76d16112` | `3233 passed, 13 skipped`; 300 sealed mutations rejected; three independent kit builds byte-identical |
| B4-R kit archive | SHA-256 `6f567b327ad53c68eff5f27623e494c1273f9a424e11896e99c5d9f5a0bb8d43` | recorded candidate for a later B5 measurement |
| B5 low-cost HP laptop | none | pending; no pass claimed |

## Historical `b223` release gates

| Gate | Required evidence | Status |
| --- | --- | --- |
| Historical local wheel metadata (`b223` artifact) | `modori-0.1.0-py3-none-any.whl`; 651,811 bytes; SHA-256 `42e8bc3fa5eb3edbebef3e76ac64d7f800def8fce15d658d42ffa0507572580a`; Metadata 2.4; normalized `b223` README body; `GPL-3.0-only`; LICENSE member | passed for `b223`; retained as historical evidence; not a public artifact |
| Judge engine smoke | copied synthetic input; exit 0; top-level `ok: true`; all generated files remained below ignored judge state | passed in 5.5s |
| Judge public-data smoke | exit 0 and top-level `ok: true` | passed in 11.9s |
| Judge Research OS cohort | four documented files, isolated `LOCALAPPDATA` and temp | `114 passed in 17.79s` |
| Compile / Ruff / Bandit / source launch / pip check | exit 0 without ignored failures | passed; Ruff reported `All checks passed!`, launch reported `launch-smoke-ok`, and pip reported no broken requirements |
| Historical release-tree non-gallery pytest (`b223`) | pinned R 4.5.3, isolated state, normal Windows permissions | `3290 passed, 5 skipped in 425.65s` |
| Historical representative visual-gallery recheck | one 30-item gallery contract under normal Windows permissions; unchanged 250 ms gate | `1 passed in 42.53s`; single-run p95 241.961 ms and maximum 304.838 ms; this is separate from the broader candidate-bound matrix and does **not** establish stable cold performance |
| PyInstaller check and local build (`b223` artifact) | PyInstaller 6.21.0, Windows 11, CPython 3.12.10 | passed; launcher 31,469,559 bytes, SHA-256 `0d468f4923cfaa6e0c92cd5a9ab69a1b80741bb70f6142695ff3762613ef35ab`; one-folder 4,491 files / 625,437,998 bytes |
| Packaged payload-load / engine / public-data smokes (`b223` package) | isolated local package state, all exit 0 | QML/library payload-load 7.51s; actual executable engine 23.12s; actual executable public-data 4.14s; payload-load is not executable launch evidence |
| Independently rerun slow statistics (`b223`) | exact `b223` extracted with `git archive`; pinned R 4.5.3; isolated state; normal Windows permissions | `4 passed, 3302 deselected in 43.91s`; exit code `0` |
| Documentation links, SRT/SVG syntax, claim scan, whitespace, Git state | no blocking defect | passed: 15 release files privacy-scanned; 14 local links valid; two SVGs valid XML; 11-cue SRT ends at 2:55; generated outputs untracked |

## Current final candidate gates

| Gate | Bound identity | Result |
| --- | --- | --- |
| Claim-fidelity non-gallery pytest | `42538443501b817cedd25f858224499f4a97322e` | `3292 passed, 5 skipped in 367.62s`; exit 0; gallery excluded |
| Source quality gates | `4253844` | compileall, Ruff, Bandit, source launch, and pip check exit 0 |
| Representative gallery | `4253844`; unchanged 250 ms threshold | `1 passed in 39.19s`; historical mixed timings retained; no stable cold-render claim |
| Final wheel | `35e5d706861a0a4a8d8333c97df5d21a95a52e38` | 652,603 bytes; SHA-256 `4cbfa9b7f82e3245b3c2ad2d44ddffdfe87b376cf3fa972d1b100961935b3be1`; metadata/license/README checks passed |
| Final one-folder candidate | `35e5d70`, source tree equal to `4253844` | executable 31,469,864 bytes; SHA-256 `81b76763dcff2faa4f33ea8ec838a3ca6b3492ab7fa2664f984b01edbab2c6b1`; 4,491 files / 625,438,455 bytes |
| Candidate smokes | final one-folder candidate | payload-load exit 0 in 7.525s; actual executable engine exit 0 in 24.230s; actual executable public-data exit 0 in 3.615s |
| Fresh packaged GUI | final one-folder candidate | full English/Casual correlation flow, explicit Run, exact result, and actual English Word creation directly observed |
| Current slow statistics | `35e5d70` source tree | `4 passed, 3304 deselected in 34.77s`; exit 0; R 4.5.3 |
| Evidence-document freeze | documentation-only child of `35e5d70`; README, `src/`, and `tests/` trees unchanged | eight authorized Markdown/SRT paths; five local links valid; two referenced SVGs valid XML and unchanged; 11-cue English SRT matches the demo narration and ends at 2:55; privacy, unresolved-token, claim, whitespace, and Git-scope checks passed |

The exact non-gallery scope for both the historical `b223` and final `4253844` source
uses explicit R and isolated state, temp, cache, and Matplotlib paths:

The command below assumes the separately installed pinned runtime is placed at the
ignored workspace-local path documented in the
[statistical reference environment](../specs/statistical-reference-environment.md).

```powershell
$releaseState = (New-Item -ItemType Directory -Force .tmp\final-release-state).FullName
New-Item -ItemType Directory -Force `
  "$releaseState\local-app-data", `
  "$releaseState\temp", `
  "$releaseState\cache", `
  "$releaseState\matplotlib" | Out-Null

$RRoot = (Resolve-Path .tools\r-env).Path
$env:PATH = "$RRoot\Library\bin;$RRoot\Scripts;$RRoot\lib\R\bin;$RRoot\lib\R\bin\x64;$env:PATH"
$env:MODORI_RSCRIPT = "$RRoot\Scripts\Rscript.exe"
$env:LOCALAPPDATA = "$releaseState\local-app-data"
$env:TEMP = "$releaseState\temp"
$env:TMP = $env:TEMP
$env:MODORI_CACHE_DIR = "$releaseState\cache"
$env:MODORI_SETTINGS_PATH = "$releaseState\settings.json"
$env:MPLCONFIGDIR = "$releaseState\matplotlib"

.\.tmp\build-week-venv\Scripts\python.exe -m pytest -q -p no:cacheprovider `
  --ignore=tests/ui/test_research_flow_visual_gallery.py
```

At `b223` that command produced 3290 passes; at the final `4253844` source it produced
3292. By contrast,
`scripts/quality_gate.py` invokes the full pytest suite without this exclusion, so a
quality-gate run includes the visual gallery and is **not** the reproduction command
for either non-gallery count. The exact-`b223` and current-`35e5d70`
slow-statistics audits each used:

```powershell
.\.tmp\build-week-venv\Scripts\python.exe scripts\slow_stats_gate.py
```

Known PyInstaller warnings from the current final local rebuild are retained:

- the installed PySide6 tree did not contain the optional Qt Labs Asset Downloader
  plugin DLL requested by its hook; and
- hidden import `scipy.special._cdflib` was not found.

All three candidate smokes succeeded despite those warnings. The fresh final-candidate
GUI sequence and Word creation were directly observed as bounded above. No inference
is made for an untested hidden-import path.
