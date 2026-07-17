# Office Benchmark Performance Recovery Design

**Status:** Approved by the resumed Decision Ledger goal on 2026-07-12

**Scope owner:** Decision Ledger, evidence-bundle quarantine, and the sealed office-PC
measurement kit

## 1. Decision

Keep every approved workload, threshold, integrity check, and product-claim boundary.
Recover the failed performance margin by removing provably redundant canonicalization
and redundant whole-input traversal. Also preserve bounded preflight failures as stable
bootstrap codes so a returned error artifact identifies battery and storage failures
without exposing a local path.

This is not permission to trust stored hashes, skip canonical-form verification, reduce
10,000 events or 16 MiB, raise a time or memory ceiling, add a native dependency, or
claim office-hardware suitability from one machine.

## 2. External evidence

The returned artifact
`modori-office-benchmark-89957b3f17104f57b6be25a245668f1e.json` was independently
checked against its SHA-256 sidecar and canonical JSON profile. It identifies source
commit `71b734b8b5d8f413193702ddc1db0df540c6e5d7`, Python 3.12.10, and
SQLite 3.49.1. Three outer runs completed on an HP Laptop 15s-eq2xxx with six physical
cores, 7.326 GiB usable memory, and a fixed WD SN740 NVMe SSD.

The worst returned measurements were:

- 10,000-event open/replay: 1,106,738 us against 1,000,000 us;
- 16 MiB and 10,000-event bundle validation: 2,451,677 us against 2,000,000 us;
- durable append p95: 4,512 us against 50,000 us;
- peak working set: 177,545,216 bytes against 201,326,592 bytes.

All three outer runs exceeded both open/replay and bundle limits. The result therefore
cannot be dismissed as one noisy tail. The device also exceeds the provisional target
profile of at most two physical cores, so it cannot establish low-end representativeness.

The first AC-disconnected attempt returned only `runner_exit_1`. The final result began
32 seconds later and records `ac_power=true`, which is consistent with the operator's
account but does not make the generic error artifact independently diagnostic.

## 3. Root-cause evidence

A cProfile run at the same source commit separated CPU validation work from SQLite I/O.
The absolute profiled times are instrumentation evidence only and are not compared with
the laptop's unprofiled measurements.

For one 10,000-event open:

- `DecisionLedgerStore.open`: 2.065 profiled seconds;
- authoritative reconstruction: 1.976 seconds;
- event-row reconstruction: 1.877 seconds;
- SQLite `execute` calls: 0.104 seconds;
- 30,015 `canonical_bytes` calls: 1.122 cumulative seconds.

`LedgerEvent.create` currently canonicalizes a payload in `_validate_payload`, embeds
and canonicalizes the same normalized payload in the body, then canonicalizes that
payload a third time for `payload_bytes`. The third operation produces bytes already
available from the first operation.

For one 16,757,534-byte bundle parse:

- `EvidenceBundle.from_bytes`: 4.836 profiled seconds;
- canonicalization and typed identity reconstruction: 2.748 cumulative seconds;
- raw character-by-character depth scan: 0.640 seconds;
- iterative resource walk: 0.412 seconds.

The byte limit, strict UTF-8 parse, JSON decoder, and resource walk already bound the
input. Depth can be enforced by carrying container depth in the existing iterative
walk. A JSON decoder `RecursionError` is converted to the same closed
`nesting_limit` outcome. This retains the depth ceiling without a separate Python pass
over all 16 MiB.

## 4. Alternatives

### A. Security-equivalent duplicate elimination

Selected. Canonicalize each event payload once, reuse those exact bytes, and enforce
depth during the resource walk. This changes neither accepted bytes nor validated
identities and adds no dependency.

### B. Trust a stored head, cached decode, or checkpoint

Deferred. It could make opening nearly constant-time, but a cache becomes another
authority boundary and would require schema, invalidation, crash-recovery, and mutation
proofs. It is disproportionate while option A has enough measured headroom to test.

### C. Reduce workload, relax thresholds, or add a native parser

Rejected. Workload or threshold changes would manufacture a pass. A native parser adds
runtime size and supply-chain burden before the dependency-free path is exhausted.

## 5. Event canonicalization change

`_validate_payload` returns both the normalized payload mapping and its canonical bytes.
`LedgerEvent.create` reuses those bytes for `payload_bytes` while still canonicalizing
the complete event body and computing the body and event hashes from that body.

The performance invariant is exactly two canonicalization calls per event creation:
one for the payload and one for the full body. Tests count the real calls and also prove
that round-trip, forgery rejection, hash-chain, SQLite reopen, crash recovery, and
evidence-bundle mutation behavior remain unchanged.

## 6. Evidence-bundle traversal change

The raw scanner is removed from `from_bytes`. `_walk_resources` uses an explicit stack
of `(value, container_depth)` pairs and performs, in one traversal:

- maximum depth enforcement at exactly the existing limit;
- maximum item count enforcement;
- maximum string length enforcement for keys and values;
- forbidden authority-bearing key rejection.

The strict byte ceiling remains before decoding. Duplicate keys, floats, constants,
invalid UTF-8, BOMs, archives, SQLite files, noncanonical JSON, unknown fields, typed
identity mismatches, chain gaps, unresolved references, and sensitive payloads retain
their existing closed error codes. Decoder recursion failure maps to `nesting_limit`.

## 7. Portable failure diagnostics

Preflight failures receive stable process exits:

- `10`: `ac_power_required`;
- `11`: `fixed_internal_volume_required`;
- `12`: `free_space_required`.

PowerShell maps only those declared exits to the corresponding bootstrap artifact code;
all other nonzero exits remain `runner_exit_<number>`. Returned diagnostics contain no
path, username, machine name, traceback, or user content. The runbook and in-kit Korean
README explicitly prohibit OneDrive, cloud-synchronized folders, USB execution, and
reparse-point roots, and direct the operator to `%LOCALAPPDATA%\ModoriBench`.

## 8. Verification and acceptance

The change is acceptable only if all of the following hold without threshold changes:

1. Each new behavior is developed red-green with a focused regression test.
2. Existing ledger, evidence-bundle, quarantine, promotion, crash, mutation, kit,
   privacy, path, and architecture tests pass.
3. The full repository test suite and Ruff pass, and `git diff --check` is clean.
4. A fresh same-host benchmark shows lower open/replay and bundle times than the frozen
   pre-change run at commit `71b734b8`: 1,473,427 us and 2,682,439 us respectively.
   This is a diagnostic comparison, not a portable performance guarantee.
5. A clean committed source builds byte-identical ZIPs twice.
6. The actual CMD-to-PowerShell-to-embedded-Python flow completes, returned JSON and
   sidecar reverify, work and bytecode directories remain empty, and mutation attacks
   still stop before payload execution.
7. The same office laptop is rerun with the new kit. Only that new returned artifact can
   decide whether the two timing gates recovered on the measured device.

If option A does not produce a material reduction on the same host, stop before adding
a cache or altering the schema and reassess the architecture. If it improves locally
but the office laptop still repeatedly fails, retain the negative evidence and decide
whether option B is proportionate; never relax the gate to manufacture success.

