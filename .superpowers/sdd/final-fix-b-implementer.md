# Final Fix B Implementer Report

## Scope

- Worktree: `C:\Users\V\Desktop\TongTong\.worktrees\internal-windows-installer`
- Branch: `codex/internal-windows-installer`
- Base: `9a5ea39c99aeac69626350db0c0fb78551c44be8`
- Requested commit subject: `fix: exercise and preserve installed user state`
- No installer or package build was run. No HKCU access, artifact mutation,
  preserved-run cleanup, diagnostic cleanup, publication, push, or live
  installed lifecycle was performed.

## Root cause

The lifecycle sentinel did not prove installed-runtime state preservation. The
installer smoke created the sentinel itself, while launch, engine, and
public-data smokes routed cache/settings/Matplotlib state to unrelated
workspace `.tmp` locations. Cleanup consequently accepted only the sentinel,
and uninstall completion checked selected known paths instead of the whole
install root.

## Implementation

- Added optional `--state-root` and matching Python parameters to all three
  package smoke scripts.
- Extended the shared package environment boundary so an explicit root maps
  exactly to `cache`, `settings.json`, and `matplotlib` under its resolved path,
  while preserving standalone `.tmp` defaults, offscreen Qt, and workspace R
  runtime stripping.
- Explicit state-root setup does not pre-create cache or Matplotlib state. The
  routed Modori runtime must create those directories, making the lifecycle
  state-exercised check meaningful.
- Deferred launch-smoke Modori imports until after the routed environment is
  applied, so Matplotlib/cache initialization observes the explicit root.
- Added the same resolved `adapter.user_state_dir` to every installed package
  smoke command and required the sentinel plus concrete `cache` and
  `matplotlib` directories after all three smokes and before repair.
- Extended bounded uninstall polling to require lexical absence of the entire
  install root. The presence predicate uses `lstat()`, so dangling symlink or
  junction/reparse entries cannot be mistaken for absence; unexpected I/O
  uncertainty fails closed.
- Post-uninstall cleanup rechecks sentinel/cache/Matplotlib survival, proves the
  state root is a direct child of a valid compact `r-<12-hex>` run root, and
  inventories every descendant before deleting anything. Every descendant
  must resolve inside the state root and must not be a symlink,
  junction/reparse point, or unsupported filesystem type.
- Only after the complete inventory passes are validated files unlinked and
  validated directories removed bottom-up. The state root is removed last;
  sibling lifecycle logs remain preserved.
- Updated the file-operation audit to record `lstat`, whole-install-root
  polling, routed state, validation-before-delete, bounded recursive cleanup,
  reparse refusal, and preserved sibling logs.

## TDD evidence

1. Baseline focused package/lifecycle suite: `64 passed`.
2. Package state-root RED: clean run produced `5 failed` for the missing shared
   parameter, launch environment parameter, and three CLI paths. GREEN reached
   `23 passed`, then `25 passed` after import-order and non-precreation
   regressions were added.
3. Lifecycle RED: `5 failed` for missing command arguments/state gate and the
   falsely accepted unknown install-root residual. GREEN reached `51 passed`.
4. Recursive-cleanup RED: `4 failed` for nested routed state and actual Windows
   directory symlink/junction cases. GREEN reached `52 passed`.
5. Audit wording RED: `1 failed`; GREEN reached `3 passed`.
6. Launch import-order RED: `1 failed`; GREEN reached `1 passed`.
7. Explicit-state non-precreation RED: `1 failed`; GREEN reached `1 passed`.
8. Review regression RED used a real dangling Windows install-root symlink:
   `is_symlink()` was true, `exists()` was false, and uninstall verification
   incorrectly returned. The `lstat()` presence fix made the focused test pass
   and the full lifecycle file reached `53 passed`.

The symlink and junction cleanup regressions both used real Windows filesystem
objects in the test-owned `.test-tmp` fixture and passed without skips in final
verification.

## Review

A read-only code review found one Important issue: `Path.exists()` could miss a
dangling install-root reparse entry. The issue was reproduced before the fix,
covered by the regression above, and corrected with fail-closed lexical
presence checks. Narrow re-review approved the correction with no remaining
Critical, Important, or Minor issue.

## Final verification

- Focused package-environment/package-smoke/lifecycle slice:
  `78 passed in 1.66s`.
- Complete installer regression slice (`installer_contract`, Inno contract,
  builder, lifecycle, quality gate, and file-operation audit):
  `106 passed in 0.77s`.
- Standalone file-operation audit: `3 passed in 0.03s`.
- `python -m ruff check src tests scripts`: `All checks passed!`.
- `git diff --check`: exit `0`, no output.

## Remaining concern

This is unit/regression evidence only. A live installed lifecycle was
intentionally not rerun because this corrective task explicitly prohibited
installer/build and HKCU actions.
