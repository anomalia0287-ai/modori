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


def _git(
    repo: Path,
    *args: str,
    allowed: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str]:
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
    value = _git(
        repo,
        "rev-parse",
        "--verify",
        f"{ref}^{{commit}}",
    ).stdout.strip()
    if not SHA_PATTERN.fullmatch(value):
        raise IntegrationVerificationError(f"invalid commit identity: {ref!r}")
    return value


def _blob(repo: Path, commit: str, path: str) -> str | None:
    completed = _git(
        repo,
        "rev-parse",
        f"{commit}:{path}",
        allowed=(0, 128),
    )
    if completed.returncode == 128:
        return None
    value = completed.stdout.strip()
    if not SHA_PATTERN.fullmatch(value):
        raise IntegrationVerificationError(
            f"invalid blob identity: {commit}:{path}"
        )
    return value


def _changed_paths(repo: Path, base: str, commit: str) -> set[str]:
    output = _git(
        repo,
        "diff",
        "--name-only",
        f"{base}..{commit}",
        "--",
    ).stdout
    return {line for line in output.splitlines() if line}


def _path_record(
    repo: Path,
    base: str,
    release: str,
    research: str,
    path: str,
) -> dict[str, object]:
    return {
        "path": path,
        "base_blob_oid": _blob(repo, base, path),
        "release_blob_oid": _blob(repo, release, path),
        "research_blob_oid": _blob(repo, research, path),
    }


def build_source_manifest(
    repo: Path,
    release_ref: str,
    research_ref: str,
) -> dict[str, object]:
    repo = repo.resolve()
    release = _commit(repo, release_ref)
    research = _commit(repo, research_ref)
    merge_base = _git(repo, "merge-base", release, research).stdout.strip()
    base = _commit(repo, merge_base)
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
            _path_record(repo, base, release, research, path)
            for path in shared
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
        raise IntegrationVerificationError(
            f"invalid schema: expected {expected} v1"
        )


def _records(
    payload: Mapping[str, object],
    key: str,
) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, dict) for item in value
    ):
        raise IntegrationVerificationError(f"invalid record list: {key}")
    return value


def _tree_paths(repo: Path, commit: str) -> tuple[str, ...]:
    output = _git(
        repo,
        "ls-tree",
        "-r",
        "--name-only",
        commit,
    ).stdout
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
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
            ):
                identities.add(f"{path}::{node.name}")
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if (
                        isinstance(
                            child,
                            (ast.FunctionDef, ast.AsyncFunctionDef),
                        )
                        and child.name.startswith("test_")
                    ):
                        identities.add(f"{path}::{node.name}::{child.name}")
    return identities


def _validate_ledger(
    manifest: Mapping[str, object],
    ledger: Mapping[str, object],
) -> list[dict[str, Any]]:
    _require_schema(ledger, LEDGER_SCHEMA)
    for key in ("merge_base", "release_sha", "research_sha"):
        if ledger.get(key) != manifest.get(key):
            raise IntegrationVerificationError(f"ledger source mismatch: {key}")
    entries = _records(ledger, "entries")
    expected = {record["path"] for record in _records(manifest, "shared")}
    actual = {entry.get("path") for entry in entries}
    if actual != expected or len(entries) != len(expected):
        raise IntegrationVerificationError(
            "ledger paths do not match shared paths"
        )
    allowed = {
        "semantic_union",
        "release_supersedes",
        "research_supersedes",
    }
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
            raise IntegrationVerificationError(
                f"unresolved ledger entry: {path}"
            )
        if not isinstance(entry.get("required_absences"), list):
            raise IntegrationVerificationError(
                f"invalid required_absences: {path}"
            )
        resolution = entry.get("resolution")
        if resolution not in allowed or entry.get("status") != "verified":
            raise IntegrationVerificationError(
                f"unresolved ledger entry: {path}"
            )
        if resolution != "semantic_union" and not str(
            entry.get("supersession_reason", "")
        ).strip():
            raise IntegrationVerificationError(
                f"missing supersession reason: {path}"
            )
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
    parents = (
        _git(repo, "show", "-s", "--format=%P", merge)
        .stdout.strip()
        .split()
    )
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

    required_tests = _test_ids(
        repo,
        str(manifest["release_sha"]),
    ) | _test_ids(repo, str(manifest["research_sha"]))
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
        "release_only_path_count": len(
            _records(manifest, "release_only")
        ),
        "research_only_path_count": len(
            _records(manifest, "research_only")
        ),
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
        raise IntegrationVerificationError(
            f"JSON root must be an object: {path}"
        )
    return payload


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Modori release integration"
    )
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
                args.repo,
                args.release_ref,
                args.research_ref,
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
    except (
        IntegrationVerificationError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
