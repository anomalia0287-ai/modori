# File Operations Audit - 2026-06-29

Scope: production Python files under `src/` and release scripts under `scripts/`
that call direct filesystem helpers:
`write_text`, `write_bytes`, `mkdir`, `unlink`, `replace`, `rmdir`, or `resolve`.

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
| `scripts/package_environment.py` | `mkdir`, `resolve` | Shared release-only environment boundary. It removes workspace R runtime directories from packaged build/run `PATH` values so R DLLs cannot contaminate the PySide6 package, and creates isolated Matplotlib, Modori cache, and settings paths under the workspace `.tmp` directory. It does not inspect or mutate user data. |
| `scripts/package_windows.py` | `mkdir` | Local release-build setup under the workspace `.tmp` directory. Not user-data cleanup. |
| `scripts/package_launch_smoke.py` | `mkdir`, `resolve` | Local smoke-test setup under the workspace `.tmp` directory and explicit executable/cwd normalization. Not product runtime deletion. |
| `scripts/package_engine_smoke.py` | `mkdir`, `resolve`, `unlink` | Local packaged-engine smoke setup under the workspace `.tmp/packaged-engine-smoke` directory. It creates a deterministic reference workbook, deletes only its own previous `result.json` before launch to prevent stale success, and reads the fresh packaged-app JSON. It does not delete user data. |
| `scripts/package_public_data_smoke.py` | `mkdir`, `resolve`, `unlink` | Local packaged public-data import smoke setup under the workspace `.tmp/packaged-public-data-smoke` directory. It deletes only its own previous `result.json`, runs the packaged app against checked-in public-data fixtures, and requires a fresh smoke JSON. It does not delete user data. |
| `scripts/stress_matrix.py` | `mkdir`, `write_text` | Local stress evidence generation under caller-selected output paths; release checklist uses ignored `.stress-matrix`. It creates deterministic synthetic datasets, JSON results, and report artifacts, not user-data cleanup. |
| `scripts/quality_gate.py` | `resolve` | Local release-gate environment setup only. It resolves the workspace-local `.tools/r-env/Scripts/Rscript.exe` path for pytest and slow statistical references, while package and ordinary command environments strip that runtime through `package_environment.py`. It does not create, modify, or delete files. |

## Decisions

- No new delete-capable product file operation is accepted without updating this
  audit and extending tests around its boundary.
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
