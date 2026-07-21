# Live Research OS Office Benchmark Legacy-Path Recovery Design

Date: 2026-07-18  
Status: approved recovery design; implementation not yet claimed complete

## 1. Decision

The `0cae87dfeb11` office kit is revoked as target-HP evidence. It remains useful as
development evidence, but its target run exposed an untested legacy-Windows path
boundary. B4 is reopened until a new source-pinned kit passes the complete local,
adversarial, packaging, and quality-gate protocol.

Adopt all three controls together:

1. release mode derives its synthetic workspace as the exact application-owned
   sibling `<extraction-parent>/w`, not `<kit-root>/work`;
2. the runner computes the longest path it can create, in UTF-16 code units, and
   rejects the run before the first child if it exceeds a fixed 240-unit budget;
3. child phases emit closed, stage-specific failure codes instead of collapsing an
   unknown scenario failure to `product_authority_failure`.

The performance gates, protocol repetitions, fixtures, recommendation contracts,
and product claims do not change.

## 2. Evidence and root cause

The target HP machine first rejected a doubly nested extraction with Windows error
`0x80010135`. After extraction was corrected, the benchmark ran through the 20 cold
identity children and failed when the first persistent Research OS scenario began.
It returned no result JSON and produced an inner `product_authority_failure` followed
by the outer `runner_exit_22` wrapper.

The first persistent scenario creates this shape below its isolated `LOCALAPPDATA`:

```text
<work>/<run-uuid>/children/<child-id>/LocalAppData/
  Modori/projects/<32-hex-project>/decision-ledger.sqlite3[-wal|-shm]
```

On the development PC, `LongPathsEnabled=1`; the target machine behaved as a legacy
path environment. With the former `<kit-root>/work` root, the first ledger path is
already about 263 characters for a one-character account name. That explains both
the timing and why identity-only children succeeded: they do not create a Decision
Ledger. The current bootstrap's 230-character check covers immutable manifest files,
not dynamically created ledger, index, journal, marker, quarantine, or result files.

The generic error was a second defect. `_closed_failure_code()` could not distinguish
fixture construction, child-root validation, scenario fingerprinting, and durable
scenario execution. It converted the observed filesystem exception to
`product_authority_failure`, which was safe but not operationally useful.

## 3. Rejected alternatives

### A. Enable Windows long-path policy

Rejected. It can require administrative policy or registry changes, changes the
machine under measurement, and does not represent the default low-cost office-PC
experience. The kit must adapt to the target, not require the target to be repaired.

### B. Shorten only the extraction folder

Rejected. The runbook already uses the deliberately short `MBL-<commit>` parent, but
the immutable kit root name and synthetic hierarchy still push the ledger over the
legacy boundary. It also leaves failed-run quarantine roughly 40 characters longer
than the active path.

### C. Keep the old kit and relabel the run invalid

Rejected. Relabeling is honest but does not repair portability. The old source
identity cannot be silently repacked because the runtime behavior would no longer
match its committed source.

## 4. Exact filesystem contract

Given a verified release kit root `K`:

- results remain under `K/results`;
- the synthetic workspace is exactly `K.parent / "w"`;
- the extraction parent must already be a plain, fixed-drive, non-cloud directory;
- `w` may be created only by `initialize_working_root()` and is accepted thereafter
  only when its exact application marker is valid;
- a pre-existing nonempty unmarked `w`, file, link, junction, reparse point, cloud
  path, UNC path, or removable-drive path is rejected;
- the archive no longer contains or authorizes a mutable `work` subtree;
- failed run roots move only to `w/q/<32-hex-nonce>` after their run marker and exact
  ancestry have been verified;
- the quarantine marker retains the original full run UUID, so shortening the
  directory name does not discard identity;
- cleanup may remove only exact, marked synthetic child/run roots;
- no user dataset, document, arbitrary path, registry key, service, or network
  endpoint enters this boundary.

The extraction parent is already dedicated by the runbook as
`%LOCALAPPDATA%\MBL-<source-commit-prefix>`. The sibling `w` therefore remains inside
one user-owned application directory while removing the immutable kit-name segment
from every persistent scenario path.

## 5. Dynamic path budget

The budget is measured as UTF-16 code units, excluding the terminating null, because
that is the relevant legacy Win32 representation. The hard maximum is **240 units**.
This leaves 19 units below the 259-unit non-null `MAX_PATH` boundary for APIs or
runtime suffixes not represented by the current closed inventory.

The runner derives candidates from the real release protocol rather than a hand-
written example. The inventory includes at least:

- root, run, child, and quarantine markers;
- the longest generated cold/warm P1 child ID;
- `research-task-index.sqlite3`, `-wal`, `-shm`, and `-journal`;
- `decision-ledger.sqlite3`, `-wal`, `-shm`, and `-journal` below a 32-hex project
  directory;
- the active run layout and the shortened quarantine layout.

The maximum candidate and its UTF-16 length are computed before the first benchmark
child. If the value exceeds 240, execution produces no result JSON, emits only the
closed code `dynamic_path_budget_exceeded`, and is classified `invalid_run`. The
absolute path, username, and candidate name are not written to diagnostics.

The target HP path is expected to fall comfortably below 240 after moving to `w`.
That expectation is not a pass claim; only the rebuilt kit's target run can prove it.

## 6. Closed failure contract

Introduce a typed stage failure carrying a reason from the closed inventory. Cause
chains may be inspected only to preserve an already-closed reason; raw exception text
must never enter child stderr, bootstrap files, result JSON, or summaries.

The child inventory adds:

- `child_root_failure`
- `fixture_build_failure`
- `identity_sample_failure`
- `scenario_fingerprint_failure`
- `scenario_execution_failure`

Existing specific reasons such as `fingerprint_timeout`,
`fingerprint_limit_exceeded`, and `acknowledgement_failure` take precedence over the
broader stage reason. The parent accepts an exact child code only if it belongs to the
same closed inventory. The release preflight adds
`dynamic_path_budget_exceeded`.

When the Python runner has already published one new closed bootstrap diagnostic,
the PowerShell wrapper must not create a second generic `runner_exit_22` file. It may
print the wrapper exit to the console, but the result directory retains one
authoritative diagnostic for that invocation. Pre-existing diagnostics do not count
as the new runner diagnostic.

## 7. TDD and verification

Implementation begins with failing tests that prove:

1. the former `K/work` projection exceeds the legacy budget for the reproduced
   target-style path while `K.parent/w` passes;
2. counting uses UTF-16 units, not Python code points;
3. the release publisher receives exactly the sibling `w` and never creates or uses
   `K/work`;
4. active and quarantine candidates both remain within the fixed inventory;
5. an over-budget extraction parent fails before child execution with
   `dynamic_path_budget_exceeded` and no result JSON;
6. each injected child-phase failure returns its exact closed stage code without raw
   exception text;
7. a new inner runner diagnostic suppresses only the duplicate outer file;
8. package directory and ZIP verification reject a `work` subtree;
9. file-operation audit and Korean runbook describe the new exact boundary.

After focused tests pass, the replacement kit must pass, without waivers:

- Ruff and the security/static gates;
- the complete repository quality gate;
- three independent byte-identical outer builds;
- ZIP inventory, CRC, digest, runtime, and identity verification;
- all 300 mutation/adversarial cases;
- the full local 20-cold/30-warm protocol and independent result recomputation;
- a final clean-worktree/source-identity audit.

Only then may it replace the revoked USB candidate. B5 remains incomplete until that
new kit is executed on the same HP laptop and the returned JSON, sidecar, summary,
execution conditions, source identity, and every frozen gate are independently
verified.

## 8. Claim boundary

This recovery can establish only portable execution and timing of the synthetic
Decision Ledger/Research OS path on the measured machines. It cannot establish
recommendation validity, numerical accuracy, human equivalence, SPSS superiority,
privacy for unexamined workflows, or general Windows compatibility beyond the tested
contract. A target failure after this repair is reported as `valid_stop` or
`invalid_run` according to the pre-existing rules; thresholds are never relaxed to
manufacture a pass.
