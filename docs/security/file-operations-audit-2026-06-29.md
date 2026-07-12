# File Operations Audit - 2026-06-29

Scope: production Python files under `src/` and release scripts under `scripts/`
that call direct filesystem helpers:
`copyfile`, `copytree`, `scandir`, `write_text`, `write_bytes`, `mkdir`, `unlink`,
`replace`, `rmdir`, `resolve`, or `lstat`,
plus the Inno Setup `[InstallDelete]` boundary.

Guard: `tests/test_file_operation_audit.py` fails when a new product file starts
using one of these operations without being added to this audited allowlist.

## Audited Files

| File | Operations | Boundary |
| --- | --- | --- |
| `src/modori/path_policy.py` | `resolve` | Central path validation helper. Rejects relative paths and symlink/junction ancestors before returning configured paths. |
| `src/modori/app.py` | `mkdir`, `write_text` | Hidden `--engine-smoke` and `--public-data-smoke` packaging gates only. The normal QML app path does not invoke these branches; the CLI writes diagnostic JSON payloads to caller-supplied smoke output paths for release verification. |
| `src/modori/public_data_smoke.py` | `mkdir`, `write_text` | Hidden public-data release verification helper used only through `--public-data-smoke`. It reads checked-in or payload fixtures and writes one diagnostic JSON result to the caller-supplied smoke output path. |
| `src/modori/cache.py` | `resolve`, `mkdir`, `write_text`, `unlink` | Cache roots are selected through `resolve_secure_directory_path` where possible. `_ensure_cache_dir` creates only the selected cache directory, rejects link/junction targets, probes writability with a random temp filename, and deletes only that probe. |
| `src/modori/ui/chart_assets.py` | `mkdir`, `unlink` | Result-panel chart preview writes a random PNG filename only under the managed `cache/charts` directory. Failure cleanup deletes only that just-selected partial PNG path and returns a display note instead of touching user files. |
| `src/modori/ui/settings.py` | `resolve`, `mkdir`, `write_text`, `replace`, `unlink` | Settings path is either a secure absolute `.json` file or the managed cache. Writes go to a same-directory random temp file and then atomically replace the target; cleanup deletes only that temp path. |
| `src/modori/ui/result_binding.py` | `resolve`, `unlink` | Obsolete chart cleanup deletes only image files under the managed `cache/charts` directory after resolving both the cache root and candidate path. |
| `src/modori/ui/session.py` | `resolve` | Recent-file storage records a resolved path string only; it does not read, write, or delete the referenced file. |
| `src/modori/ui/worker.py` | `resolve`, `write_text` | Engine exception traces are written only when explicitly enabled by `MODORI_DEBUG_ENGINE_ERRORS=1` or an executable-adjacent `enable-engine-debug` sentinel. The file is written under the managed Modori cache directory and is not part of the normal user-facing error path. |
| `src/modori/steps/reporting.py` | `mkdir`, `resolve`, `unlink`, `rmdir` | `ReportStep` is not allowed in untrusted project JSON. Report paths reject direct output aliases, path separators in filenames, symlink output targets, and chart dirs outside `output_dir`. Failure cleanup deletes only created report/chart files under `output_dir` and removes the output directory only when this run created it. |
| `src/modori/knowledge/loader.py` | `resolve` | Read-only package data root resolution. No mutation. |
| `src/modori/ui/resources.py` | `resolve` | Read-only QML resource root resolution. No mutation. |
| `scripts/build_installer.py` | `copyfile`, `lstat`, `mkdir`, `replace`, `resolve`, `scandir`, `write_bytes` | Before creating a run root or snapshot file, the builder validates `WORKSPACE`, `.tmp`, and `.tmp/ib` component-by-component with `lstat` without following links, rejecting every symlink/junction/reparse point, non-directory, or resolved escape; it creates missing components one at a time and revalidates the unique run root after exclusive creation. At frozen-input entry after package-build return, and again immediately before snapshot creation, it revalidates the supplied staging ancestry component-by-component without following links so replacement during the package build cannot redirect a snapshot write. It then creates a deterministic full-tree snapshot and exact installer script copy inside one unique compact `.tmp/ib/<commit12>-<uuid12>` staging tree, using fixed children including `s/p`, `s/modori.iss`, `so`, `po`, `dp`, `do`, and `c`; an existing run name raises without altering its content. The lexical workspace-to-package boundary and every descendant are enumerated by non-following `scandir`, reject any link or junction/reparse point, and require resolved containment before hash/copy traversal. Relative paths, sizes, and content SHA values are verified before and after copying. Before any compiler output or ISCC call, the authenticated frozen inventory and resolved snapshot root compute the actual compiler source maximum in strict UTF-16 code units across files, directories, and directory search wildcards (including root and directory `\*`) and fail closed above `240`; an inventory with no files also fails closed. Package smokes and the smoke/production compilers use the frozen payload, while a staging-owned tiny downgrade payload contains only its sentinel `Modori.exe` and uses the same frozen script. The selected compiler must equal registered `InstallLocation\ISCC.exe`; its registered version, actual fixed file version, and uppercase SHA256 are recorded separately and re-read before and after every ISCC invocation. The builder then, after candidate materialization, requires exactly three regular non-reparse candidate files and finally revalidates source, frozen/live input, and compiler evidence immediately before return or publication. Build-only mode is staging-only and cannot publish, publication requires successful installed lifecycle verification, and all staging evidence is preserved on failure. A verified candidate is published only by directory move to a new immutable `dist/installer/<build-id>` path. It does not delete user data. |
| `scripts/installer_contract.py` | `write_text` | The contract measures source, payload-path, installer, and SHA256 evidence, then writes `release-manifest.json`, the smoke manifest, or `SHA256SUMS.txt` only to caller-selected staging paths. It does not select or delete user paths. |
| `scripts/installer_smoke.py` | `lstat`, `mkdir`, `resolve`, `rmdir`, `unlink`, `write_bytes`, `write_text` | Lifecycle smoke writes only under a unique `.tmp/installer-smoke/r-<12-hex>` tree and routes installed package cache, settings, and Matplotlib state into its direct-child `user-state` tree. Before repair it requires the sentinel plus routed cache and Matplotlib directories. After bounded polling proves the registration, shortcut, and entire install root are absent, cleanup revalidates `user-state` as a direct child of the compact run root, proves every descendant resolves inside it and is not a symlink/junction/reparse point, then performs recursive bottom-up removal of only that test-owned state tree; sibling logs remain preserved. |
| `installer/modori.iss` | `[InstallDelete]` | Repair cleanup deletes only the installer-owned `{app}\Modori` payload tree. It never targets product user state in `%LocalAppData%\Modori\cache`; that cache remains outside the per-user install tree and outside this delete boundary. |
| `scripts/package_environment.py` | `mkdir`, `resolve` | Shared release-only environment boundary. It removes workspace R runtime directories from packaged build/run `PATH` values so R DLLs cannot contaminate the PySide6 package. Standalone smokes create isolated Matplotlib, Modori cache, and settings paths under workspace `.tmp`; installed lifecycle smokes instead supply one resolved, unique test-owned state root and route all three paths beneath it. It does not select or clean product user data. |
| `scripts/package_windows.py` | `mkdir` | Local release-build setup under the workspace `.tmp` directory. Not user-data cleanup. |
| `scripts/package_launch_smoke.py` | `mkdir`, `resolve` | Local smoke-test setup under the workspace `.tmp` directory and explicit executable/cwd normalization. Not product runtime deletion. |
| `scripts/package_engine_smoke.py` | `mkdir`, `resolve`, `unlink` | Local packaged-engine smoke setup under the workspace `.tmp/packaged-engine-smoke` directory. It creates a deterministic reference workbook, deletes only its own previous `result.json` before launch to prevent stale success, and reads the fresh packaged-app JSON. It does not delete user data. |
| `scripts/package_public_data_smoke.py` | `mkdir`, `resolve`, `unlink` | Local packaged public-data import smoke setup under the workspace `.tmp/packaged-public-data-smoke` directory. It deletes only its own previous `result.json`, runs the packaged app against checked-in public-data fixtures, and requires a fresh smoke JSON. It does not delete user data. |
| `scripts/stress_matrix.py` | `mkdir`, `write_text` | Local stress evidence generation under caller-selected output paths; release checklist uses ignored `.stress-matrix`. It creates deterministic synthetic datasets, JSON results, and report artifacts, not user-data cleanup. |
| `scripts/quality_gate.py` | `resolve` | Local release-gate environment setup only. It resolves the workspace-local `.tools/r-env/Scripts/Rscript.exe` path for pytest and slow statistical references, while package and ordinary command environments strip that runtime through `package_environment.py`. It does not create, modify, or delete files. |

## Decisions

- No new delete-capable product file operation is accepted without updating this
  audit and extending tests around its boundary.
- Installer repair cleanup remains limited to `{app}\Modori`; the application
  cache at `%LocalAppData%\Modori\cache` is user state and is never an
  `[InstallDelete]` target.
- `ReportStep`, table imports, and regression imports remain blocked from
  untrusted project JSON, so attacker-controlled project files cannot trigger
  report output writes or cleanup.
- Direct helper calls such as `render_chart` and `write_docx` are treated as
  trusted internal/reporting API entry points. User-facing project loading must
  go through `Pipeline.from_json`, which rejects those IO steps unless trusted.

## Residual Risk

- Filesystem race conditions between path validation and write/delete operations
  are reduced but not eliminated. The current product stance is local desktop
  hardening, not a multi-tenant sandbox guarantee.
- Relative report `output_dir` remains allowed for trusted workflows and resolves
  against the current working directory. Untrusted project JSON cannot invoke it.
