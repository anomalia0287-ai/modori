# Build Week Public-P0 Functional Delta Ledger

Date: 2026-07-21 KST

## Scope and immutable references

- Writable lane before reconciliation: `codex/research-os-functional-usability` at `84f184e09acabfbe4ac8510507beb67b2375c815`.
- Public release tip inspected read-only: `c23164c2cf42857c24776c83ee3cfbd017e74b9e`.
- Shared merge base: `b368cdcf208d04509717826bc6b0ab7e7b72ba7e`.
- Release-side functional source commits:
  - `616955232d91aa322da66cb21a8865ec686ba87f`: current imported-pipeline operations and the correlation parameter-contract fix.
  - `b2235dabbe01258ae68be4f49bcbb974777a9578`: English correlation prose and missing English runtime-message mappings.
  - `42538443501b817cedd25f858224499f4a97322e`: reliability-only Cronbach explanation gate and corrected settings copy.
- Integration rule: no merge, cherry-pick, blanket side selection, or whole-file copy. Each behavior is either proven superseded or ported with its owning regression.

`git diff --name-status b368cdcf..c23164c2 -- src tests` returns exactly the following 12 paths. Blob IDs below are Git blob IDs, not filesystem hashes.

## Exact path inventory and disposition

| Path | Public release blob | Usability blob at `84f184e` | Reconciled working blob | Owning change | Disposition |
| --- | --- | --- | --- | --- | --- |
| `src/modori/correlation_reporting.py` | `cde27bbd` | `631c3af7` | `cde27bbd` | `b2235da` | Missing; exact English singular/plural prose ported. |
| `src/modori/ui/controller.py` | `eec243d1` | `a6dd5da1` | `083d4a6f` | `6169552`, `4253844` | Imported-pipeline boundary was already superseded by the later `pipeline_ops_provider` design; the missing typed reliability-result property was ported without reverting later report/import/recovery behavior. |
| `src/modori/ui/localization.py` | `4dd2619d` | `c6c608b5` | `b29cbb5a` | `b2235da` | Three missing English mappings ported into the larger current catalog. |
| `src/modori/ui/qml/components/ResultsPanel.qml` | `13a0bb70` | `6df27f85` | `13a0bb70` | `4253844` | Missing reliability-only explanation binding ported exactly. |
| `src/modori/ui/run_validation.py` | `e1482b7a` | `06196f94` | `e1482b7a` | `6169552` | Missing engine-owned correlation migration/validation contract ported exactly. |
| `src/modori/ui/strings.py` | `6ef310cf` | `fca239e4` | `e74c296c` | `4253844` | Meaning ported while retaining current Guided-mode and recovery catalog additions. |
| `src/modori/ui/strings_en.py` | `4a07d2f4` | `f18ab791` | `61257f6a` | `4253844` | Meaning ported while retaining current English Guided-mode and recovery additions. |
| `tests/test_correlation_reporting.py` | `d5e718a5` | `20ff85bc` | `d5e718a5` | `b2235da` | Release regression ported exactly. |
| `tests/ui/test_controller.py` | `762d0be3` | `ddeac368` | `1ee66734` | `4253844` | Reliability-result regression ported while retaining current report-replacement tests. |
| `tests/ui/test_importing_service.py` | `3125c8c1` | `6819267a` | `64be35c4` | `b2235da` | Header-evidence localization regression ported while retaining current Excel recovery tests. |
| `tests/ui/test_qml_runtime_load.py` | `02cee328` | `a63c084d` | `28158d15` | `4253844` | Actual-QML visibility regression ported while retaining current Guided-mode and layout runtime tests. |
| `tests/ui/test_session_localization.py` | `beae1ed6` | `55a463ca` | `beae1ed6` | `b2235da`, `4253844` | Both release localization regressions ported exactly. |

The following two current-lane test paths are outside the 12-path release diff but close the same semantics:

- `tests/ui/test_run_validation.py::test_validator_accepts_pair_scoped_correlation_from_research_os` is the direct regression for the sealed Research OS `pairs` shape. Before the fix it failed with `상관분석 변수는 문자열 목록이어야 합니다.`; after the fix it passed.
- `tests/ui/test_research_flow_controller.py::test_imported_pipeline_can_confirm_research_preparation_without_running` already proves the later provider-based imported-pipeline design. It passed before any controller edit, so the release `_CurrentPipelineOperations` wrapper was not copied back.

## Semantic conflict decisions

### Imported pipeline operations

The public release wraps a fixed `PipelineOperations` dependency with `_CurrentPipelineOperations`. The current usability lane instead changed `ResearchPreparationEditor` itself to accept `pipeline_ops_provider` and resolves the provider again at confirmation time. The current controller supplies `lambda: owner._services.pipeline_ops`. This is the same freshness guarantee at the owning abstraction and is covered by a stronger real-import test that also proves separate Run and Word export. Reintroducing the wrapper would duplicate the boundary and make the provider contract harder to reason about.

### Correlation parameters

Research OS seals one exact `pairs` entry. The old UI validator accepted only a `variables` list even though `CorrelationStep` supports both representations through `migrate_params` and `validate_params`. The reconciliation delegates to that engine-owned contract, converts the clean variables to strings, and then retains the UI's known-variable check. It does not broaden the engine method set or weaken schema validation.

### Cronbach explanation

The previous button claimed to explain why an analysis was selected but always opened the Cronbach-alpha explanation, including on correlation results. The reconciled property inspects typed `DisplayResult` instances and exposes the action only when a reliability result is present and explanation mode is enabled. This removes a false selection-rationale claim; it does not add a recommendation-validity claim.

### English claim fidelity

The release English correlation prose previously began with a Korean title, and three controller/import/validator messages fell through to Korean. The port adds only the release-proven strings and retains unknown technical details unchanged, preserving the existing fail-visible localization policy.

## TDD observations

1. Research OS `pairs` regression: observed RED with the exact variables-list error; then `1 passed`, followed by `26 passed` for all of `tests/ui/test_run_validation.py`.
2. Public-P0 claim-fidelity cohort: after porting tests but before production, seven tests failed for the expected missing behaviors: two English prose assertions, header-evidence localization, confirmation localization, QML binding, typed controller property, and actual-QML button lookup.
3. After the minimal production port, the same focused command passed `8 passed in 3.41s`, including the `pairs` regression.

4. Complete release-delta cohort:

   ```text
   python -m pytest -p no:cacheprovider tests/ui/test_run_validation.py tests/ui/test_research_flow_controller.py tests/ui/test_importing_service.py tests/ui/test_session_localization.py tests/test_correlation_reporting.py tests/ui/test_controller.py tests/ui/test_qml_runtime_load.py -q
   155 passed in 32.55s
   exit 0
   ```

Broader repository verification remains a separate gate; this ledger does not pre-claim it.
