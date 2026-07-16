from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from scripts.verify_release_integration import (
    IntegrationVerificationError,
    build_initial_ledger,
    build_source_manifest,
    verify_integration,
)


def _remove_readonly(
    function: Callable[[str], object],
    path: str,
    exc: BaseException,
) -> None:
    if not isinstance(exc, PermissionError):
        raise exc
    os.chmod(path, stat.S_IWRITE)
    function(path)


@pytest.fixture
def git_tmp_path(tmp_path: Path) -> Iterator[Path]:
    yield tmp_path
    repo = tmp_path / "repo"
    if repo.exists():
        shutil.rmtree(repo, onexc=_remove_readonly)


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
    _git(repo, "config", "core.autocrlf", "false")
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


def test_manifest_classifies_paths_and_records_blob_oids(
    git_tmp_path: Path,
) -> None:
    repo, release, research, _ = _fixture_repo(git_tmp_path)

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


def test_verifier_accepts_exact_two_parent_semantic_merge(
    git_tmp_path: Path,
) -> None:
    repo, release, research, merge = _fixture_repo(git_tmp_path)
    manifest = build_source_manifest(repo, release, research)
    ledger = _completed_ledger(manifest)

    report = verify_integration(repo, manifest, ledger, merge)

    assert report["ok"] is True
    assert report["parents"] == [release, research]
    assert report["missing_test_ids"] == []
    assert report["shared_path_count"] == 2


def test_verifier_rejects_unresolved_ledger(git_tmp_path: Path) -> None:
    repo, release, research, merge = _fixture_repo(git_tmp_path)
    manifest = build_source_manifest(repo, release, research)
    ledger = build_initial_ledger(manifest)

    with pytest.raises(IntegrationVerificationError, match="unresolved ledger"):
        verify_integration(repo, manifest, ledger, merge)


def test_verifier_rejects_dropped_parent_test(git_tmp_path: Path) -> None:
    repo, release, research, merge = _fixture_repo(
        git_tmp_path, omit_research_test=True
    )
    manifest = build_source_manifest(repo, release, research)
    ledger = _completed_ledger(manifest)

    with pytest.raises(IntegrationVerificationError, match="missing parent tests"):
        verify_integration(repo, manifest, ledger, merge)


def test_verifier_rejects_wrong_parent_commit(git_tmp_path: Path) -> None:
    repo, release, research, _ = _fixture_repo(git_tmp_path)
    manifest = build_source_manifest(repo, release, research)
    ledger = _completed_ledger(manifest)

    with pytest.raises(IntegrationVerificationError, match="merge parents differ"):
        verify_integration(repo, manifest, ledger, release)


def test_verifier_rejects_committed_conflict_marker(
    git_tmp_path: Path,
) -> None:
    repo, release, research, merge = _fixture_repo(
        git_tmp_path, leave_conflict_marker=True
    )
    manifest = build_source_manifest(repo, release, research)
    ledger = _completed_ledger(manifest)

    with pytest.raises(IntegrationVerificationError, match="conflict markers present"):
        verify_integration(repo, manifest, ledger, merge)


def test_verifier_rejects_branch_only_blob_loss(
    git_tmp_path: Path,
) -> None:
    repo, release, research, merge = _fixture_repo(
        git_tmp_path, drop_research_only_path=True
    )
    manifest = build_source_manifest(repo, release, research)
    ledger = _completed_ledger(manifest)

    with pytest.raises(IntegrationVerificationError, match="branch-only blob mismatch"):
        verify_integration(repo, manifest, ledger, merge)


def test_cli_writes_canonical_json(git_tmp_path: Path) -> None:
    repo, release, research, _ = _fixture_repo(git_tmp_path)
    output = git_tmp_path / "manifest.json"
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
