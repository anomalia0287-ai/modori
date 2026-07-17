# Portable Office-Hardware Benchmark Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a hash-anchored, offline, one-click Windows x64 kit that measures the Decision Ledger workload three times on the user's existing office laptop without reading user files or installing software.

**Architecture:** A pure contract module defines canonical manifests, bounded hardware evidence, privacy constraints, and fail-closed gate evaluation. A verifier checks the extracted inventory before Modori imports; a target runner performs a bounded Windows hardware probe and launches each synthetic benchmark in a fresh process; a deterministic builder assembles only committed allowlisted sources with the pinned official Python 3.12.10 embeddable runtime and a two-stage PowerShell/bootstrap hash chain.

**Tech Stack:** Python 3.12 standard library, SQLite 3.49.1 bundled by CPython, Windows PowerShell 5.1 built-ins, SHA-256, deterministic ZIP, pytest, Ruff.

## Global Constraints

- Use only the assigned `codex/research-os-contract-design` worktree and branch.
- Do not use subagents; the user explicitly rejected delegated implementation.
- Do not modify product UI, calculation modules, benchmark corpora, package/VM payloads, or model artifacts.
- Target Windows x64; no administrator rights, installation, network access, registry/service/power-plan mutation, or system temporary directory.
- Read and write only below the resolved kit root except for bounded read-only Windows hardware metadata APIs.
- Never enumerate or open user documents, profiles, network interfaces, installed programs, serial numbers, or credentials.
- Use synthetic Decision Ledger data only. Returned results are research evidence, never human gold or automatic product evidence.
- `office_hardware_claim_allowed` is always `false`; only a later human evidence review may broaden the claim.
- Run the full benchmark in three fresh child processes. Open/replay and bundle gates use the maximum inner repetition; append uses each outer run's p95; memory uses the largest peak.
- Pin `https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip` at SHA-256 `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`.
- The pinned runtime must report Python `3.12.10`, SQLite `3.49.1`, `Connection.setconfig`, and `SQLITE_DBCONFIG_DEFENSIVE` before packaging.
- Every filesystem write/delete is added to `tests/test_file_operation_audit.py` and `docs/security/file-operations-audit-2026-06-29.md`.
- Use TDD red-green cycles and commit each independently reviewable task.

---

### Task 1: Closed kit contracts and conservative gate evaluation

**Files:**
- Create: `scripts/office_research_memory_kit.py`
- Create: `tests/test_office_research_memory_kit_contract.py`
- Modify: `docs/superpowers/specs/2026-07-12-portable-office-benchmark-kit-design.md`

**Interfaces:**
- Produces: `RuntimeSpec`, `ManifestEntry`, `KitContractError`, `canonical_json_bytes(value)`, `parse_manifest(raw)`, `manifest_bytes(entries)`, `evaluate_measurements(hardware, runs)`.
- Consumes: mappings containing integer-only benchmark payloads from `scripts/benchmark_research_memory.py`.

- [ ] **Step 1: Write failing manifest and runtime tests**

```python
def test_manifest_is_canonical_sorted_and_rejects_traversal() -> None:
    entries = (
        ManifestEntry("runtime/python.exe", 3, "a" * 64),
        ManifestEntry("payload/src/modori/__init__.py", 2, "b" * 64),
    )
    raw = manifest_bytes(tuple(reversed(entries)))
    assert parse_manifest(raw) == entries
    with pytest.raises(KitContractError, match="relative"):
        ManifestEntry("../outside", 1, "c" * 64)


def test_runtime_pin_matches_official_sigstore_digest() -> None:
    assert RUNTIME_SPEC.version == "3.12.10"
    assert RUNTIME_SPEC.sqlite_version == "3.49.1"
    assert RUNTIME_SPEC.sha256 == (
        "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
    )
```

- [ ] **Step 2: Run the contract tests and confirm RED**

Run:

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest tests/test_office_research_memory_kit_contract.py -q -p no:cacheprovider
```

Expected: import failure for `scripts.office_research_memory_kit`.

- [ ] **Step 3: Implement canonical manifest primitives and the exact runtime inventory**

```python
@dataclass(frozen=True)
class ManifestEntry:
    path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        candidate = PurePosixPath(self.path)
        if (
            candidate.is_absolute()
            or not self.path
            or "\\" in self.path
            or any(part in {"", ".", ".."} for part in candidate.parts)
        ):
            raise KitContractError("manifest path must be a closed relative POSIX path")
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise KitContractError("manifest size must be a non-negative integer")
        if not _DIGEST_RE.fullmatch(self.sha256):
            raise KitContractError("manifest digest must be lowercase SHA-256")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
```

Define `RUNTIME_SPEC.expected_files` as the exact 35-entry inventory observed in the official archive, including `python.exe`, `python312.dll`, `_sqlite3.pyd`, `sqlite3.dll`, `python312.zip`, `python312._pth`, `LICENSE.txt`, and the remaining pinned DLL/PYD files. Reject duplicate, missing, extra, directory, encrypted, absolute, traversal, and symlink ZIP entries.

- [ ] **Step 4: Write failing conservative evaluation tests**

```python
def test_three_hdd_runs_pass_only_when_every_worst_case_passes() -> None:
    hardware = _hardware(media_type="hdd", bus_type="sata", cores=2, memory_gib=8)
    runs = tuple(_run(open_max_us=2_900_000, append_p95_us=140_000) for _ in range(3))
    result = evaluate_measurements(hardware, runs)
    assert result["measurement_complete"] is True
    assert result["provisional_gate_pass"] is True
    assert result["office_hardware_claim_allowed"] is False


def test_above_target_cpu_or_unknown_storage_never_provisionally_passes() -> None:
    result = evaluate_measurements(
        _hardware(media_type="unknown", bus_type="unknown", cores=4, memory_gib=8),
        tuple(_run() for _ in range(3)),
    )
    assert result["provisional_gate_pass"] is False
    assert result["reason_codes"] == [
        "cpu_profile_above_target",
        "storage_profile_unqualified",
    ]
```

- [ ] **Step 5: Implement exact fail-closed evaluation**

```python
def evaluate_measurements(
    hardware: Mapping[str, object],
    runs: tuple[Mapping[str, object], ...],
) -> dict[str, object]:
    reasons: set[str] = set()
    if len(runs) != 3:
        reasons.add("measurement_incomplete")
    media = hardware.get("storage", {}).get("media_type")
    bus = hardware.get("storage", {}).get("bus_type")
    if media not in {"ssd", "hdd"} or bus in {"unknown", "usb", "virtual"}:
        reasons.add("storage_profile_unqualified")
    if hardware.get("physical_core_count", 10**9) > 2:
        reasons.add("cpu_profile_above_target")
    if hardware.get("physical_memory_bytes", 10**18) > 9 * 1024**3:
        reasons.add("memory_profile_above_target")
    open_limit = 1_000_000 if media == "ssd" else 3_000_000
    for run in runs:
        if run["open_replay"]["max_us"] > open_limit:
            reasons.add("open_replay_exceeded")
        if run["durable_append"]["p95_us"] > (50_000 if media == "ssd" else 150_000):
            reasons.add("durable_append_exceeded")
        if run["bundle_validation"]["max_us"] > 2_000_000:
            reasons.add("bundle_validation_exceeded")
        if run["open_replay"]["process_peak_working_set_bytes"] > 192 * 1024**2:
            reasons.add("peak_memory_exceeded")
    return {
        "measurement_complete": len(runs) == 3,
        "provisional_gate_pass": not reasons,
        "office_hardware_claim_allowed": False,
        "reason_codes": sorted(reasons),
    }
```

Use strict mapping/type validators rather than permissive `.get()` chains in the actual implementation; the snippet fixes the decision logic, not a relaxed parser.

- [ ] **Step 6: Run tests, Ruff, and commit**

Run the focused test and:

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m ruff check scripts/office_research_memory_kit.py tests/test_office_research_memory_kit_contract.py
git diff --check
```

Commit: `feat: define portable benchmark kit contracts`

### Task 2: Manifest verifier and immutable inventory boundary

**Files:**
- Create: `scripts/verify_office_research_memory_kit.py`
- Create: `tests/test_office_research_memory_kit_verifier.py`

**Interfaces:**
- Consumes: `MANIFEST.json`, `KIT-IDENTITY.json`, the extracted kit root, and Task 1 contract functions.
- Produces: `VerifiedKit(root: Path, identity: Mapping[str, object], entries: tuple[ManifestEntry, ...])` and `verify_kit(root: Path) -> VerifiedKit`.

- [ ] **Step 1: Write failing exact-inventory and mutation tests**

```python
def test_verify_kit_accepts_only_manifested_immutable_files(tmp_path: Path) -> None:
    root = _fake_kit(tmp_path)
    verified = verify_kit(root)
    assert verified.root == root.resolve()
    (root / "payload" / "extra.py").write_text("pass", encoding="utf-8")
    with pytest.raises(KitVerificationError, match="unexpected"):
        verify_kit(root)


@pytest.mark.parametrize("target", ["runtime/python.exe", "KIT-IDENTITY.json"])
def test_verify_kit_rejects_one_byte_mutation(tmp_path: Path, target: str) -> None:
    root = _fake_kit(tmp_path)
    path = root / PurePosixPath(target)
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(KitVerificationError, match="digest|size"):
        verify_kit(root)
```

- [ ] **Step 2: Run the verifier tests and confirm RED**

Expected: import failure for `scripts.verify_office_research_memory_kit`.

- [ ] **Step 3: Implement streaming hash checks and a no-follow inventory walk**

```python
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _walk_immutable(root: Path) -> tuple[str, ...]:
    found: list[str] = []
    stack = [root]
    while stack:
        parent = stack.pop()
        with os.scandir(parent) as entries:
            for entry in entries:
                relative = Path(entry.path).relative_to(root).as_posix()
                if relative.split("/", 1)[0] in {"results", "work"}:
                    continue
                if entry.is_symlink() or _is_junction(Path(entry.path)):
                    raise KitVerificationError("kit inventory contains a link")
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    found.append(relative)
                else:
                    raise KitVerificationError("kit inventory contains a special file")
    return tuple(sorted(found))
```

Exclude only `RUN-MODORI-BENCHMARK.cmd`, `VERIFY-AND-RUN.ps1`, and `MANIFEST.json` from the Python inventory comparison. Require `results/` and `work/` to be real, non-link directories. Validate `KIT-IDENTITY.json` against the runtime pin and source commit format.

- [ ] **Step 4: Add traversal, junction, malformed JSON, duplicate entry, extra file, and mutable-directory tests**

Each test changes exactly one boundary and expects a typed `KitVerificationError`. A symlink/junction test may skip only when Windows denies test link creation.

- [ ] **Step 5: Run focused tests, Ruff, and commit**

Commit: `feat: verify portable benchmark inventory`

### Task 3: Bounded Windows hardware probe and three-process runner

**Files:**
- Create: `scripts/run_office_research_memory_benchmark.py`
- Create: `tests/test_office_research_memory_kit_runner.py`

**Interfaces:**
- Consumes: `verify_kit`, the embedded `python.exe`, and `run_benchmark(root=...)` from the existing benchmark script.
- Produces: `probe_windows_hardware(kit_root)`, `run_office_measurement(kit_root)`, canonical result JSON, SHA-256 sidecar, and Korean summary.

- [ ] **Step 1: Write failing hardware-schema and privacy tests**

```python
def test_hardware_probe_parser_keeps_only_approved_fields() -> None:
    raw = json.dumps(
        {
            "logical_cpu_count": 4,
            "physical_core_count": 2,
            "physical_memory_bytes": 8 * 1024**3,
            "manufacturer": "Example",
            "model": "OfficeBook",
            "storage": {
                "bus_type": "SATA",
                "media_type": "HDD",
                "friendly_name": "Example Disk",
                "filesystem": "NTFS",
                "free_bytes": 50 * 1024**3,
            },
        }
    )
    profile = parse_hardware_probe(raw)
    assert "computer_name" not in canonical_json_bytes(profile).decode("utf-8")
    assert profile["storage"]["media_type"] == "hdd"


def test_privacy_denylist_rejects_identifying_fields() -> None:
    with pytest.raises(OfficeBenchmarkError, match="privacy"):
        parse_hardware_probe('{"user_name":"person"}')
```

- [ ] **Step 2: Implement the static PowerShell probe and AC/fixed-drive checks**

The PowerShell command accepts one regex-validated drive letter and queries only
`Win32_ComputerSystem`, `Win32_Processor`, `Get-Partition`, `Get-Disk`,
`Get-PhysicalDisk`, and `Get-Volume`. It emits UTF-8 compressed JSON. It never
interpolates a path, command fragment, or user string. Python uses
`GetSystemPowerStatus`, `GetDriveTypeW`, and `shutil.disk_usage` to require AC power,
a fixed local volume, and 2 GiB free.

- [ ] **Step 3: Write failing fresh-child and output-confinement tests**

```python
def test_parent_requires_three_fresh_valid_child_payloads(tmp_path: Path) -> None:
    runner = _runner_with_three_payloads(tmp_path)
    result = runner.run()
    assert len(result["runs"]) == 3
    assert runner.child_pids == tuple(sorted(set(runner.child_pids)))


def test_result_writer_never_overwrites_or_escapes_results(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    first = write_result_files(results, "measurement-a", _result())
    with pytest.raises(OfficeBenchmarkError, match="exists"):
        write_result_files(results, "measurement-a", _result())
    assert all(path.parent == results.resolve() for path in first)
```

- [ ] **Step 4: Implement parent and child modes**

Parent mode verifies the kit before adding `payload/src` to `sys.path`, probes hardware,
and starts exactly three commands shaped as:

```python
[
    str(verified.root / "runtime" / "python.exe"),
    "-I",
    str(Path(__file__).resolve()),
    "--child-run",
    measurement_id,
    str(run_index),
]
```

Child mode re-verifies the kit, derives an owned work path named
`modori-office-benchmark-<measurement-id>-run-<index>`, imports the existing benchmark,
runs it, prints one canonical JSON object, and removes only that verified work path in a
`finally` block. Parent mode uses a 1,800-second timeout per child and never includes
absolute paths or raw tracebacks in returned evidence.

- [ ] **Step 5: Implement canonical results, exclusive writes, and Korean summary**

Result names use only UTC and a random measurement ID. Write with exclusive creation,
flush, and `os.fsync`; then write a lowercase SHA-256 sidecar. The summary reports the
observed hardware, worst metrics, reason codes, and the fixed sentence that product
claim authority remains false.

- [ ] **Step 6: Run focused tests, current-host hardware probe, Ruff, and commit**

Commit: `feat: run offline office hardware benchmark`

### Task 4: Deterministic builder and two-stage bootstrap chain

**Files:**
- Create: `scripts/build_office_research_memory_kit.py`
- Create: `scripts/office_benchmark_kit/RUN-MODORI-BENCHMARK.cmd.in`
- Create: `scripts/office_benchmark_kit/VERIFY-AND-RUN.ps1.in`
- Create: `scripts/office_benchmark_kit/README-KO.txt`
- Create: `tests/test_office_research_memory_kit_builder.py`
- Modify: `docs/superpowers/specs/2026-07-12-portable-office-benchmark-kit-design.md`

**Interfaces:**
- Consumes: a clean Git commit, the exact source allowlist, and the pinned official runtime ZIP.
- Produces: `dist/modori-office-benchmark-kit-<commit>-py31210.zip` and `.zip.sha256`.

- [ ] **Step 1: Update the design inventory with the bootstrap PowerShell file**

Document the trust chain exactly: outer ZIP digest anchors `RUN.cmd`; `RUN.cmd` embeds
the SHA-256 of `VERIFY-AND-RUN.ps1`; the PowerShell bootstrap embeds the SHA-256 of
`MANIFEST.json`; the manifest covers every remaining immutable file.

- [ ] **Step 2: Write failing safe-runtime and deterministic-build tests**

```python
def test_builder_rejects_wrong_runtime_digest(tmp_path: Path) -> None:
    archive = tmp_path / "runtime.zip"
    archive.write_bytes(b"not the pinned runtime")
    with pytest.raises(KitBuildError, match="runtime digest"):
        build_kit(_request(runtime_archive=archive))


def test_identical_inputs_produce_identical_zip_bytes(tmp_path: Path) -> None:
    first = build_kit(_fake_request(tmp_path / "one"))
    second = build_kit(_fake_request(tmp_path / "two"))
    assert first.archive.read_bytes() == second.archive.read_bytes()
    assert first.archive_sha256 == second.archive_sha256
```

- [ ] **Step 3: Implement safe runtime extraction and committed-source reads**

Inspect the runtime ZIP before writing any member. Require the exact pinned inventory,
no encryption, no links, no duplicate normalized paths, and no directory members.
Read every payload/template byte from `git show <commit>:<allowlisted-path>` after
requiring a clean worktree; never copy `.git`, `.venv`, untracked files, data fixtures,
or the current environment.

- [ ] **Step 4: Implement canonical identity, manifest, and bootstrap rendering**

Use the source commit timestamp as `source_date_epoch` and ZIP timestamp anchor. Write
identity first, manifest all immutable non-bootstrap files, render the manifest digest
into PowerShell, then render the PowerShell digest into CMD. `README-KO.txt` is covered
by the manifest. Bootstrap failures show a Korean error, preserve a bounded diagnostic
under `results/`, and pause for a photo.

- [ ] **Step 5: Implement deterministic ZIP creation**

Sort every path, construct `ZipInfo` manually, use one normalized timestamp and stable
external attributes, UTF-8 names, DEFLATE level 9, and explicit empty `results/` and
`work/` directory entries. Build in a UUID-named directory below `dist/`, verify its
resolved parent and prefix before cleanup, and create output files without overwrite.

- [ ] **Step 6: Run builder tests, inspect two archive listings/digests, Ruff, and commit**

Commit: `feat: build sealed office benchmark kit`

### Task 5: Security, file-operation audit, and operator runbook

**Files:**
- Create: `docs/qa/portable-office-benchmark-kit-runbook.md`
- Create: `tests/test_office_research_memory_kit_architecture.py`
- Modify: `tests/test_file_operation_audit.py`
- Modify: `docs/security/file-operations-audit-2026-06-29.md`

**Interfaces:**
- Consumes: all kit scripts and templates.
- Produces: enforceable offline/privacy/path constraints and the exact user procedure.

- [ ] **Step 1: Write failing architecture and privacy-source tests**

Parse the AST of all kit Python files. Reject imports of `socket`, `urllib`, `http`,
`requests`, `ftplib`, `smtplib`, `webbrowser`, `winreg`, browser/UI modules, product
calculation modules, and package installers. Assert the PowerShell template contains no
`Invoke-WebRequest`, `Start-Process -Verb RunAs`, registry, service, power-plan, serial,
network, user-profile, or recursive filesystem command.

- [ ] **Step 2: Add every write/delete site to the file-operation audit**

Describe the builder's bounded `dist/` staging cleanup, verifier's read-only inventory,
and runner's exclusive `results/` writes and prefix-checked `work/` cleanup. The audit
test's exact file set must match.

- [ ] **Step 3: Write the Korean runbook**

Include: connect AC; copy ZIP from USB to the internal disk; compare the chat-reported
ZIP SHA-256; extract; double-click launcher; leave the window open; photograph any
error; return only JSON, `.sha256`, summary, and bounded error file; never run from USB;
do not delete or format existing files.

- [ ] **Step 4: Run architecture, audit, mutation, and full Research Memory tests**

Expected: all kit architecture tests pass, 300/300 existing import mutations retain
their expected classification, and all 10 crash stages remain valid.

- [ ] **Step 5: Commit**

Commit: `docs: add portable benchmark safety runbook`

### Task 6: Reproducible build, current-host smoke, and USB handoff artifact

**Files:**
- Generate, do not commit: `dist/modori-office-benchmark-kit-<commit>-py31210.zip`
- Generate, do not commit: matching `.zip.sha256`
- Use cached official input: `.tmp/python-runtime/python-3.12.10-embed-amd64.zip`

**Interfaces:**
- Consumes: the clean final source commit and pinned runtime.
- Produces: the exact USB deliverables and current-host result evidence.

- [ ] **Step 1: Run the complete focused and repository gates**

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m ruff check src tests scripts
git diff --check
git status --short
```

- [ ] **Step 2: Build twice from the same commit into separate output directories**

Run the builder twice with the pinned runtime and compare the archive bytes and SHA-256.
Any difference blocks delivery.

- [ ] **Step 3: Verify the outer digest and extract to a path containing spaces and Korean text**

Use a new directory below `.tmp/`; verify resolved ownership before any cleanup. Confirm
the archive contains no `.git`, environment, fixture, dataset, secret-like filename, or
unexpected source.

- [ ] **Step 4: Execute the actual bootstrap on the current Windows host**

Run `RUN-MODORI-BENCHMARK.cmd`. Expect three complete child runs, a verified JSON and
sidecar, and `office_hardware_claim_allowed=false`. Reparse the JSON independently with
the development interpreter and confirm all paths/host identifiers are absent.

- [ ] **Step 5: Run one-byte post-extraction mutations**

On separate disposable extracted copies, mutate `python.exe`, one Modori source,
`KIT-IDENTITY.json`, `MANIFEST.json`, and `VERIFY-AND-RUN.ps1`. Each must stop before a
benchmark child begins. Verify no path outside that disposable kit changed.

- [ ] **Step 6: Re-run the clean kit once, clean ignored smoke directories, and confirm Git status**

The second clean execution must produce a new non-overwriting measurement identity.
The worktree must remain clean; only ignored `dist/` deliverables remain.

- [ ] **Step 7: Report the handoff**

Provide clickable absolute paths to the ZIP, `.sha256`, design, and Korean runbook;
state archive size and exact digest; repeat that the user extracts to the internal disk,
uses AC power, photographs any error, and returns only generated evidence files.

Do not mark the parent Decision Ledger goal complete until the user's laptop result is
returned and independently reviewed.
