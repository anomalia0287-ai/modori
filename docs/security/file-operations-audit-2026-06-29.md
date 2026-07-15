# File Operations Audit - 2026-06-29

Scope: production Python files under `src/` and release scripts under `scripts/`
that call direct filesystem helpers:
`write_text`, `write_bytes`, `mkdir`, `unlink`, `replace`, `rmdir`, `resolve`, or
`shutil.rmtree`.

Guard: `tests/test_file_operation_audit.py` fails when a new product file starts
using one of these operations without being added to this audited allowlist.

## Audited Files

| File | Operations | Boundary |
| --- | --- | --- |
| `scripts/benchmark_counterfactual_clarification.py` | `mkdir`, `write_text` | Developer-only formal-policy benchmark. It performs no dataset discovery and has no product entry point, network client, deletion, rename, or persistence integration. Without `--output` it writes canonical JSON to stdout only. With `--output`, it creates the caller-selected parent and overwrites exactly that caller-selected evidence file; repository practice uses ignored `.tmp/counterfactual-clarification-evidence.json`. The caller-selected overwrite is an explicit developer CLI boundary, not an operation reachable from user projects or the packaged product. |
| `scripts/benchmark_research_memory.py` | `shutil.rmtree` | Developer-only Decision Ledger benchmark. It creates a UUID-named directory below the worktree's existing `.test-tmp` root, prints metrics to stdout only, verifies the exact parent and `research-memory-benchmark-` prefix, and recursively removes only that owned temporary directory. It never runs in the product or writes benchmark evidence into the repository. |
| `scripts/build_office_research_memory_kit.py` | `mkdir`, `resolve`, `unlink`, `shutil.rmtree` | Developer-only sealed-kit builder. It requires a clean committed source snapshot, an exact source allowlist, and the pinned official Python archive digest and inventory. It stages only below a UUID-named `.office-kit-build-` directory under the caller-selected `dist` root, refuses existing delivery files, finalizes by a same-volume hard link, and deletes only that verified staging directory or a just-created incomplete delivery hard link. It never copies `.git`, environments, fixtures, datasets, or user files and has no network client. |
| `scripts/run_office_research_memory_benchmark.py` | `resolve`, `shutil.rmtree` | Offline target-laptop runner. It verifies the kit before importing Modori, queries only bounded Windows hardware metadata, creates three prefix-checked synthetic benchmark directories below the kit's own `work` directory, and removes only each exact owned work directory. Final JSON, digest, and Korean summary use exclusive creation below the kit's `results` directory and never overwrite. It does not inspect user documents or use system temp. |
| `scripts/verify_office_research_memory_kit.py` | `resolve` | Read-only extracted-kit verifier. It walks only the kit's immutable tree without following links or entering `results`/`work`, hashes manifested files, and rejects missing, extra, linked, malformed, or modified content before payload import. It performs no mutation. |
| `src/modori/path_policy.py` | `resolve` | Central path validation helper. Rejects relative paths and symlink/junction ancestors before returning configured paths. |
| `src/modori/app.py` | `mkdir`, `write_text` | Hidden `--engine-smoke` and `--public-data-smoke` packaging gates only. The normal QML app path does not invoke these branches; the CLI writes diagnostic JSON payloads to caller-supplied smoke output paths for release verification. |
| `src/modori/public_data_smoke.py` | `mkdir`, `write_text` | Hidden public-data release verification helper used only through `--public-data-smoke`. It reads checked-in or payload fixtures and writes one diagnostic JSON result to the caller-supplied smoke output path. |
| `src/modori/recommendation_baseline.py` | `resolve` | Read-only benchmark adapter. It resolves each case data path and rejects any path outside the selected pilot root before passing the file to the normal table importer. |
| `src/modori/recommendation_benchmark_io.py` | `mkdir`, `replace`, `unlink` | Central local benchmark I/O boundary. JSONL writes use same-directory random temporary files, `fsync`, and atomic replacement; overwrite requires an explicit flag. Workbook generation uses two owned temporary files and replaces only the caller-selected target. XML core properties are parsed with `defusedxml`; workbook loaders reject formulas, schema drift, missing case coverage, and invalid controlled vocabulary. Reviewer workbooks remain untrusted local inputs and may consume resources inside `openpyxl`, so they are not opened automatically by the product runtime. |
| `src/modori/research_memory/ledger_store.py` | `mkdir` | Decision Ledger persistence creates only the validated parent of one application-selected absolute local `.sqlite3` path. UNC and mapped remote drives, relative paths, wrong suffixes, existing targets, and symlink/junction ancestry are rejected before creation and checked again afterward. SQLite owns the database/WAL files; this delivery exposes no clear, delete, replace, or arbitrary-path API. |
| `src/modori/cache.py` | `resolve`, `mkdir`, `write_text`, `unlink` | Cache roots are selected through `resolve_secure_directory_path` where possible. `_ensure_cache_dir` creates only the selected cache directory, rejects link/junction targets, probes writability with a random temp filename, and deletes only that probe. |
| `src/modori/ui/chart_assets.py` | `mkdir`, `unlink` | Result-panel chart preview writes a random PNG filename only under the managed `cache/charts` directory. Failure cleanup deletes only that just-selected partial PNG path and returns a display note instead of touching user files. |
| `src/modori/ui/settings.py` | `resolve`, `mkdir`, `write_text`, `replace`, `unlink` | Settings path is either a secure absolute `.json` file or the managed cache. Writes go to a same-directory random temp file and then atomically replace the target; cleanup deletes only that temp path. |
| `src/modori/ui/result_binding.py` | `resolve`, `unlink` | Obsolete chart cleanup deletes only image files under the managed `cache/charts` directory after resolving both the cache root and candidate path. |
| `src/modori/ui/session.py` | `resolve` | Recent-file storage records a resolved path string only; it does not read, write, or delete the referenced file. |
| `src/modori/ui/worker.py` | `resolve`, `write_text` | Engine exception traces are written only when explicitly enabled by `MODORI_DEBUG_ENGINE_ERRORS=1` or an executable-adjacent `enable-engine-debug` sentinel. The file is written under the managed Modori cache directory and is not part of the normal user-facing error path. |
| `src/modori/steps/reporting.py` | `mkdir`, `resolve`, `unlink`, `rmdir` | `ReportStep` is not allowed in untrusted project JSON. Report paths reject direct output aliases, path separators in filenames, symlink output targets, and chart dirs outside `output_dir`. Failure cleanup deletes only created report/chart files under `output_dir` and removes the output directory only when this run created it. |
| `src/modori/knowledge/loader.py` | `resolve` | Read-only package data root resolution. No mutation. |
| `src/modori/ui/resources.py` | `resolve` | Read-only QML resource root resolution. No mutation. |
| `scripts/package_environment.py` | `mkdir`, `resolve` | Shared release-only environment boundary. It removes workspace R runtime directories from packaged build/run `PATH` values so R ICU/UCRT/OpenSSL DLLs cannot contaminate the PySide6 package, and creates isolated Matplotlib, Modori cache, and settings paths under the workspace `.tmp` directory. It does not inspect or mutate user data. |
| `scripts/package_windows.py` | `mkdir` | Local release-build setup under the workspace `.tmp` directory. Not user-data cleanup. |
| `scripts/package_launch_smoke.py` | `mkdir`, `resolve` | Local smoke-test setup under the workspace `.tmp` directory and explicit executable/cwd normalization. Not product runtime deletion. |
| `scripts/package_engine_smoke.py` | `mkdir`, `resolve`, `unlink` | Local packaged-engine smoke setup under the workspace `.tmp/packaged-engine-smoke` directory. It creates a deterministic reference workbook, deletes only its own previous `result.json` before launch to prevent stale success, and reads the fresh packaged-app JSON. It does not delete user data. |
| `scripts/package_public_data_smoke.py` | `mkdir`, `resolve`, `unlink` | Local packaged public-data import smoke setup under the workspace `.tmp/packaged-public-data-smoke` directory. It deletes only its own previous `result.json`, runs the packaged app against checked-in public-data fixtures, and requires a fresh smoke JSON. It does not delete user data. |
| `scripts/stress_matrix.py` | `mkdir`, `write_text` | Local stress evidence generation under caller-selected output paths; release checklist uses ignored `.stress-matrix`. It creates deterministic synthetic datasets, JSON results, and report artifacts, not user-data cleanup. |
| `scripts/quality_gate.py` | `resolve` | Local release-gate environment setup only. It resolves the workspace-local `.tools/r-env/Scripts/Rscript.exe` path for pytest and slow statistical references, while package and ordinary command environments strip that runtime through `package_environment.py`. It does not create, modify, or delete files. |
| `scripts/recommendation_benchmark.py` | `resolve` | Developer-only benchmark scoring CLI. It resolves the repository root and reads the frozen scorer core, workbook I/O, and CLI sources to bind score output to an implementation digest. Source discovery never runs inside the packaged product scorer core and performs no mutation. |
| `scripts/build_recommendation_pilot.py` | `mkdir`, `write_text`, `write_bytes`, `resolve` | Developer-only deterministic fixture builder. It writes a fixed set of benchmark files below the caller-selected root, refuses existing outputs unless `--force` is explicit, validates data paths against root escape, and validates the completed pack before reporting success. Interruption can leave an incomplete pack, which the validator rejects; this script is not a product runtime or user-data cleanup path. |
| `scripts/check_product_wording.py` | `resolve` | Read-only release scanner. It resolves the selected repository root, reads UTF-8 product text only from fixed source, help, README, and `docs/product` paths, and excludes an explicit historical benchmark allowlist. It does not create, modify, or delete files. |

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
