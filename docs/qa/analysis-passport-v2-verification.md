# AnalysisPassport V2 Verification Record

Date: 2026-07-15  
Branch: `codex/research-os-contract-design`  
Implementation and regression head under verification: `4f45233`

## 1. Decision

Status: **passed for the reduced V2 + fresh-replan slice**.

The implemented slice is:

- exact V1 read compatibility;
- strict AnalysisPassport V2 decoding;
- request, registry, selected-question, decision, and embedded-plan commitments;
- one resolver search per plan;
- V1 transition rejection and fresh V2 replanning;
- one durable outstanding V2 clarify passport per
  `(project, request binding, registry)` key;
- exact active-passport gating before a durable answer;
- SQLite and evidence-bundle history enforcement;
- foreign-passport authority quarantine; and
- no direct V1-to-V2 migration producer.

Direct migration remains a reserved design and is **not implemented**. The current
evidence does not justify its cost because no real V1 population requiring lineage
preservation has been demonstrated.

## 2. Verified commits

| Commit | Verified responsibility |
|---|---|
| `d8f2be8` | Strict ClarificationPlan decoder and historical planner allowlist |
| `8ad5bc5` | AnalysisPassport V2 closed wire contract |
| `53de4c6` | Request binding and single-pass `resolve_and_plan` |
| `18ab4dc` | V2 transition authority and V1 typed rejection |
| `f1a333f` | Pure ledger-derived PassportHistory reducer |
| `6fe2018` | Durable commit, active-answer gate, and concurrency closure |
| `b4dbd0a` | Crash, mutation, quarantine, and resource closure |
| `4f45233` | Unrelated-head race rejection without stale replanning |

The approved reduced design is `2be9fc7`; the executable TDD plan is `ae67673`.

## 3. Frozen compatibility and V2 contract

The frozen V1 mapping still excludes both V2 binding fields and has digest:

```text
256019034d7fb5fbe1ac1547c5c3516dfc83ae0f125f059c5ceb91f6c9d41ec8
```

V2 adds exactly:

- `request_binding_digest`;
- `clarification_registry_digest`; and
- for clarify, one `ClarificationRef` plus its complete `ClarificationPlan`.

The locked worst P1 plan is exactly 14,267 canonical bytes, below the fixed 64 KiB
gate. The V2 evidence representation requires a maximum JSON container depth of 10;
depth 11 is still rejected during structural pre-scan. The paired-request passport
used for the contract-overhead measurement was 3,164 canonical bytes.

## 4. Test and static-verification evidence

### Focused closure

Command:

```text
python -m pytest \
  tests/test_research_os_passport.py \
  tests/test_research_os_passport_audit.py \
  tests/test_research_os_service.py \
  tests/test_research_os_planning.py \
  tests/test_research_os_transitions.py \
  tests/test_research_memory_passport_state.py \
  tests/test_research_memory_ledger_contracts.py \
  tests/test_research_memory_ledger_store.py \
  tests/test_research_memory_evidence_bundle.py \
  tests/test_research_memory_promotion.py \
  tests/test_research_memory_quarantine.py \
  tests/test_research_memory_crash_recovery.py \
  tests/test_research_memory_performance.py \
  tests/test_research_os_architecture.py -q -p no:cacheprovider
```

Result: **285 passed in 30.92s**.

### Complete repository suite

The first complete run found one real audit-test incompatibility:

```text
2049 passed, 5 skipped, 1 failed in 186.77s
```

`test_file_operation_audit.py` treated the new `self.resolve(...)` planning call as if
it were `Path.resolve(...)`. The security audit allowlist was not relaxed. The call was
expressed through the same bound method without the false-positive syntax, and its
single-call spy and no-I/O architecture tests were rerun.

The complete suite was then rerun from the beginning with the pinned Python/R/test
environment:

```text
2050 passed, 5 skipped in 131.15s
```

After adding the explicit unrelated-head race regression, the complete suite was run
once more. Final result:

```text
2051 passed, 5 skipped in 131.80s
```

The five skips equal the pre-slice environmental skip count; this slice added no skip.

### Static and bytecode gates

```text
python -m ruff check src tests scripts
All checks passed!

python -m compileall -q src tests scripts
exit 0

git diff --check
exit 0
```

## 5. Single-search and concurrency evidence

- A spy proves `resolve_and_plan` calls `resolve` exactly once.
- Returning an already-active passport invokes no planner search.
- In the two-connection barrier race, exactly one receipt has `appended=True`.
- The loser reverifies the winning chain and returns the winner's exact passport
  digest.
- The resulting verified ledger contains project creation plus exactly one
  `passport_committed` event.
- A head change that does not yield the exact active key is rejected rather than
  retried with stale inputs.

## 6. Crash matrix

Twenty forced-process-death cases passed: ten generic append stages and the same ten
stages for V2 passport commit.

| Forced-death stage | Permitted recovered state |
|---|---|
| `before_begin` | Original project state only |
| `after_begin` | Original project state only |
| `after_head_check` | Original project state only |
| `after_artifacts` | Original project state only |
| `after_event_row` | Original project state only |
| `after_relationships` | Original project state only |
| `after_materialized` | Original project state only |
| `after_head_update` | Original project state only |
| `before_commit` | Original project state only |
| `after_commit_before_receipt` | Complete committed V2 state only |

No recovered database contained an artifact-only, event-only, changed-snapshot, or
unverifiable intermediate state.

## 7. Mutation and adversarial closure

The following failures are independently covered:

- V1/V2 cross-shape fields and unknown fields;
- request-binding splice;
- registry-digest drift against the current local catalog;
- embedded plan digest drift;
- selected question version and digest drift;
- source decision digest drift;
- `created_event_ref` mismatch;
- wrong `passport_artifact_id` artifact role;
- changed or non-exact request snapshot subjects;
- a V2 answer without a prior commit;
- duplicate outstanding passports for one key;
- consumed-passport replay and object-identity reuse;
- imported or ephemeral passport use as local authority; and
- production construction of `MIGRATION_APPLIED`.

The existing 300-case deterministic quarantine mutation corpus also passed unchanged.
An AST guard finds zero production calls that construct an event with
`event_kind=LedgerEventKind.MIGRATION_APPLIED`.

## 8. Foreign bundle result

A structurally valid foreign V2 bundle can be integrity-inspected. Its passport is not
returned as a passport, Fact, transition, or local authority. Only downgraded
`ImportedAssertion` values may cross quarantine. A self-consistent foreign bundle with
a non-current V2 registry digest is rejected as `stale_catalog`. V1 continues to use
the frozen Method Space and ruleset freshness checks.

## 9. Planner evidence

Command:

```text
python scripts/benchmark_counterfactual_clarification.py --iterations 1
```

Observed locked evidence:

- matrix cases: 108;
- trajectories: 256;
- independent-oracle disagreements: 0;
- E4/E5 failures: 0;
- repeated-question attempts for bounded minimax: 0;
- deliberately killed mutants: 3/3;
- locked evaluated states: 11,539;
- locked memo hits: 5,172;
- state cap hit: false;
- locked elapsed time: 2,090.46ms;
- locked peak working set: 70,365,184 bytes; and
- development gates: below 5,000ms and 256 MiB.

Additional benchmark suite result:

```text
18 passed in 14.90s
```

## 10. Resource measurements

### V2 contract overhead, resolution excluded

Five fresh samples measured only `resolve_and_plan` contract construction after the
decision was fixed. The maximum was:

| Metric | Observed | Fixed gate |
|---|---:|---:|
| Elapsed | 12,154us | < 50,000us |
| Peak tracemalloc | 155,512 bytes | < 5,242,880 bytes |
| Worst locked plan | 14,267 bytes | < 65,536 bytes |

### Decision-memory development PC measurement

Environment: Python 3.12.10, SQLite 3.49.1, 16 effective logical CPUs,
16,802,762,752 physical bytes. Storage was not classified.

| Path | Median | P95 | Max | Additional measurement |
|---|---:|---:|---:|---:|
| Open/replay 1,000 events | 137,543us | 144,755us | 144,755us | 38,879,232B peak working set |
| Full integrity, 1,000 events | 128,791us | 133,664us | 133,664us | 3 repetitions |
| Bundle validation | 164,198us | 165,703us | 165,703us | 732,065 input bytes |
| Full-sync append | 9,730us | 11,168us | 11,749us | 25 measured, 10 warmups |

The fixed regression gates remained unchanged: open/full-integrity below 10 seconds
and 192 MiB, and every measured append below 1 second.

## 11. Stop-criterion disposition

| Criterion | Result |
|---|---|
| Frozen V1 mapping or digest changes | Did not occur |
| V2 answer appends without prior active commit | Rejected at coordinator, store, and bundle boundaries |
| Two outstanding clarify passports share one key | Rejected; concurrency has one winner |
| Planner performs a second search | Did not occur |
| V2 plan exceeds 64 KiB | Did not occur; 14,267 bytes |
| V2 contract exceeds 50ms/5MiB | Did not occur in the fixed measurement |
| Existing 1,000-event or append ceiling fails | Did not occur |
| Direct migration becomes necessary | Not demonstrated; producer remains absent |

No stop criterion fired for the reduced fresh-replan slice.

## 12. Explicit nonclaims and deferred work

This record is **not** evidence of:

- human gold or expert equivalence;
- recommendation validity;
- numerical calculation accuracy;
- SPSS superiority or broad social-science coverage;
- office-PC remeasurement of this V2 slice;
- local SLM value;
- safe cloud processing of user data; or
- correctness of a direct V1-to-V2 migration.

The external-review opportunity to render the embedded counterfactual trace as
“why this question?” guidance remains a separate UI/product slice. It must not grant
new authority or expose raw/free text. Direct migration may be reconsidered only after
a real lineage-preservation population and benefit are demonstrated.
