# Evidence Bundle Resource Preflight Design

**Status:** Approved under the resumed Decision Ledger completion audit on 2026-07-12

**Scope owner:** Canonical evidence-bundle parsing before import quarantine

## 1. Audit finding

The first implementation correctly rejected a five-million-object, 15,000,001-byte
JSON array as `item_limit`, but only after `json.loads` allocated the complete graph.
The isolated process consumed 806,232,064 bytes peak working set and 4,853,842 us.
Rejection after that allocation is not a sufficient resource boundary for an
untrusted import.

The approved 2026-07-12 design also contains two internal contradictions that cannot
be copied into code:

1. it permits 30,000 top-level artifacts while limiting every list to 10,000 items;
2. it limits total decoded string code points to 4,000,000 while the required valid
   16 MiB and 10,000-event benchmark contains 15,684,020 string code points.

The measured valid benchmark is 16,757,534 bytes, contains 10,000 events, 80 padded
artifacts, 361,652 decoded nodes, and no container larger than 10,000 items. The outer
16 MiB byte ceiling already bounds decoded string code points because every decoded
code point consumes at least one source byte and JSON escapes consume more, not fewer,
source bytes per decoded code point.

## 2. Decision

Add a lightweight structural preflight after strict UTF-8 validation but before
`json.loads`. It scans JSON bytes without constructing values, skips quoted content by
using the C-implemented `bytes.find`, and closes three allocation-amplification paths:

- nesting deeper than 8;
- any single pre-parse container larger than 30,000 entries;
- more than 1,000,000 decoded-node equivalents across the document.

After parsing, the existing iterative resource walk enforces the exact semantic
container policy:

- top-level `events`: at most 10,000;
- top-level `artifacts`: at most 30,000;
- every other list or mapping: at most 10,000;
- total decoded nodes, including object keys: at most 1,000,000;
- every ordinary decoded string: at most 512 code points;
- nesting depth: at most 8.

The preflight is deliberately not a second JSON parser. Malformed brackets, escapes,
numbers, literals, duplicate keys, and schema fields still receive their existing
closed outcomes from the strict decoder and typed validators. The preflight may reject
an already over-budget malformed document before reporting its later syntax defect;
it never accepts or repairs a document.

## 3. Wire identity correction

The implemented V1 top-level contract remains:

```text
schema_id
schema_version
canonicalization_id
hash_algorithm
source_project_id
exported_at_utc | null
head { sequence, event_hash }
artifacts[]
events[]
```

This is stricter than accepting a second top-level `dataset_fingerprint` assertion.
Quarantine derives the source fingerprint only after it has verified the complete
chain, reconstructed the typed `ResearchRequestSnapshot`, and confirmed that the
snapshot's current fingerprint equals its typed `StudySpec.dataset_fingerprint`.
It then compares that derived value with the locally supplied dataset fingerprint.
A redundant top-level fingerprint could disagree with those typed authorities and
would add a choice of which copy to trust.

The nested `head` is the canonical grouping of the source sequence and hash. The
optional export timestamp is hash-bound display metadata and grants no freshness,
identity, or authority.

The original Decision Ledger design is updated to this wire and resource contract so
the approved architecture has one authoritative description rather than a silent
implementation deviation.

## 4. Alternatives

### A. Structural allocation preflight plus typed post-parse limits

Selected. A prototype scanned the valid 16,757,534-byte bundle in 234,802 us and
stopped the five-million-object attack after 21,353 us, before JSON allocation. It adds
no dependency, process authority, file access, or platform-specific runtime.

### B. Parse every bundle in a memory-capped child process

Deferred. A child provides a stronger OS failure boundary, but portable memory caps
would require different Windows and POSIX implementations, subprocess authority in a
module currently proven free of execution imports, a new authenticated parent-child
contract, and crash cleanup. That expansion is disproportionate while option A can
bound the demonstrated amplification in-process.

### C. Reduce the 16 MiB envelope or retain post-allocation rejection

Rejected. Reducing the envelope contradicts the accepted benchmark and corpus
contract. Keeping the current parser preserves an 806 MiB allocation attack and is not
an acceptable interpretation of strict resource isolation.

## 5. Scanner contract

The scanner consumes only strict-UTF-8 bytes already below 16 MiB. It maintains a
bounded stack containing container kind, comma count, and whether content was seen.
For valid JSON, a nonempty array has `commas + 1` values and a nonempty object has
`commas + 1` key-value pairs. Total node equivalents are:

```text
1 root node
+ one node for every array item
+ two nodes for every object pair (key and value)
```

This equals the node accounting used by the iterative parsed-value walk. The scanner
checks each completed entry while reading, so it stops a huge container near its
30,001st entry instead of scanning or allocating the remaining document.

Quoted strings are skipped to the next unescaped quote. Backslash parity determines
whether a quote is escaped. Structural characters inside strings never affect counts.
An unterminated string, mismatched closer, illegal literal, or invalid escape is left
to `json.loads`, which retains the existing `invalid_json` mapping when no resource
ceiling has already been exceeded.

## 6. Security invariants

The change must preserve all existing gates:

- exact 16 MiB byte check before UTF-8 decoding;
- SQLite and archive signature rejection;
- BOM and invalid UTF-8 rejection;
- duplicate-key, float, constant, and safe-integer rejection;
- canonical byte reproduction;
- exact top-level and typed artifact/event fields;
- artifact identities and complete event-chain verification;
- path, URL, command, tool, network, execution, and persistence key rejection;
- sensitive free-text rejection;
- imported assertions remain outside the active `Fact` graph;
- no file, archive, network, subprocess, UI, calculation, or persistence imports in
  quarantine.

The preflight accepts no data and grants no authority. It can only allow strict parsing
to continue or terminate with `nesting_limit` or `item_limit`.

## 7. TDD and acceptance

The change is acceptable only when all of the following are fresh evidence:

1. A regression test monkeypatches `json.loads` to fail and proves a 30,001-entry
   container is rejected as `item_limit` before the decoder is called.
2. The same decoder guard proves depth 9 and an injected small total-node overflow are
   rejected before parsing.
3. A 10,001-item nested list is rejected, while the exact 10,000-event benchmark and a
   30,000-item top-level artifact array remain within their distinct structural limits.
4. The 300-mutation corpus, quarantine, promotion, crash, architecture, and full
   repository gates pass unchanged.
5. The five-million-object isolated attack peaks below 192 MiB and terminates in under
   500 ms on the current host. These are local regression ceilings, not population
   claims.
6. The same-host 16 MiB valid-bundle maximum remains below the frozen pre-optimization
   2,682,439 us. The product threshold remains 2,000,000 us and is adjudicated again on
   the target laptop.
7. The kit is rebuilt twice from a clean commit, its ZIP bytes match, two Windows smoke
   executions and five one-byte mutation attacks pass, and the final delivery pair is
   replaced atomically.

If the preflight restores the demonstrated resource boundary but the target laptop
still exceeds the unchanged bundle or open/replay gate, the existing stop rule fires:
do not relax the benchmark or validation contract, and retain deterministic Research
OS without persistent memory/imported decision evidence as the accepted fallback.

