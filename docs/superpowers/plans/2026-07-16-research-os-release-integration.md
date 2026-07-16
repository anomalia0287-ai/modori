# Research OS Release Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Subagents are forbidden by the owner for this work.

**Goal:** Produce a clean, history-preserving integration branch in which the frozen release product shell and frozen Research OS feature set coexist without a detected regression or provenance downgrade.

**Architecture:** Add a standard-library-only integration verifier to the Research OS lane, freeze both source commits, then create a third worktree from the release pin and merge the Research OS pin with `--no-ff --no-commit`. Resolve the 38 audited shared paths by semantic cohort, preserve every branch-only blob and parent test identifier, run focused and full local gates, create the two-parent merge commit, and record machine-verifiable evidence in a follow-up commit.

**Tech Stack:** Git worktrees and three-way merge; Python 3.12.10; pytest; Ruff; Bandit; PySide6/QML; pandas/scipy/statsmodels/pingouin/factor_analyzer; R 4.x reference runtime; PyInstaller; JSON evidence contracts; PowerShell on Windows.

## Global Constraints

- Design authority: `docs/superpowers/specs/2026-07-16-research-os-release-integration-design.md`.
- Source worktrees are read-only during integration. Never switch, stash, clean, reset, commit, or resolve conflicts in them.
- Do not use subagents. Execute this plan inline with explicit checkpoints.
- Do not push, open a pull request, merge into `release/readiness-1-9`, delete branches, or remove worktrees during P0.
- No GitHub Actions run is required; all acceptance evidence is local.
- No real user data, cloud model, network service, SLM, telemetry, or new dependency.
- Preserve local-only runtime, imported-authority downgrade, evidence quarantine, deterministic resolver authority, and non-automatic experimental recommendations.
- Never relabel legacy heuristic state as AnalysisPassport or question-rationale evidence.
- Never obtain green by removing a test, lowering a threshold, adding an exclusion, or increasing skips.
- Canonical Python: `C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe`.
- Canonical Rscript: `C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe`.
- Set `PYTHONPATH` to the active worktree's `src` directory and prepend all four R runtime directories before running pytest or the quality gate.
- The execution conflict inventory must remain the audited 36 `changed in both` plus 2 `added in both` paths. If it changes, stop and amend this plan before resolving.
- The final P0 branch contains one exact two-parent merge commit plus a later evidence commit. P0 does not add live Research OS UI wiring.

---

## File map

### New verification and evidence files

- `scripts/verify_release_integration.py`: deterministic source-manifest generation, conflict-ledger initialization, ancestry/blob/test-census verification, and JSON report generation.
- `tests/test_verify_release_integration_script.py`: isolated temporary-repository tests for the verifier's acceptance and fail-closed paths.
- `docs/qa/research-os-release-integration-source-manifest.json`: generated immutable source pins and per-path blob identities.
- `docs/qa/research-os-release-integration-conflict-ledger.json`: human-reviewed dispositions for every shared path.
- `docs/qa/research-os-release-integration-verification.json`: generated final verifier output.
- `docs/qa/research-os-release-integration-evidence.md`: commands, environments, test counts, package results, and non-claims.
- `tests/ui/test_release_research_os_integration_boundary.py`: cross-parent UI API preservation and forbidden-provenance regression tests.

### Existing conflict cohorts

- Documentation/metadata: `docs/security/file-operations-audit-2026-06-29.md`, `docs/superpowers/specs/2026-07-11-experimental-recommendation-boundary-design.md`, `pyproject.toml`.
- Packaging/quality: `scripts/package_engine_smoke.py`, `scripts/package_environment.py`, `scripts/package_public_data_smoke.py`, `scripts/package_windows.py`, `scripts/quality_gate.py`.
- Core runtime: `src/modori/app.py`, `src/modori/steps/reporting.py`.
- Python UI: `src/modori/ui/contracts.py`, `src/modori/ui/controller.py`, `src/modori/ui/recommendation_controller.py`, `src/modori/ui/run_validation.py`, `src/modori/ui/strings.py`.
- QML: `src/modori/ui/qml/components/DataGridView.qml`, `src/modori/ui/qml/components/GuideRail.qml`, `src/modori/ui/qml/components/PipelineRail.qml`.
- Conflicting tests: the 6 core and 14 UI test files listed in Task 5 through Task 8.

---

## Integration-task environment bootstrap

At the start of every fresh PowerShell process for Tasks 4 through 10, run this block. It rehydrates all values from the committed source manifest rather than relying on terminal history:

```powershell
$IntegrationWorktree = 'C:\Users\V\Desktop\TongTong\.worktrees\research-os-release-integration'
Set-Location $IntegrationWorktree
$Python = 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe'
$RRoot = 'C:\Users\V\Desktop\TongTong\.tools\r-env'
$ManifestPayload = Get-Content -Raw `
    'docs\qa\research-os-release-integration-source-manifest.json' |
    ConvertFrom-Json
$ReleaseSha = [string]$ManifestPayload.release_sha
$ResearchSha = [string]$ManifestPayload.research_sha
$env:PYTHONPATH = (Resolve-Path 'src').Path
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:MODORI_RSCRIPT = "$RRoot\Scripts\Rscript.exe"
$env:PATH = "$RRoot\Library\bin;$RRoot\Scripts;$RRoot\lib\R\bin;$RRoot\lib\R\bin\x64;$env:PATH"
```

Before Task 10, also set `$MergeSha = (git rev-parse HEAD).Trim()` while `HEAD` is still the two-parent merge commit. The evidence commit is created only after verification.

---

### Task 1: Add a deterministic integration verifier on the Research OS lane

**Files:**

- Create: `scripts/verify_release_integration.py`
- Create: `tests/test_verify_release_integration_script.py`

**Interfaces:**

- Produces: `build_source_manifest(repo: Path, release_ref: str, research_ref: str) -> dict[str, object]`
- Produces: `build_initial_ledger(manifest: Mapping[str, object]) -> dict[str, object]`
- Produces: `verify_integration(repo: Path, manifest: Mapping[str, object], ledger: Mapping[str, object], merge_ref: str) -> dict[str, object]`
- CLI: `inventory --repo PATH --release-ref REF --research-ref REF --output FILE`
- CLI: `init-ledger --manifest FILE --output FILE`
- CLI: `verify --repo PATH --manifest FILE --ledger FILE --merge-ref REF --output FILE`
- Consumes later: frozen source refs, the generated manifest, a completed conflict ledger, and the two-parent merge commit.

- [ ] **Step 1: Write the verifier tests first**

Create `tests/test_verify_release_integration_script.py` with temporary Git repositories. The tests must exercise real Git objects rather than mocking subprocess output:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.verify_release_integration import (
    IntegrationVerificationError,
    build_initial_ledger,
    build_source_manifest,
    verify_integration,
)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "--all")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _fixture_repo(
    tmp_path: Path,
    *,
    omit_research_test: bool = False,
    leave_conflict_marker: bool = False,
    drop_research_only_path: bool = False,
) -> tuple[Path, str, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "base")
    _git(repo, "config", "user.email", "integration@example.invalid")
    _git(repo, "config", "user.name", "Integration Test")
    _write(repo, "shared.txt", "base\n")
    _write(repo, "tests/test_shared.py", "def test_base():\n    assert True\n")
    base = _commit(repo, "base")

    _git(repo, "checkout", "-b", "release")
    _write(repo, "shared.txt", "release\n")
    _write(repo, "release-only.txt", "release\n")
    _write(
        repo,
        "tests/test_shared.py",
        "def test_base():\n    assert True\n\n"
        "def test_release_behavior():\n    assert True\n",
    )
    release = _commit(repo, "release")

    _git(repo, "checkout", "-b", "research", base)
    _write(repo, "shared.txt", "research\n")
    _write(repo, "research-only.txt", "research\n")
    _write(
        repo,
        "tests/test_shared.py",
        "def test_base():\n    assert True\n\n"
        "def test_research_behavior():\n    assert True\n",
    )
    research = _commit(repo, "research")

    _git(repo, "checkout", "-b", "integration", release)
    completed = subprocess.run(
        ["git", "merge", "--no-ff", "--no-commit", research],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 1
    shared_text = (
        "<<<<<<< stale\nrelease\nresearch\n>>>>>>> stale\n"
        if leave_conflict_marker
        else "release\nresearch\n"
    )
    _write(repo, "shared.txt", shared_text)
    merged_tests = (
        "def test_base():\n    assert True\n\n"
        "def test_release_behavior():\n    assert True\n"
    )
    if not omit_research_test:
        merged_tests += "\ndef test_research_behavior():\n    assert True\n"
    _write(repo, "tests/test_shared.py", merged_tests)
    if drop_research_only_path:
        (repo / "research-only.txt").unlink()
    merge = _commit(repo, "merge")
    return repo, release, research, merge


def _completed_ledger(manifest: dict[str, object]) -> dict[str, object]:
    ledger = build_initial_ledger(manifest)
    for entry in ledger["entries"]:
        entry.update(
            {
                "release_behaviors": ["release behavior retained"],
                "research_behaviors": ["research behavior retained"],
                "required_presences": ["semantic union"],
                "required_absences": ["conflict markers"],
                "focused_tests": ["tests/test_shared.py"],
                "resolution": "semantic_union",
                "status": "verified",
            }
        )
    return ledger


def test_manifest_classifies_paths_and_records_blob_oids(tmp_path: Path) -> None:
    repo, release, research, _ = _fixture_repo(tmp_path)

    manifest = build_source_manifest(repo, release, research)

    assert manifest["release_sha"] == release
    assert manifest["research_sha"] == research
    assert [item["path"] for item in manifest["release_only"]] == [
        "release-only.txt"
    ]
    assert [item["path"] for item in manifest["research_only"]] == [
        "research-only.txt"
    ]
    assert [item["path"] for item in manifest["shared"]] == [
        "shared.txt",
        "tests/test_shared.py",
    ]
    assert all(item["release_blob_oid"] for item in manifest["shared"])
    assert all(item["research_blob_oid"] for item in manifest["shared"])


def test_verifier_accepts_exact_two_parent_semantic_merge(tmp_path: Path) -> None:
    repo, release, research, merge = _fixture_repo(tmp_path)
    manifest = build_source_manifest(repo, release, research)
    ledger = _completed_ledger(manifest)

    report = verify_integration(repo, manifest, ledger, merge)

    assert report["ok"] is True
    assert report["parents"] == [release, research]
    assert report["missing_test_ids"] == []
    assert report["shared_path_count"] == 2


def test_verifier_rejects_unresolved_ledger(tmp_path: Path) -> None:
    repo, release, research, merge = _fixture_repo(tmp_path)
    manifest = build_source_manifest(repo, release, research)
    ledger = build_initial_ledger(manifest)

    with pytest.raises(IntegrationVerificationError, match="unresolved ledger"):
        verify_integration(repo, manifest, ledger, merge)


def test_verifier_rejects_dropped_parent_test(tmp_path: Path) -> None:
    repo, release, research, merge = _fixture_repo(
        tmp_path, omit_research_test=True
    )
    manifest = build_source_manifest(repo, release, research)
    ledger = _completed_ledger(manifest)

    with pytest.raises(IntegrationVerificationError, match="missing parent tests"):
        verify_integration(repo, manifest, ledger, merge)


def test_verifier_rejects_wrong_parent_commit(tmp_path: Path) -> None:
    repo, release, research, _ = _fixture_repo(tmp_path)
    manifest = build_source_manifest(repo, release, research)
    ledger = _completed_ledger(manifest)

    with pytest.raises(IntegrationVerificationError, match="merge parents differ"):
        verify_integration(repo, manifest, ledger, release)


def test_verifier_rejects_committed_conflict_marker(tmp_path: Path) -> None:
    repo, release, research, merge = _fixture_repo(
        tmp_path, leave_conflict_marker=True
    )
    manifest = build_source_manifest(repo, release, research)
    ledger = _completed_ledger(manifest)

    with pytest.raises(IntegrationVerificationError, match="conflict markers present"):
        verify_integration(repo, manifest, ledger, merge)


def test_verifier_rejects_branch_only_blob_loss(tmp_path: Path) -> None:
    repo, release, research, merge = _fixture_repo(
        tmp_path, drop_research_only_path=True
    )
    manifest = build_source_manifest(repo, release, research)
    ledger = _completed_ledger(manifest)

    with pytest.raises(IntegrationVerificationError, match="branch-only blob mismatch"):
        verify_integration(repo, manifest, ledger, merge)


def test_cli_writes_canonical_json(tmp_path: Path) -> None:
    repo, release, research, _ = _fixture_repo(tmp_path)
    output = tmp_path / "manifest.json"
    script = Path("scripts/verify_release_integration.py").resolve()

    subprocess.run(
        [
            sys.executable,
            str(script),
            "inventory",
            "--repo",
            str(repo),
            "--release-ref",
            release,
            "--research-ref",
            research,
            "--output",
            str(output),
        ],
        check=True,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_id"] == "modori.release-integration-source-manifest"
    assert output.read_text(encoding="utf-8").endswith("\n")
```

- [ ] **Step 2: Run the tests and confirm the intended red state**

Run from `C:\Users\V\.codex\worktrees\b39f\TongTong`:

```powershell
$Python = 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe'
$env:PYTHONPATH = (Resolve-Path 'src').Path
& $Python -m pytest tests/test_verify_release_integration_script.py -q -p no:cacheprovider
```

Expected: collection fails because `scripts.verify_release_integration` does not exist.

- [ ] **Step 3: Implement the standard-library-only verifier**

Create `scripts/verify_release_integration.py` with these exact contracts and no shell execution:

```python
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


MANIFEST_SCHEMA = "modori.release-integration-source-manifest"
LEDGER_SCHEMA = "modori.release-integration-conflict-ledger"
REPORT_SCHEMA = "modori.release-integration-verification"
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


class IntegrationVerificationError(RuntimeError):
    pass


def _git(repo: Path, *args: str, allowed: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode not in allowed:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise IntegrationVerificationError(
            f"git {' '.join(args)} failed ({completed.returncode}): {detail}"
        )
    return completed


def _commit(repo: Path, ref: str) -> str:
    value = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()
    if not SHA_PATTERN.fullmatch(value):
        raise IntegrationVerificationError(f"invalid commit identity: {ref!r}")
    return value


def _blob(repo: Path, commit: str, path: str) -> str | None:
    completed = _git(repo, "rev-parse", f"{commit}:{path}", allowed=(0, 128))
    if completed.returncode == 128:
        return None
    value = completed.stdout.strip()
    if not SHA_PATTERN.fullmatch(value):
        raise IntegrationVerificationError(f"invalid blob identity: {commit}:{path}")
    return value


def _changed_paths(repo: Path, base: str, commit: str) -> set[str]:
    output = _git(repo, "diff", "--name-only", f"{base}..{commit}", "--").stdout
    return {line for line in output.splitlines() if line}


def _path_record(repo: Path, base: str, release: str, research: str, path: str) -> dict[str, object]:
    return {
        "path": path,
        "base_blob_oid": _blob(repo, base, path),
        "release_blob_oid": _blob(repo, release, path),
        "research_blob_oid": _blob(repo, research, path),
    }


def build_source_manifest(
    repo: Path, release_ref: str, research_ref: str
) -> dict[str, object]:
    repo = repo.resolve()
    release = _commit(repo, release_ref)
    research = _commit(repo, research_ref)
    base = _commit(repo, _git(repo, "merge-base", release, research).stdout.strip())
    release_paths = _changed_paths(repo, base, release)
    research_paths = _changed_paths(repo, base, research)
    release_only = sorted(release_paths - research_paths)
    research_only = sorted(research_paths - release_paths)
    shared = sorted(release_paths & research_paths)
    return {
        "schema_id": MANIFEST_SCHEMA,
        "schema_version": 1,
        "merge_base": base,
        "release_sha": release,
        "research_sha": research,
        "release_only": [
            _path_record(repo, base, release, research, path)
            for path in release_only
        ],
        "research_only": [
            _path_record(repo, base, release, research, path)
            for path in research_only
        ],
        "shared": [
            _path_record(repo, base, release, research, path) for path in shared
        ],
    }


def build_initial_ledger(manifest: Mapping[str, object]) -> dict[str, object]:
    _require_schema(manifest, MANIFEST_SCHEMA)
    entries: list[dict[str, object]] = []
    for raw in _records(manifest, "shared"):
        entries.append(
            {
                "path": raw["path"],
                "conflict_kind": (
                    "added_in_both"
                    if raw["base_blob_oid"] is None
                    else "changed_in_both"
                ),
                "release_behaviors": [],
                "research_behaviors": [],
                "required_presences": [],
                "required_absences": [],
                "focused_tests": [],
                "resolution": "unresolved",
                "supersession_reason": "",
                "status": "unresolved",
            }
        )
    return {
        "schema_id": LEDGER_SCHEMA,
        "schema_version": 1,
        "merge_base": manifest["merge_base"],
        "release_sha": manifest["release_sha"],
        "research_sha": manifest["research_sha"],
        "entries": entries,
    }


def _require_schema(payload: Mapping[str, object], expected: str) -> None:
    if payload.get("schema_id") != expected or payload.get("schema_version") != 1:
        raise IntegrationVerificationError(f"invalid schema: expected {expected} v1")


def _records(payload: Mapping[str, object], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise IntegrationVerificationError(f"invalid record list: {key}")
    return value


def _tree_paths(repo: Path, commit: str) -> tuple[str, ...]:
    output = _git(repo, "ls-tree", "-r", "--name-only", commit).stdout
    return tuple(line for line in output.splitlines() if line)


def _source(repo: Path, commit: str, path: str) -> str:
    return _git(repo, "show", f"{commit}:{path}").stdout


def _test_ids(repo: Path, commit: str) -> set[str]:
    identities: set[str] = set()
    for path in _tree_paths(repo, commit):
        if not path.startswith("tests/") or not path.endswith(".py"):
            continue
        try:
            tree = ast.parse(_source(repo, commit, path), filename=path)
        except SyntaxError as exc:
            raise IntegrationVerificationError(
                f"cannot parse test module {commit}:{path}: {exc}"
            ) from exc
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                identities.add(f"{path}::{node.name}")
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                        identities.add(f"{path}::{node.name}::{child.name}")
    return identities


def _validate_ledger(
    manifest: Mapping[str, object], ledger: Mapping[str, object]
) -> list[dict[str, Any]]:
    _require_schema(ledger, LEDGER_SCHEMA)
    for key in ("merge_base", "release_sha", "research_sha"):
        if ledger.get(key) != manifest.get(key):
            raise IntegrationVerificationError(f"ledger source mismatch: {key}")
    entries = _records(ledger, "entries")
    expected = {record["path"] for record in _records(manifest, "shared")}
    actual = {entry.get("path") for entry in entries}
    if actual != expected or len(entries) != len(expected):
        raise IntegrationVerificationError("ledger paths do not match shared paths")
    allowed = {"semantic_union", "release_supersedes", "research_supersedes"}
    for entry in entries:
        path = str(entry["path"])
        list_fields = (
            "release_behaviors",
            "research_behaviors",
            "required_presences",
            "focused_tests",
        )
        if any(
            not isinstance(entry.get(field), list) or not entry[field]
            for field in list_fields
        ):
            raise IntegrationVerificationError(f"unresolved ledger entry: {path}")
        if not isinstance(entry.get("required_absences"), list):
            raise IntegrationVerificationError(f"invalid required_absences: {path}")
        resolution = entry.get("resolution")
        if resolution not in allowed or entry.get("status") != "verified":
            raise IntegrationVerificationError(f"unresolved ledger entry: {path}")
        if resolution != "semantic_union" and not str(
            entry.get("supersession_reason", "")
        ).strip():
            raise IntegrationVerificationError(f"missing supersession reason: {path}")
    return entries


def verify_integration(
    repo: Path,
    manifest: Mapping[str, object],
    ledger: Mapping[str, object],
    merge_ref: str,
) -> dict[str, object]:
    repo = repo.resolve()
    _require_schema(manifest, MANIFEST_SCHEMA)
    entries = _validate_ledger(manifest, ledger)
    merge = _commit(repo, merge_ref)
    parents = _git(repo, "show", "-s", "--format=%P", merge).stdout.strip().split()
    expected_parents = [manifest["release_sha"], manifest["research_sha"]]
    if parents != expected_parents:
        raise IntegrationVerificationError(
            f"merge parents differ: expected {expected_parents}, got {parents}"
        )

    blob_mismatches: list[str] = []
    for side, key, blob_key in (
        ("release", "release_only", "release_blob_oid"),
        ("research", "research_only", "research_blob_oid"),
    ):
        for record in _records(manifest, key):
            if _blob(repo, merge, record["path"]) != record[blob_key]:
                blob_mismatches.append(f"{side}:{record['path']}")
    if blob_mismatches:
        raise IntegrationVerificationError(
            "branch-only blob mismatch: " + ", ".join(blob_mismatches)
        )

    required_tests = _test_ids(repo, str(manifest["release_sha"])) | _test_ids(
        repo, str(manifest["research_sha"])
    )
    merged_tests = _test_ids(repo, merge)
    missing_tests = sorted(required_tests - merged_tests)
    if missing_tests:
        raise IntegrationVerificationError(
            "missing parent tests: " + ", ".join(missing_tests)
        )

    tree_paths = _tree_paths(repo, merge)
    residue = sorted(
        path for path in tree_paths if path.endswith((".orig", ".rej"))
    )
    if residue:
        raise IntegrationVerificationError(
            "merge residue present: " + ", ".join(residue)
        )
    markers = _git(
        repo,
        "grep",
        "-n",
        "-e",
        "^<<<<<<< ",
        "-e",
        "^>>>>>>> ",
        merge,
        "--",
        allowed=(0, 1),
    )
    if markers.returncode == 0:
        raise IntegrationVerificationError(
            "conflict markers present: " + markers.stdout.strip()
        )

    return {
        "schema_id": REPORT_SCHEMA,
        "schema_version": 1,
        "ok": True,
        "merge_sha": merge,
        "parents": parents,
        "merge_base": manifest["merge_base"],
        "release_only_path_count": len(_records(manifest, "release_only")),
        "research_only_path_count": len(_records(manifest, "research_only")),
        "shared_path_count": len(entries),
        "required_parent_test_id_count": len(required_tests),
        "merged_test_id_count": len(merged_tests),
        "missing_test_ids": missing_tests,
        "branch_only_blob_mismatches": blob_mismatches,
        "merge_residue": residue,
    }


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise IntegrationVerificationError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a Modori release integration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--repo", type=Path, required=True)
    inventory.add_argument("--release-ref", required=True)
    inventory.add_argument("--research-ref", required=True)
    inventory.add_argument("--output", type=Path, required=True)

    ledger = subparsers.add_parser("init-ledger")
    ledger.add_argument("--manifest", type=Path, required=True)
    ledger.add_argument("--output", type=Path, required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--repo", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--ledger", type=Path, required=True)
    verify.add_argument("--merge-ref", required=True)
    verify.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "inventory":
            result = build_source_manifest(
                args.repo, args.release_ref, args.research_ref
            )
        elif args.command == "init-ledger":
            result = build_initial_ledger(_read_json(args.manifest))
        else:
            result = verify_integration(
                args.repo,
                _read_json(args.manifest),
                _read_json(args.ledger),
                args.merge_ref,
            )
        _write_json(args.output, result)
    except (IntegrationVerificationError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run focused tests and static checks**

```powershell
$Python = 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe'
$env:PYTHONPATH = (Resolve-Path 'src').Path
& $Python -m pytest tests/test_verify_release_integration_script.py -q -p no:cacheprovider
& $Python -m ruff check scripts/verify_release_integration.py tests/test_verify_release_integration_script.py
```

Expected: all verifier tests pass and Ruff reports no findings. If the exact code needs line wrapping or typing corrections, change formatting only; do not weaken any rejection case.

- [ ] **Step 5: Commit the verifier**

```powershell
git add -- scripts/verify_release_integration.py tests/test_verify_release_integration_script.py
git diff --cached --check
git commit -m "test: add release integration verifier"
```

Expected: one commit containing only the verifier and its tests.

---
### Task 2: Verify and freeze the Research OS source lane

**Files:**

- Read only: the complete `codex/research-os-contract-design` tree
- Produces no new file; the final SHA is later embedded by Task 3 in the source manifest.

**Interfaces:**

- Consumes: Task 1 verifier commit.
- Produces: a clean, fully verified immutable Research OS source SHA.

- [ ] **Step 1: Confirm exclusive branch identity and cleanliness**

```powershell
$ResearchWorktree = 'C:\Users\V\.codex\worktrees\b39f\TongTong'
Set-Location $ResearchWorktree
git status --short --branch
git branch --show-current
```

Expected: branch is exactly `codex/research-os-contract-design`, there are no working-tree entries, and the branch contains the approved design, this plan, and the Task 1 verifier commit.

- [ ] **Step 2: Configure the canonical local verification environment**

```powershell
$Python = 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe'
$RRoot = 'C:\Users\V\Desktop\TongTong\.tools\r-env'
$env:PYTHONPATH = (Resolve-Path 'src').Path
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:MODORI_RSCRIPT = "$RRoot\Scripts\Rscript.exe"
$env:PATH = "$RRoot\Library\bin;$RRoot\Scripts;$RRoot\lib\R\bin;$RRoot\lib\R\bin\x64;$env:PATH"
& $Python --version
& $env:MODORI_RSCRIPT --version
```

Expected: Python 3.12.10 and the configured local R runtime respond without network access.

- [ ] **Step 3: Run the complete Research OS source baseline**

```powershell
& $Python scripts\quality_gate.py `
    --with-package-check `
    --with-package-build `
    --with-packaged-launch `
    --with-slow-stats
```

Expected: compile, Ruff, Bandit, launch smoke, pytest, `pip check`, package check/build, packaged launch/engine/public-data smoke, and slow-statistics gate all pass. With only the eight Task 1 tests added to the previously verified tree, the expected pytest result is `2143 passed, 5 skipped`; any different count must be explained from the committed diff before continuing. The package build may create ignored `dist/Modori` output, but it may not remove or alter the benchmark ZIP and sidecar already present in `dist`.

- [ ] **Step 4: Capture the immutable Research OS SHA**

```powershell
$ResearchSha = (git rev-parse HEAD).Trim()
$ResearchStatus = @(git status --porcelain=v1 --untracked-files=all)
if ($ResearchStatus.Count -ne 0) { throw 'Research OS source is not clean' }
if ($ResearchSha -notmatch '^[0-9a-f]{40}$') { throw 'Invalid Research OS SHA' }
$ResearchSha
```

Expected: one 40-character SHA and no status entries. Do not move this branch after capture. If a correction is required, make it before Task 3 and rerun this entire task.

---

### Task 3: Freeze the release lane and create the third worktree

**Files:**

- Read only: `C:\Users\V\Desktop\TongTong` (`release/readiness-1-9`)
- Create worktree: `C:\Users\V\Desktop\TongTong\.worktrees\research-os-release-integration`
- Create branch: `codex/research-os-release-integration`
- Generate: `docs/qa/research-os-release-integration-source-manifest.json`

**Interfaces:**

- Consumes: the clean Research OS SHA from Task 2 and a clean release SHA.
- Produces: an isolated release-based integration worktree and a deterministic source manifest.

- [ ] **Step 1: Enforce the release freeze gate without changing that worktree**

```powershell
$ReleaseWorktree = 'C:\Users\V\Desktop\TongTong'
$ReleaseBranch = (git -C $ReleaseWorktree branch --show-current).Trim()
$ReleaseStatus = @(git -C $ReleaseWorktree status --porcelain=v1 --untracked-files=all)
if ($ReleaseBranch -ne 'release/readiness-1-9') {
    throw "Unexpected release branch: $ReleaseBranch"
}
if ($ReleaseStatus.Count -ne 0) {
    $ReleaseStatus
    throw 'Release worktree is still active or dirty; do not integrate'
}
$ReleaseSha = (git -C $ReleaseWorktree rev-parse HEAD).Trim()
```

Expected at the time this plan was written: this step fails because the visual-finish lane has 45 modified or untracked entries. That is a correct protective failure. Do not stash, commit, clean, or discard those entries. Resume only after their owning session leaves the release worktree clean.

- [ ] **Step 2: Reconfirm both immutable inputs and the integration destination**

```powershell
$ResearchWorktree = 'C:\Users\V\.codex\worktrees\b39f\TongTong'
$ResearchSha = (git -C $ResearchWorktree rev-parse HEAD).Trim()
$IntegrationWorktree = 'C:\Users\V\Desktop\TongTong\.worktrees\research-os-release-integration'
$IntegrationBranch = 'codex/research-os-release-integration'

if (@(git -C $ResearchWorktree status --porcelain=v1 --untracked-files=all).Count -ne 0) {
    throw 'Research worktree moved out of the frozen state'
}
if (Test-Path -LiteralPath $IntegrationWorktree) {
    throw 'Integration worktree path already exists; inspect it instead of overwriting it'
}
git -C $ResearchWorktree show-ref --verify --quiet "refs/heads/$IntegrationBranch"
if ($LASTEXITCODE -eq 0) {
    throw 'Integration branch already exists; inspect it instead of reusing it blindly'
}
```

Expected: both source worktrees are clean, and neither the branch nor destination path exists.

- [ ] **Step 3: Create the integration branch and worktree from the release SHA**

```powershell
git -C $ResearchWorktree worktree add -b $IntegrationBranch $IntegrationWorktree $ReleaseSha
git -C $IntegrationWorktree status --short --branch
git -C $IntegrationWorktree rev-parse HEAD
```

Expected: a clean worktree on `codex/research-os-release-integration`, with `HEAD` exactly equal to `$ReleaseSha`. This command requires permission to write the shared Git metadata and the new worktree path; request that permission directly rather than changing locations or branches as a workaround.

- [ ] **Step 4: Run the complete frozen release baseline in the new worktree**

```powershell
Set-Location $IntegrationWorktree
$Python = 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe'
$RRoot = 'C:\Users\V\Desktop\TongTong\.tools\r-env'
$env:PYTHONPATH = (Resolve-Path 'src').Path
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:MODORI_RSCRIPT = "$RRoot\Scripts\Rscript.exe"
$env:PATH = "$RRoot\Library\bin;$RRoot\Scripts;$RRoot\lib\R\bin;$RRoot\lib\R\bin\x64;$env:PATH"
& $Python scripts\quality_gate.py `
    --with-package-check `
    --with-package-build `
    --with-packaged-launch `
    --with-slow-stats
```

Expected: every release baseline command, package smoke, and slow-statistics check passes. Record the exact pass/skip count and package outputs. If it fails, stop before merging; repair belongs to the release owner or a separately approved release fix.

- [ ] **Step 5: Generate and validate the frozen source manifest**

```powershell
$Verifier = 'C:\Users\V\.codex\worktrees\b39f\TongTong\scripts\verify_release_integration.py'
$Manifest = Join-Path $IntegrationWorktree 'docs\qa\research-os-release-integration-source-manifest.json'
& $Python $Verifier inventory `
    --repo $IntegrationWorktree `
    --release-ref $ReleaseSha `
    --research-ref $ResearchSha `
    --output $Manifest
if ($LASTEXITCODE -ne 0) { throw 'Source manifest generation failed' }
$Payload = Get-Content -Raw -LiteralPath $Manifest | ConvertFrom-Json
if ($Payload.merge_base -ne '4e1170c58af35edc20e172f616b51d3464a5a2ef') {
    throw "Unexpected merge base: $($Payload.merge_base)"
}
if ($Payload.shared.Count -ne 38) {
    throw "Conflict design changed: expected 38 shared paths, got $($Payload.shared.Count)"
}
```

Expected: merge base remains the audited SHA and the shared set remains exactly 38 paths. If either differs, stop and revise the design and this plan; do not reinterpret the threshold.

---

### Task 4: Start the history-preserving merge and establish the red ledger gate

**Files:**

- Merge state: all automatically merged Research OS paths plus the 38 shared paths
- Create: `docs/qa/research-os-release-integration-conflict-ledger.json`

**Interfaces:**

- Consumes: Task 3 source manifest and frozen SHAs.
- Produces: an unresolved merge with an exact conflict inventory and a deliberately unresolved ledger that cannot yet verify.

- [ ] **Step 1: Begin the merge using the immutable Research OS SHA**

```powershell
Set-Location 'C:\Users\V\Desktop\TongTong\.worktrees\research-os-release-integration'
git merge --no-ff --no-commit $ResearchSha
if ($LASTEXITCODE -ne 1) {
    throw "Expected a conflict exit code of 1, got $LASTEXITCODE"
}
```

Expected: Git enters a merge state and reports conflicts. A zero exit would mean the audited topology changed; an exit other than 1 is an operational failure. Stop in either case.

- [ ] **Step 2: Compare unresolved paths with the fixed 38-path contract**

```powershell
$ExpectedConflicts = @(
    'docs/security/file-operations-audit-2026-06-29.md',
    'docs/superpowers/specs/2026-07-11-experimental-recommendation-boundary-design.md',
    'pyproject.toml',
    'scripts/package_engine_smoke.py',
    'scripts/package_environment.py',
    'scripts/package_public_data_smoke.py',
    'scripts/package_windows.py',
    'scripts/quality_gate.py',
    'src/modori/app.py',
    'src/modori/steps/reporting.py',
    'src/modori/ui/contracts.py',
    'src/modori/ui/controller.py',
    'src/modori/ui/qml/components/DataGridView.qml',
    'src/modori/ui/qml/components/GuideRail.qml',
    'src/modori/ui/qml/components/PipelineRail.qml',
    'src/modori/ui/recommendation_controller.py',
    'src/modori/ui/run_validation.py',
    'src/modori/ui/strings.py',
    'tests/test_app_engine_smoke.py',
    'tests/test_file_operation_audit.py',
    'tests/test_package_engine_smoke_script.py',
    'tests/test_package_public_data_smoke_script.py',
    'tests/test_package_windows_script.py',
    'tests/test_quality_gate_script.py',
    'tests/ui/test_controller.py',
    'tests/ui/test_data_grid_qml.py',
    'tests/ui/test_end_to_end_ui_flow.py',
    'tests/ui/test_guided_standard_pipeline_rail.py',
    'tests/ui/test_guided_standard_variable_selection_flow.py',
    'tests/ui/test_human_operated_qml_flow.py',
    'tests/ui/test_mode_action_surfaces.py',
    'tests/ui/test_pipeline_ops.py',
    'tests/ui/test_qml_runtime_load.py',
    'tests/ui/test_recommendations.py',
    'tests/ui/test_result_surface_qml.py',
    'tests/ui/test_security_privacy.py',
    'tests/ui/test_smoke_qml.py',
    'tests/ui/test_variable_metadata_editing.py'
) | Sort-Object
$ActualConflicts = @(git diff --name-only --diff-filter=U) | Sort-Object
$Difference = @(Compare-Object $ExpectedConflicts $ActualConflicts)
if ($Difference.Count -ne 0) {
    $Difference
    git merge --abort
    throw 'Unresolved path set differs from the approved design'
}
```

Expected: no comparison output and exactly 38 unresolved paths.

- [ ] **Step 3: Generate the fail-closed initial ledger**

```powershell
$Manifest = 'docs\qa\research-os-release-integration-source-manifest.json'
$Ledger = 'docs\qa\research-os-release-integration-conflict-ledger.json'
& $Python scripts\verify_release_integration.py init-ledger `
    --manifest $Manifest `
    --output $Ledger
$LedgerPayload = Get-Content -Raw -LiteralPath $Ledger | ConvertFrom-Json
if ($LedgerPayload.entries.Count -ne 38) { throw 'Ledger count mismatch' }
if (@($LedgerPayload.entries | Where-Object status -ne 'unresolved').Count -ne 0) {
    throw 'Initial ledger must be entirely unresolved'
}
```

Expected: 38 entries, each carrying exact source pins and an unresolved status. This is the intentional red state; it may not be changed to `verified` until its path is resolved and its focused tests pass.

- [ ] **Step 4: Confirm the verifier itself remains green inside the merge worktree**

```powershell
$env:PYTHONPATH = (Resolve-Path 'src').Path
& $Python -m pytest tests/test_verify_release_integration_script.py -q -p no:cacheprovider
```

Expected: the verifier's isolated temporary-repository tests pass even though unrelated merge paths remain unresolved.

---

### Task 5: Reconcile documentation, dependencies, packaging, and quality gates

**Files:**

- Modify: `docs/security/file-operations-audit-2026-06-29.md`
- Modify: `docs/superpowers/specs/2026-07-11-experimental-recommendation-boundary-design.md`
- Modify: `pyproject.toml`
- Modify: `scripts/package_engine_smoke.py`
- Modify: `scripts/package_environment.py`
- Modify: `scripts/package_public_data_smoke.py`
- Modify: `scripts/package_windows.py`
- Modify: `scripts/quality_gate.py`
- Modify: `tests/test_file_operation_audit.py`
- Modify: `tests/test_package_engine_smoke_script.py`
- Modify: `tests/test_package_public_data_smoke_script.py`
- Modify: `tests/test_package_windows_script.py`
- Modify: `tests/test_quality_gate_script.py`
- Modify ledger entries for these 13 paths.

**Interfaces:**

- Consumes: release installer/runtime isolation and Research OS statistical/package additions.
- Produces: one offline-by-default, fail-closed packaging and quality contract containing the union of both parents.

- [ ] **Step 1: Inspect each parent and the three-way conflict without editing**

For every file in this task, run all three reads before resolving it:

```powershell
$CohortPaths = @(
    'docs/security/file-operations-audit-2026-06-29.md',
    'docs/superpowers/specs/2026-07-11-experimental-recommendation-boundary-design.md',
    'pyproject.toml',
    'scripts/package_engine_smoke.py',
    'scripts/package_environment.py',
    'scripts/package_public_data_smoke.py',
    'scripts/package_windows.py',
    'scripts/quality_gate.py',
    'tests/test_file_operation_audit.py',
    'tests/test_package_engine_smoke_script.py',
    'tests/test_package_public_data_smoke_script.py',
    'tests/test_package_windows_script.py',
    'tests/test_quality_gate_script.py'
)
foreach ($Path in $CohortPaths) {
    git diff $ReleaseSha $ResearchSha -- $Path
    git show "$ReleaseSha`:$Path"
    git show "$ResearchSha`:$Path"
}
```

Expected: the release side contributes current package isolation, installer/resource handling, and UI-era audit entries; the Research OS side contributes factorial/logistic smoke, Research OS packaging, stricter wording checks, and current quality gates. Treat a missing behaviour on one side as ignorance, not an instruction to delete the other side.

- [ ] **Step 2: Resolve the five packaging/quality test files before their implementations**

Use `apply_patch` to retain every distinct parent test function and combine assertions when the same test function changed on both sides. The required union is:

| Test file | Required retained assertions |
|---|---|
| `tests/test_file_operation_audit.py` | all release file-operation entries and all Research OS ledger/quarantine/import entries |
| `tests/test_package_engine_smoke_script.py` | release engine/open/rerun checks plus logistic-regression and factorial-ANOVA evidence checks |
| `tests/test_package_public_data_smoke_script.py` | release public-data isolation and Research OS expanded analysis evidence |
| `tests/test_package_windows_script.py` | release QML/resources/installer contents plus every Research OS module and script required at runtime |
| `tests/test_quality_gate_script.py` | offline default command order, package opt-ins, R scoping, Bandit, full pytest, and no implicit network scan |

Run the test-census helper against the working tree only after all five files parse:

```powershell
& $Python -m compileall -q `
    tests/test_file_operation_audit.py `
    tests/test_package_engine_smoke_script.py `
    tests/test_package_public_data_smoke_script.py `
    tests/test_package_windows_script.py `
    tests/test_quality_gate_script.py
```

Expected: compilation succeeds; the tests themselves should still fail until the implementations are reconciled.

- [ ] **Step 3: Resolve documentation and `pyproject.toml` semantically**

Use `apply_patch` with these non-negotiable outcomes:

- the security audit contains both the release file-operation evidence and Research OS decision-ledger/quarantine boundaries without duplicate claim inflation;
- the experimental recommendation boundary retains the stronger local-only, no-auto-execution, no-human-gold, calculation-versus-validity, and legacy-provenance clauses from either parent;
- dependencies are the exact set union of both source pins, preserving compatible version bounds rather than choosing a wider bound without evidence;
- `project.scripts`, setuptools package-data, pytest markers, and Ruff exclusions are preserved as a semantic union; and
- no dependency or tool exclusion absent from both parents is introduced.

Then run:

```powershell
& $Python -m pip check
& $Python -m pytest tests/test_file_operation_audit.py -q -p no:cacheprovider
```

Expected: dependency consistency and the file-operation audit pass.

- [ ] **Step 4: Resolve package and quality implementations to satisfy the union tests**

Use `apply_patch`; preserve these exact behaviours:

- `package_engine_smoke.py` validates the release open/rerun/status contract and rejects missing logistic or factorial evidence;
- `package_environment.py` removes workspace/reference-runtime contamination while retaining every release package-environment defence;
- `package_public_data_smoke.py` uses only committed public/synthetic fixtures and fails on missing expected analysis evidence;
- `package_windows.py` includes all QML/resources/statistical packages/Research OS modules required by the two parents, with no network fetch; and
- `quality_gate.py` remains offline by default and includes compile, Ruff, Bandit, launch smoke, full pytest, and `pip check`, with package, slow-statistics, and advisory scans only behind explicit flags.

Run:

```powershell
& $Python -m pytest `
    tests/test_package_engine_smoke_script.py `
    tests/test_package_public_data_smoke_script.py `
    tests/test_package_windows_script.py `
    tests/test_quality_gate_script.py `
    -q -p no:cacheprovider
& $Python -m ruff check `
    scripts/package_engine_smoke.py `
    scripts/package_environment.py `
    scripts/package_public_data_smoke.py `
    scripts/package_windows.py `
    scripts/quality_gate.py `
    tests/test_file_operation_audit.py `
    tests/test_package_engine_smoke_script.py `
    tests/test_package_public_data_smoke_script.py `
    tests/test_package_windows_script.py `
    tests/test_quality_gate_script.py
```

Expected: all focused tests and Ruff pass.

- [ ] **Step 5: Complete the 13 ledger entries and stage this cohort**

For each exact path listed under **Files**, replace the generated empty arrays with concrete parent behaviours observed in Step 1, list the passing focused test file, set `resolution` to `semantic_union` unless the design document is demonstrably superseded, set `status` to `verified`, and record these required absences where relevant: network-by-default, dropped package content, skipped security scan, missing factorial/logistic smoke, and conflict markers.

```powershell
git add -- `
    docs/security/file-operations-audit-2026-06-29.md `
    docs/superpowers/specs/2026-07-11-experimental-recommendation-boundary-design.md `
    pyproject.toml `
    scripts/package_engine_smoke.py `
    scripts/package_environment.py `
    scripts/package_public_data_smoke.py `
    scripts/package_windows.py `
    scripts/quality_gate.py `
    tests/test_file_operation_audit.py `
    tests/test_package_engine_smoke_script.py `
    tests/test_package_public_data_smoke_script.py `
    tests/test_package_windows_script.py `
    tests/test_quality_gate_script.py `
    docs/qa/research-os-release-integration-conflict-ledger.json
```

Expected: none of these paths remains in `git diff --name-only --diff-filter=U`. Do not commit while the overall merge is open.

---

### Task 6: Reconcile application bootstrap and statistical reporting

**Files:**

- Modify: `src/modori/app.py`
- Modify: `src/modori/steps/reporting.py`
- Modify: `tests/test_app_engine_smoke.py`
- Modify ledger entries for these 3 paths.

**Interfaces:**

- Consumes: release bootstrap/open/rerun behaviour and Research OS factorial/logistic reporting and smoke evidence.
- Produces: one application entry point and report dispatcher that fail closed for unknown result types and expose the union of verified analyses.

- [ ] **Step 1: Resolve the app-smoke test into a failing behavioural union**

Retain every distinct parent test in `tests/test_app_engine_smoke.py`. Where both parents modify the same payload assertion, require all of the following together:

- dataset opens, run completes, wait succeeds, and status is `ready`;
- existing release statistics smoke remains `ok`;
- logistic-regression evidence names `LogisticRegressionResult`; and
- factorial-ANOVA evidence names `FactorialAnovaResult` with the pinned interaction evidence.

Run:

```powershell
& $Python -m pytest tests/test_app_engine_smoke.py -q -p no:cacheprovider
```

Expected: at least one union assertion fails against either unresolved implementation; a collection error caused by conflict markers is not an acceptable red state.

- [ ] **Step 2: Resolve `src/modori/app.py`**

Use `apply_patch` after comparing both source blobs. Preserve release bootstrap properties, clipboard/local settings, CLI entry behaviour, engine open/rerun/wait/status payload, and every Research OS factorial/logistic smoke field. Do not import or initialize a live Research OS UI coordinator in P0.

Run:

```powershell
& $Python -m pytest tests/test_app_engine_smoke.py -q -p no:cacheprovider
```

Expected: the app-engine smoke union passes.

- [ ] **Step 3: Resolve `src/modori/steps/reporting.py` and its branch-only suites**

Preserve the release reliability/comparison/regression prose, chart rendering, safe report paths, and export behaviour. Add the Research OS factorial interaction, odds-ratio forest, ROC, calibration, report-chart sequence, and selection-disclosure logic. Dispatch remains explicit and unknown result types do not silently become generic prose.

Run:

```powershell
& $Python -m pytest `
    tests/test_report_step.py `
    tests/test_factorial_anova_reporting.py `
    tests/test_factorial_anova_results.py `
    tests/test_logistic_regression_reporting.py `
    tests/test_logistic_regression_metrics.py `
    -q -p no:cacheprovider
& $Python -m ruff check src/modori/app.py src/modori/steps/reporting.py tests/test_app_engine_smoke.py
```

Expected: all report and smoke tests pass with no Ruff findings.

- [ ] **Step 4: Complete the three ledger entries and stage this cohort**

Record both parent behaviours, required output types, required absence of generic fallback or live UI wiring, focused tests, `semantic_union`, and `verified` for all three paths.

```powershell
git add -- `
    src/modori/app.py `
    src/modori/steps/reporting.py `
    tests/test_app_engine_smoke.py `
    docs/qa/research-os-release-integration-conflict-ledger.json
```

Expected: all three paths leave the unresolved set.

---

### Task 7: Reconcile Python UI contracts while preserving provenance boundaries

**Files:**

- Modify: `src/modori/ui/contracts.py`
- Modify: `src/modori/ui/controller.py`
- Modify: `src/modori/ui/recommendation_controller.py`
- Modify: `src/modori/ui/run_validation.py`
- Modify: `src/modori/ui/strings.py`
- Modify: `tests/ui/test_controller.py`
- Modify: `tests/ui/test_end_to_end_ui_flow.py`
- Modify: `tests/ui/test_guided_standard_variable_selection_flow.py`
- Modify: `tests/ui/test_human_operated_qml_flow.py`
- Modify: `tests/ui/test_pipeline_ops.py`
- Modify: `tests/ui/test_recommendations.py`
- Modify: `tests/ui/test_security_privacy.py`
- Modify: `tests/ui/test_variable_metadata_editing.py`
- Create: `tests/ui/test_release_research_os_integration_boundary.py`
- Modify ledger entries for the 13 shared paths above.

**Interfaces:**

- Consumes: release controller/QML-facing API and Research OS selection-origin, preparation, factorial/logistic validation, and experimental-confirmation API.
- Produces: a backwards-compatible controller surface with explicit authority separation and no passport-rationale wiring.

- [ ] **Step 1: Add cross-parent API and provenance tests before resolving implementations**

Create `tests/ui/test_release_research_os_integration_boundary.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

from modori.ui.controller import UiController
from modori.ui.recommendation_controller import RecommendationControllerMixin


def test_ui_controller_preserves_release_and_research_properties() -> None:
    release_api = {
        "canRerun",
        "selectionConfirmationRequired",
        "stepChainDisplayText",
    }
    research_api = {
        "analysisSelectionOrigin",
        "markCurrentSelectionExperimental",
    }

    missing = sorted(
        name for name in release_api | research_api if not hasattr(UiController, name)
    )

    assert missing == []


def test_recommendation_mixin_preserves_both_parent_contracts() -> None:
    release_api = {
        "recommendationLevel",
        "recommendationAlternativesText",
        "preparedReliabilityItems",
        "preparedDescriptiveVariables",
        "preparedVariableKeys",
        "preparedOutcomeKey",
        "preparedGroupKey",
        "preparedPredictorKeys",
        "preparedCovariateKeys",
    }
    research_api = {
        "recommendationRequiresConfiguration",
        "recommendationPreparationPending",
        "experimentalRecommendationConfirmed",
        "preparedRecommendationIntent",
        "preparedRecommendationReviewRequirement",
        "prepareSelectedRecommendationNow",
        "setExperimentalRecommendationConfirmed",
        "clearExperimentalRecommendationPreparation",
        "clearExperimentalRecommendationSelection",
        "preparedRecommendationField",
        "recommendationCandidateReviewRequirementAt",
    }

    missing = sorted(
        name
        for name in release_api | research_api
        if not hasattr(RecommendationControllerMixin, name)
    )

    assert missing == []


def test_legacy_recommendation_mixin_does_not_import_passport_rationale() -> None:
    source = Path("src/modori/ui/recommendation_controller.py").read_text(
        encoding="utf-8"
    )

    assert "question_rationale_presenter" not in source
    assert "QuestionRationalePresenter" not in source
    assert "QuestionRationaleResult" not in source


def test_qml_does_not_alias_legacy_reason_as_passport_rationale() -> None:
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "src/modori/ui/qml/components/GuideRail.qml",
            "src/modori/ui/qml/components/PipelineRail.qml",
        )
    )
    forbidden_alias = re.compile(
        r"(?:question|passport)\w*rationale\w*\s*:\s*"
        r"(?:controller\.)?recommendationReason",
        re.IGNORECASE,
    )

    assert forbidden_alias.search(sources) is None
```

Run only the first three tests before QML resolution:

```powershell
& $Python -m pytest `
    tests/ui/test_release_research_os_integration_boundary.py::test_ui_controller_preserves_release_and_research_properties `
    tests/ui/test_release_research_os_integration_boundary.py::test_recommendation_mixin_preserves_both_parent_contracts `
    tests/ui/test_release_research_os_integration_boundary.py::test_legacy_recommendation_mixin_does_not_import_passport_rationale `
    -q -p no:cacheprovider
```

Expected: API tests fail against a one-sided resolution; the provenance test passes only if the legacy mixin remains isolated.

- [ ] **Step 2: Resolve the eight existing Python-oriented UI test files**

Use `apply_patch` to retain the distinct parent test functions and assertion union in:

```text
tests/ui/test_controller.py
tests/ui/test_end_to_end_ui_flow.py
tests/ui/test_guided_standard_variable_selection_flow.py
tests/ui/test_human_operated_qml_flow.py
tests/ui/test_pipeline_ops.py
tests/ui/test_recommendations.py
tests/ui/test_security_privacy.py
tests/ui/test_variable_metadata_editing.py
```

Required union: release rerun/confirmation/display behaviour, Research OS selection origin and explicit experimental confirmation, factorial/logistic pipeline validation, manual override, stale-state clearing, privacy wording, and unchanged variable editing. Preserve all test identifiers.

- [ ] **Step 3: Resolve the five Python UI implementation files**

Use `apply_patch` with these exact outcomes:

- `contracts.py`: retain both `SelectionProvenance` compatibility and `SelectionOrigin` semantics through one canonical type plus an explicit compatibility alias if both names are imported by surviving code;
- `controller.py`: retain release `canRerun`, `selectionConfirmationRequired`, and `stepChainDisplayText` plus Research OS `analysisSelectionOrigin` and `markCurrentSelectionExperimental`;
- `recommendation_controller.py`: retain the full release candidate/display/prepared-variable surface and the Research OS preparation/confirmation/review-requirement state machine, while keeping it a legacy experimental recommendation controller rather than a passport source;
- `run_validation.py`: retain all release validators and the Research OS logistic-regression and factorial-ANOVA validators, including dataset-aware checks; and
- `strings.py`: preserve the closed bilingual union without silently relabelling heuristic recommendations as Research OS decisions.

Run:

```powershell
& $Python -m pytest `
    tests/ui/test_release_research_os_integration_boundary.py::test_ui_controller_preserves_release_and_research_properties `
    tests/ui/test_release_research_os_integration_boundary.py::test_recommendation_mixin_preserves_both_parent_contracts `
    tests/ui/test_release_research_os_integration_boundary.py::test_legacy_recommendation_mixin_does_not_import_passport_rationale `
    tests/ui/test_controller.py `
    tests/ui/test_end_to_end_ui_flow.py `
    tests/ui/test_guided_standard_variable_selection_flow.py `
    tests/ui/test_human_operated_qml_flow.py `
    tests/ui/test_pipeline_ops.py `
    tests/ui/test_recommendations.py `
    tests/ui/test_security_privacy.py `
    tests/ui/test_variable_metadata_editing.py `
    -q -p no:cacheprovider
& $Python -m ruff check `
    src/modori/ui/contracts.py `
    src/modori/ui/controller.py `
    src/modori/ui/recommendation_controller.py `
    src/modori/ui/run_validation.py `
    src/modori/ui/strings.py `
    tests/ui/test_release_research_os_integration_boundary.py
```

Expected: the complete Python UI cohort passes and Ruff is clean.

- [ ] **Step 4: Complete the 13 shared-path ledger entries and stage the cohort**

Record concrete API/state behaviours from both parents, the forbidden legacy-to-passport path, the focused test files, `semantic_union`, and `verified`. The new integration-boundary test is not a shared path and therefore is staged but has no ledger row.

```powershell
git add -- `
    src/modori/ui/contracts.py `
    src/modori/ui/controller.py `
    src/modori/ui/recommendation_controller.py `
    src/modori/ui/run_validation.py `
    src/modori/ui/strings.py `
    tests/ui/test_controller.py `
    tests/ui/test_end_to_end_ui_flow.py `
    tests/ui/test_guided_standard_variable_selection_flow.py `
    tests/ui/test_human_operated_qml_flow.py `
    tests/ui/test_pipeline_ops.py `
    tests/ui/test_recommendations.py `
    tests/ui/test_security_privacy.py `
    tests/ui/test_variable_metadata_editing.py `
    tests/ui/test_release_research_os_integration_boundary.py `
    docs/qa/research-os-release-integration-conflict-ledger.json
```

Expected: these 13 shared paths are no longer unresolved.

---

### Task 8: Reconcile the three shared QML surfaces and their six visual-contract tests

**Files:**

- Modify: `src/modori/ui/qml/components/DataGridView.qml`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/components/PipelineRail.qml`
- Modify: `tests/ui/test_data_grid_qml.py`
- Modify: `tests/ui/test_guided_standard_pipeline_rail.py`
- Modify: `tests/ui/test_mode_action_surfaces.py`
- Modify: `tests/ui/test_qml_runtime_load.py`
- Modify: `tests/ui/test_result_surface_qml.py`
- Modify: `tests/ui/test_smoke_qml.py`
- Modify: `tests/ui/test_release_research_os_integration_boundary.py`
- Modify ledger entries for the 9 shared paths above.

**Interfaces:**

- Consumes: the frozen release visual/accessibility structure and Research OS experimental-state/provenance requirements.
- Produces: QML that preserves release appearance and interactions without exposing a false Research OS source.

- [ ] **Step 1: Resolve the six QML-oriented test files into a parent assertion union**

Use `apply_patch`. Preserve all release visual-system, geometry, focus, scrollbar, compact-control, and runtime-load assertions. Preserve all Research OS experimental-candidate, confirmation, no-auto-run, and mode-boundary assertions. Keep every parent test identifier.

Run compilation only:

```powershell
& $Python -m compileall -q `
    tests/ui/test_data_grid_qml.py `
    tests/ui/test_guided_standard_pipeline_rail.py `
    tests/ui/test_mode_action_surfaces.py `
    tests/ui/test_qml_runtime_load.py `
    tests/ui/test_result_surface_qml.py `
    tests/ui/test_smoke_qml.py
```

Expected: all six test modules parse before QML is changed.

- [ ] **Step 2: Resolve each QML file with the release visual tree as the comparison baseline**

Do not copy a complete parent file. Compare both blobs and apply bounded patches:

- `DataGridView.qml`: retain the frozen release grid geometry, scrolling, focus, accessibility, editing, and visual tokens; add only missing Research OS-compatible state hooks that have a surviving test;
- `GuideRail.qml`: retain the frozen release composition and visual controls; retain experimental labelling, candidate selection, configuration, confirmation, and no-auto-run behaviour; do not instantiate `QuestionRationalePresenter` or bind legacy `recommendationReason` to any passport/rationale property; and
- `PipelineRail.qml`: retain release sizing/scroll/focus and Research OS selection-origin/experimental disclosure without adding live passport state.

Use the fourth integration-boundary test as the permanent negative gate.

- [ ] **Step 3: Run the QML and interaction cohort**

```powershell
& $Python -m pytest `
    tests/ui/test_release_research_os_integration_boundary.py::test_qml_does_not_alias_legacy_reason_as_passport_rationale `
    tests/ui/test_data_grid_qml.py `
    tests/ui/test_guided_standard_pipeline_rail.py `
    tests/ui/test_mode_action_surfaces.py `
    tests/ui/test_qml_runtime_load.py `
    tests/ui/test_result_surface_qml.py `
    tests/ui/test_smoke_qml.py `
    -q -p no:cacheprovider
```

Expected: QML loads and all union/negative assertions pass. A visually plausible render does not override a failing contract test.

- [ ] **Step 4: Complete the nine ledger entries and stage the cohort**

For QML rows, record release visual/accessibility behaviours, Research OS experimental-state behaviours, required absence of false passport provenance and automatic execution, and the exact focused tests. For test rows, record the retained parent assertion families. Set all nine rows to `semantic_union` and `verified`.

```powershell
git add -- `
    src/modori/ui/qml/components/DataGridView.qml `
    src/modori/ui/qml/components/GuideRail.qml `
    src/modori/ui/qml/components/PipelineRail.qml `
    tests/ui/test_data_grid_qml.py `
    tests/ui/test_guided_standard_pipeline_rail.py `
    tests/ui/test_mode_action_surfaces.py `
    tests/ui/test_qml_runtime_load.py `
    tests/ui/test_result_surface_qml.py `
    tests/ui/test_smoke_qml.py `
    tests/ui/test_release_research_os_integration_boundary.py `
    docs/qa/research-os-release-integration-conflict-ledger.json
```

Expected: `git diff --name-only --diff-filter=U` is now empty. If any path remains, do not proceed to the full gate.

---

### Task 9: Close the conflict ledger, run all local gates, and create the merge commit

**Files:**

- Finalize: `docs/qa/research-os-release-integration-source-manifest.json`
- Finalize: `docs/qa/research-os-release-integration-conflict-ledger.json`
- Stage: all automatically merged branch-only paths and every resolved conflict from Tasks 5 through 8.

**Interfaces:**

- Consumes: all resolved cohorts and their focused evidence.
- Produces: the exact two-parent merge commit that the verifier can audit.

- [ ] **Step 1: Enforce structural completion before any full test**

```powershell
$Unmerged = @(git diff --name-only --diff-filter=U)
$IndexResidue = @(git ls-files -u)
if ($Unmerged.Count -ne 0 -or $IndexResidue.Count -ne 0) {
    $Unmerged
    $IndexResidue
    throw 'Merge still contains unresolved index entries'
}
git diff --check
if ($LASTEXITCODE -ne 0) { throw 'Whitespace or conflict-marker check failed' }
$MarkerOutput = @(git grep -n -e '^<<<<<<< ' -e '^>>>>>>> ' --)
if ($LASTEXITCODE -eq 0) {
    $MarkerOutput
    throw 'Tracked working tree still contains merge markers'
}
if ($LASTEXITCODE -ne 1) { throw 'Merge-marker scan failed operationally' }

$LedgerPayload = Get-Content -Raw `
    'docs\qa\research-os-release-integration-conflict-ledger.json' |
    ConvertFrom-Json
$BadLedger = @(
    $LedgerPayload.entries | Where-Object {
        $_.status -ne 'verified' -or
        $_.resolution -notin @(
            'semantic_union',
            'release_supersedes',
            'research_supersedes'
        ) -or
        $_.release_behaviors.Count -eq 0 -or
        $_.research_behaviors.Count -eq 0 -or
        $_.required_presences.Count -eq 0 -or
        $_.focused_tests.Count -eq 0
    }
)
if ($LedgerPayload.entries.Count -ne 38 -or $BadLedger.Count -ne 0) {
    $BadLedger | ConvertTo-Json -Depth 8
    throw 'Conflict ledger is incomplete'
}
```

Expected: no unmerged entries, no diff-check output, exactly 38 verified ledger entries, and no blank required evidence fields.

- [ ] **Step 2: Run the combined integration-focused suite**

```powershell
& $Python -m pytest `
    tests/test_verify_release_integration_script.py `
    tests/test_app_engine_smoke.py `
    tests/test_file_operation_audit.py `
    tests/test_package_engine_smoke_script.py `
    tests/test_package_public_data_smoke_script.py `
    tests/test_package_windows_script.py `
    tests/test_quality_gate_script.py `
    tests/test_report_step.py `
    tests/test_factorial_anova_reporting.py `
    tests/test_logistic_regression_reporting.py `
    tests/test_research_memory_architecture.py `
    tests/test_research_memory_ledger_store.py `
    tests/test_research_memory_quarantine.py `
    tests/test_research_memory_promotion.py `
    tests/test_research_os_counterfactual_planner.py `
    tests/test_research_os_passport.py `
    tests/test_research_os_resolver.py `
    tests/test_question_rationale_projection.py `
    tests/ui/test_release_research_os_integration_boundary.py `
    tests/ui/test_controller.py `
    tests/ui/test_recommendations.py `
    tests/ui/test_qml_runtime_load.py `
    tests/ui/test_data_grid_qml.py `
    tests/ui/test_mode_action_surfaces.py `
    -q -p no:cacheprovider
```

Expected: every named suite passes with zero skip introduced by P0. Fix failures with TDD in the owning cohort and update its ledger evidence; never edit the assertion merely to match the broken merge.

- [ ] **Step 3: Run the complete local quality, package, and slow-statistics gate**

```powershell
& $Python scripts\quality_gate.py `
    --with-package-check `
    --with-package-build `
    --with-packaged-launch `
    --with-slow-stats
```

Expected, in order: compile passes; Ruff passes; Bandit passes; launch smoke reports success; the full pytest suite passes with no unexplained new skip; `pip check` passes; Windows package check and build pass; packaged launch, engine, and public-data smoke pass; slow statistical adequacy checks pass. Do not enable `--with-pip-audit` because P0 is offline and that flag may contact an external advisory service.

- [ ] **Step 4: Inspect the staged merge without adding generated artifacts**

```powershell
git status --short
git diff --cached --stat
git diff --cached --check
```

Expected: all automatically merged and explicitly resolved source paths are staged; the source manifest, completed ledger, and new integration-boundary test are staged; no unexpected non-ignored build output or user/environment artifact appears. Stage only an intended missing file by exact path. Do not use `git add --all`.

- [ ] **Step 5: Create the exact two-parent merge commit**

```powershell
git add -- `
    docs/qa/research-os-release-integration-source-manifest.json `
    docs/qa/research-os-release-integration-conflict-ledger.json `
    tests/ui/test_release_research_os_integration_boundary.py
git diff --cached --check
git commit -m "merge: integrate Research OS into release lane"
$MergeSha = (git rev-parse HEAD).Trim()
$Parents = (git show -s --format=%P $MergeSha).Trim().Split(' ')
if ($Parents.Count -ne 2) { throw 'Integration commit is not a two-parent merge' }
if ($Parents[0] -ne $ReleaseSha -or $Parents[1] -ne $ResearchSha) {
    throw "Unexpected merge parents: $($Parents -join ' ')"
}
```

Expected: the commit succeeds and its ordered parents are exactly the frozen release SHA and frozen Research OS SHA. If parent order or identity differs, stop; do not amend history until the cause is understood.

---

### Task 10: Verify the merge commit and record durable evidence

**Files:**

- Generate: `docs/qa/research-os-release-integration-verification.json`
- Create: `docs/qa/research-os-release-integration-evidence.md`

**Interfaces:**

- Consumes: the exact merge commit, source manifest, completed ledger, and command outputs from Task 9.
- Produces: machine-readable and human-readable P0 evidence in one follow-up commit.

- [ ] **Step 1: Run the independent merge verifier against the committed tree**

```powershell
$Verification = 'docs\qa\research-os-release-integration-verification.json'
& $Python scripts\verify_release_integration.py verify `
    --repo . `
    --manifest docs\qa\research-os-release-integration-source-manifest.json `
    --ledger docs\qa\research-os-release-integration-conflict-ledger.json `
    --merge-ref $MergeSha `
    --output $Verification
if ($LASTEXITCODE -ne 0) { throw 'Integration verifier rejected the merge' }
$Report = Get-Content -Raw $Verification | ConvertFrom-Json
if ($Report.ok -ne $true -or $Report.shared_path_count -ne 38) {
    throw 'Integration verification report is not an accepted 38-path result'
}
```

Expected: `ok: true`, exact parent SHAs, zero branch-only blob mismatch, zero missing parent test ID, zero merge residue, and `shared_path_count: 38`.

- [ ] **Step 2: Write the human evidence record from fresh outputs**

Use `apply_patch` to create `docs/qa/research-os-release-integration-evidence.md`. The title is `Research OS Release Integration Evidence`; the date is `2026-07-16`; the status is `P0 local integration evidence`. Populate every value from the exact command source below rather than copying a prior report:

| Evidence field | Exact source |
|---|---|
| release SHA | `$ReleaseSha`, cross-checked with `git show -s --format=%H $ReleaseSha` |
| Research OS SHA | `$ResearchSha`, cross-checked with `git show -s --format=%H $ResearchSha` |
| merge base | literal `4e1170c58af35edc20e172f616b51d3464a5a2ef`, cross-checked with `git merge-base $ReleaseSha $ResearchSha` |
| merge commit and ordered parents | `$MergeSha` and `git show -s --format=%P $MergeSha` |
| Python | `& $Python --version` |
| SQLite | `& $Python -c "import sqlite3; print(sqlite3.sqlite_version)"` |
| PySide6 and Qt | `& $Python -c "import PySide6; from PySide6.QtCore import qVersion; print(PySide6.__version__, qVersion())"` |
| R | `& $env:MODORI_RSCRIPT --version` |
| worktree | symbolic `%USERPROFILE%\Desktop\TongTong\.worktrees\research-os-release-integration`; do not commit the Windows account name, hostname, or an absolute user path |
| release source baseline | exact pytest pass/skip line and exit code from Task 3 Step 4 |
| Research OS source baseline | exact pytest pass/skip line and exit code from Task 2 Step 3 |
| focused integration suite | exact pass/skip line and exit code from Task 9 Step 2 |
| full suite, Ruff, Bandit, dependency check | exact lines and exit codes from Task 9 Step 3 |
| QML runtime | exact focused and full-suite QML result from Tasks 8 and 9 |
| Windows package | exact check/build exit codes from Task 9 Step 3 |
| packaged launch, engine, public-data smoke | exact success lines and exit codes from Task 9 Step 3 |
| slow statistics | exact result and exit code from Task 9 Step 3 |
| machine verifier | literal `ok` plus `docs/qa/research-os-release-integration-verification.json` after Step 1 validates it |

The document also records: 38 shared paths, 36 changed-in-both paths, 2 added-in-both paths, zero unresolved paths, and the conflict-ledger path. Its preserved-boundary section states that no legacy recommendation reason became passport rationale, no live Research OS UI was added, no network/cloud model/SLM/telemetry/real user data was used, imported authority remained downgraded, experimental candidates remained non-automatic, neither source worktree was modified, and no username/hostname/absolute user path was committed. Its non-claim paragraph states that P0 does not establish recommendation validity, numerical accuracy, human equivalence, SPSS superiority, complete accessibility conformance, office-PC performance, or public release readiness.

- [ ] **Step 3: Rerun the verifier tests and final default quality gate at the evidence tree**

```powershell
& $Python -m pytest tests/test_verify_release_integration_script.py -q -p no:cacheprovider
& $Python scripts\quality_gate.py
```

Expected: verifier tests and the complete default gate pass at the exact evidence-tree content. Record the fresh full-suite count in the evidence document if it differs from the pre-merge count because of the new verifier and integration-boundary tests.

- [ ] **Step 4: Commit evidence and prove final cleanliness and ancestry**

```powershell
git add -- `
    docs/qa/research-os-release-integration-verification.json `
    docs/qa/research-os-release-integration-evidence.md
git diff --cached --check
git commit -m "docs: record Research OS release integration evidence"

git merge-base --is-ancestor $ReleaseSha HEAD
if ($LASTEXITCODE -ne 0) { throw 'Release source is not an ancestor' }
git merge-base --is-ancestor $ResearchSha HEAD
if ($LASTEXITCODE -ne 0) { throw 'Research source is not an ancestor' }
if ((git -C 'C:\Users\V\Desktop\TongTong' rev-parse HEAD).Trim() -ne $ReleaseSha) {
    throw 'Release source branch moved during P0'
}
if ((git -C 'C:\Users\V\.codex\worktrees\b39f\TongTong' rev-parse HEAD).Trim() -ne $ResearchSha) {
    throw 'Research source branch moved during P0'
}
if (@(git -C 'C:\Users\V\Desktop\TongTong' status --porcelain=v1 --untracked-files=all).Count -ne 0) {
    throw 'Release source worktree changed during P0'
}
if (@(git -C 'C:\Users\V\.codex\worktrees\b39f\TongTong' status --porcelain=v1 --untracked-files=all).Count -ne 0) {
    throw 'Research source worktree changed during P0'
}
if (@(git status --porcelain=v1 --untracked-files=all).Count -ne 0) {
    git status --short
    throw 'Final integration worktree is not clean'
}
git log -2 --oneline --decorate
```

Expected: evidence commit succeeds, both frozen source commits are ancestors, and the integration worktree is clean. Do not push or merge the branch during P0 handoff.

---

## Execution checkpoint and stop policy

Execute Tasks 1 and 2 immediately after this plan is committed. Task 3 is a hard external-state gate: if the release worktree remains dirty, report the exact status and pause without changing it. Resume from Task 3 only after it is clean.

During Tasks 4 through 10, an ordinary failing focused test triggers root-cause diagnosis and a bounded fix in the integration worktree. Repeated failure, a changed conflict inventory, a source-baseline failure, a required authority downgrade, or pressure to weaken a gate triggers `git merge --abort` in the dedicated integration worktree and a plan revision. The two source lanes remain intact in every stop path.

## Final P0 handoff

Report only evidence-backed results:

- exact source and merge SHAs;
- conflict count and ledger status;
- full and focused test counts;
- package and local runtime results;
- verifier report status;
- the absence or presence of any unresolved risk; and
- the explicit P1 boundary: live multi-round Research OS UI wiring remains next.

Do not describe P0 as proving recommendation validity, numerical accuracy, office-PC performance, or SPSS superiority.
