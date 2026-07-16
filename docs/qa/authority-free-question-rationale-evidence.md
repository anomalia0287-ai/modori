# Authority-Free Question Rationale — QA Evidence

**Evidence class:** `planner_explanation_fidelity_internal`  
**Date:** 2026-07-16 (Asia/Seoul)  
**Branch:** `codex/research-os-contract-design`  
**Measured tree:** `cf90294526c2fe122e5005d6ba17baed4852a094`  
**Status:** resource and integrity gates passed; product UI integration remains out of scope

## 1. Claim boundary

This record supports one bounded claim:

> Given one exact outstanding locally committed V2 clarify passport, its bound
> clarification registry, and the recorded minimax evaluation trace, Modori can verify
> and present why the recorded question ranked ahead of its recorded runner-up without
> rerunning the resolver or planner and without inventing free-form prose.

This is internal explanation-fidelity evidence. It is not human gold and does not
measure recommendation validity.

This record does **not** establish:

- that the selected question, later analysis recommendation, or research conclusion is
  substantively correct;
- academic truth, expert approval, human parity, or superiority to an expert or SPSS;
- statistical calculation accuracy;
- validity of the complete candidate ordering beyond the selected-versus-runner-up
  first differing rank component;
- office-PC latency, end-to-end application latency, or UI usability;
- integrity of the entire project ledger when this projection reports a local evidence
  failure; or
- deployment of this read model in QML, a controller, or the legacy heuristic
  recommendation surface.

## 2. Verified implementation chain

| Commit | Verified change |
|---|---|
| `4492cab` | Reject a clarification plan whose marked selection is not the minimum recorded rank key. |
| `f02efd5` | Add strict in-memory question-rationale result, projection, comparison, and question-copy contracts. |
| `a5e91e1` | Project one exact outstanding passport and bound registry into a verified rationale read model. |
| `6d64920` | Render closed Korean/English `guided` and `standard` read models. |
| `57ba053` | Attack lifecycle, provenance, mutation, no-second-search, and authority boundaries. |
| `cf90294` | Lock the resource gate and correct the registry-size/candidate-count distinction. |

No QML, controller, calculation engine, SQLite schema, evidence-bundle wire contract,
package payload, or VM payload was changed by this slice.

## 3. Fixture identity and corrected count

The locked P1 fixture contains:

- 15 questions in `build_p1_clarification_registry()`;
- 4 candidates actually eligible, evaluated, and sealed into this request's
  `ClarificationPlan.evaluations`;
- 2 ledger events, 5 artifacts, and 1 inspected committed-passport record; and
- a registry digest that exactly matches the passport binding.

The implementation plan originally called this a “15-candidate” fixture. Direct
inspection disproved that wording. Commit `cf90294` corrects it to a 15-question
registry with 4 recorded evaluated candidates. The performance claim uses the actual
recorded count and does not relabel registry inventory as evaluated candidates.

## 4. Environment

| Item | Value |
|---|---|
| OS | Windows 11, build family `10.0.26200`, AMD64 |
| Python | CPython 3.12.10, MSC v.1943, 64 bit |
| CPU | 12th Gen Intel(R) Core(TM) i5-12500H |
| Logical processors visible to process | 16 |
| R anchor runtime | Rscript 4.5.3 (2026-03-11) |
| Python executable | `C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe` |
| R executable | `C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe` |

The resource result below is a development-PC internal gate. It is not a substitute
for the earlier HP office-laptop benchmark and does not predict that machine's UI
latency.

## 5. Resource gate

Command:

```powershell
$env:PYTHONPATH='C:\Users\V\.codex\worktrees\b39f\TongTong\src'
$env:MPLCONFIGDIR='C:\Users\V\.codex\worktrees\b39f\TongTong\matplotlib-cache'
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' `
  -m pytest tests/test_question_rationale_performance.py -q -s -p no:cacheprovider
```

The fixture and inspected history were constructed outside the timed region. The timed
operation was one complete pure projection plus one Korean `standard` presentation.
There were 50 warmups and exactly 1,000 timed samples. The p95 is
`sorted(samples)[949]`. Allocation was measured in a separate post-warmup
`tracemalloc` block.

| Metric | Result | Gate | Outcome |
|---|---:|---:|---|
| Registry questions | 15 | exact fixture assertion | pass |
| Recorded evaluated candidates | 4 | exact passport assertion | pass |
| Timed samples | 1,000 | exactly 1,000 | pass |
| Median | 1,202,600 ns (1.203 ms) | descriptive | — |
| p95 | 1,868,800 ns (1.869 ms) | at most 10,000,000 ns | pass |
| Maximum | 3,131,000 ns (3.131 ms) | descriptive | — |
| Traced peak | 130,817 bytes | at most 524,288 bytes | pass |
| 20 repeated `repr` byte values | 1 unique value | exactly 1 | pass |

Focused resource result: `1 passed in 1.58s`.

The repeated `repr` comparison is test-only determinism evidence. It is not a product
serialization or wire-compatibility contract.

## 6. Integrity and adversarial evidence

The attack gate covered:

- planner and resolver method poisoning after fixture creation, proving that projection
  performs no second search;
- direct AST scans that reject filesystem, SQLite, network, subprocess, model,
  retrieval, resolver, planner-execution, transition, and ledger-write authority in
  the two production files;
- consumed, retracted, stale-request, and stale-registry sources;
- absent and digest-mismatched registries;
- selected-question revision drift both normally and under a poisoned registry digest;
- alternative-question revision drift after the selected-question audit;
- a moved selected marker, changed selected identity, and changed embedded plan with an
  unchanged reference digest;
- bare passports, mappings, and imported assertions at the history boundary;
- registry declaration-order permutation;
- a non-ranking context metric change that must not become the decisive dimension;
- a test-only false caution-code mutation; and
- a missing closed-catalog key.

Attack gate result: `80 passed in 0.49s`.

Final focused planner/projector/presenter/resource gate result:
`103 passed in 4.43s`.

Ruff reported `All checks passed!` for the changed production and test files.
`compileall -q src tests` and `git diff --check` both exited zero.

## 7. Full repository gate and environment diagnosis

The first full-suite attempt omitted `MODORI_RSCRIPT`. It produced:

```text
4 failed, 2118 passed, 16 skipped in 180.86s
```

All four failures were the same environment defect: the factorial-ANOVA R anchor could
not find an executable Rscript. No product or test criterion was changed. After setting
the already provisioned executable, the four previously failing nodes passed:

```text
4 passed in 7.93s
```

The complete repository gate was then rerun from the beginning with:

```powershell
$env:PYTHONPATH='C:\Users\V\.codex\worktrees\b39f\TongTong\src'
$env:MPLCONFIGDIR='C:\Users\V\.codex\worktrees\b39f\TongTong\matplotlib-cache'
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' `
  -m pytest -q -p no:cacheprovider
```

Result:

```text
2133 passed, 5 skipped in 173.60s
```

The five expected skips were independently enumerated with `-rs`:

1. one `paired_comparison` recommendation-eligibility assertion that is not applicable
   to that analysis contract;
2. three bootstrap-adequacy slow-stat cases gated by
   `MODORI_RUN_SLOW_STATS=1`; and
3. one factorial-ANOVA slow performance case gated by
   `MODORI_RUN_SLOW_STATS=1`.

No skip in the final environment was caused by missing R, a missing R package, or
unavailable symlink creation.

## 8. Decision

The authority-free rationale slice passes its fixed resource, mutation, provenance,
closed-copy, static-authority, and full-repository gates. It may remain as a verified
in-memory read-model capability.

This is **not** approval to connect it to the current legacy recommendation UI. A
future adapter must consume the V2 planner-backed rationale only, return no control for
`not_applicable`, clear stale available content before showing status-only states, and
preserve the existing `guided`/`standard` distinction. That adapter requires a separate
approved UI slice and its own usability evidence.
