# Counterfactual Clarification Planner Evidence

Date: 2026-07-15 KST

Status: **conditional pass for the deterministic Research OS research branch; blocked
for product release integration.** The bounded minimax planner passed its predeclared
formal-fidelity, structural-cap, development-time, and memory gates. This evidence does
not establish recommendation validity, statistical accuracy, expert equivalence, or
broad social-science coverage. Product integration remains blocked by the unresolved
AnalysisPassport clarification-revision binding gap and by the separate absence of an
independently anchored recommendation-validity corpus.

## Claim boundary

This work tests whether C1 can select one decision-relevant clarification question at a
time more rigorously than a batch form, fixed tree, frozen severity-impact sorter, or
one-step greedy policy. It does not test whether the underlying P1 decision table chooses
the scientifically correct method for a real study. The independent oracle reimplements
the formal policy; it is not a human expert and is not recommendation gold.

The strongest supported claims are:

- the production planner implements the frozen bounded-minimax contract on the complete
  locked small state space;
- the selected policy is never formally worse than one-step greedy on that state space
  and is strictly better on two nontrivial roots;
- refusal, exhaustion, integrity failure, and resource exhaustion remain closed outcomes;
- the frozen all-unknown P1 operating slice completes inside the structural, time, and
  memory gates on the recorded development machine; and
- the planner adds no file, network, calculation, subprocess, tool, or persistence
  authority.

It is prohibited to relabel these results as human gold, recommendation accuracy,
statistical correctness, or proof that Modori outperforms SPSS or a qualified researcher.

## Source and evidence identity

| Item | Pinned value |
| --- | --- |
| Branch | `codex/research-os-contract-design` |
| Baseline before planner work | `cc1e94bce5d147717447e195179bb68584a2574e` |
| Benchmark implementation commit | `bb78ec6501ef1d90080a108ab32a104cb5861df5` |
| Planner version | `research-os-counterfactual-minimax-v1` |
| Evidence class | `planner_fidelity_internal` |
| Fresh JSON path | `.tmp/counterfactual-clarification-evidence.json` (untracked, reproducible output) |
| Fresh JSON SHA-256 | `C733BE5CCB143180DEABE472986A6CED8C7CBE9FF89618009601FB8F3E31A33D` |
| Fresh JSON size | 11,311 bytes |
| Toy Method Space digest | `144f6e9405cc2c2c4e135f590130fec587bf2bc2f59ee4bfffc179dc63a7245f` |
| Toy registry digest | `8bc060a3014f1f6add68e8a58c854bec6e159a517969d06cd39be620f7e035f2` |
| P1 Method Space digest | `3c8eb1ce4ff19c703fc30ef6ceb77c34ba4d03c06b55b65b09a7585b5b576b29` |
| P1 registry digest | `ed762a596485de8b678357619455de3519d13659c157208cf9a8e05b0414029e` |
| P1 outcome digest | `98d9cd1f21c88d0a3b95e1100beceae0630f1dc8987785bab376582d1eec19ef` |

The JSON is intentionally not a tracked answer fixture. Regeneration must be able to
disagree. A changed result therefore cannot be hidden by updating a golden file.

## Environment

| Item | Recorded value |
| --- | --- |
| OS | Windows 11 `10.0.26200`, AMD64 |
| Python | CPython 3.12.10, MSC v.1943, 64 bit |
| SQLite | 3.49.1 |
| CPU | 12th Gen Intel Core i5-12500H, 16 logical processors |
| Physical memory | 16,802,762,752 bytes |

The policy-matrix timings below run with `tracemalloc` enabled. The P1 elapsed samples do
not run under `tracemalloc`; process peak working set is read from
`K32GetProcessMemoryInfo` after the complete benchmark process and is therefore a
conservative process-lifetime peak, not an isolated allocation measurement.

## Complete small-state matrix

The locked contract contains three binary facts. Each begins as unknown, first answer, or
second answer, producing 27 fact states. Budgets zero through three produce exactly 108
root cases. Completing the remaining unknown facts produces 256 deterministic
trajectories.

Results:

- 108/108 production roots agreed with the separately implemented exhaustive oracle on
  selected question and worst terminal loss;
- 0 oracle disagreements;
- 0 E4/E5 comparative failures;
- 0 cases where bounded minimax was worse than one-step greedy;
- 2 strict bounded-minimax advantages, at the all-unknown state with budgets two and
  three;
- 0 repeated-question attempts; and
- all three deliberate mutants were killed: worst-branch `max` changed to `min`, E4/E3
  priority reversed, and duplicated rule addresses counted more than once.

The all-case worst risk vector is identical across policies because budget-zero roots
contain unavoidable unresolved risk. It is not evidence that the policies are equally
good. Root-level strict loss and unnecessary-question counts are the discriminating
measures.

| Policy | Strictly suboptimal roots | Unnecessary questions vs oracle | Worst / median questions | Root states total / max | Memo hits total / max | Matrix median / max ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Batch form | 20 | 64 | 3 / 1 | 0 / 0 | 0 / 0 | 0.164 / 0.256 |
| Fixed tree | 6 | 24 | 3 / 1 | 108 / 1 | 0 / 0 | 4.784 / 7.730 |
| Frozen severity-impact | 4 | 12 | 3 / 1 | 108 / 1 | 0 / 0 | 4.816 / 9.108 |
| One-step greedy | 2 | 4 | 3 / 1 | 276 / 7 | 0 / 0 | 21.994 / 41.112 |
| Bounded minimax | 0 | 0 | 2 / 1 | 413 / 48 | 40 / 16 | 203.585 / 312.668 |
| Independent oracle | 0 | 0 | 2 / 1 | 298 / 27 | 40 / 16 | 111.644 / 148.922 |

The bounded production implementation evaluates more states than the formal oracle
because it also creates and safety-checks refusal snapshots and emits digest-bound branch
evidence. The timing cost is measurable but far below the P1 gate.

## Locked P1 operating slice

The P1 stress slice sets every one of the 15 rule-referenced fact addresses to a typed
unknown value, uses the experimental surface, and grants the full three-question budget.
It is deliberately harsher than a partially completed study specification.

| Measure | Result | Gate |
| --- | ---: | ---: |
| Evaluated states | 11,539 | below 250,000 |
| Memo hits | 5,172 | descriptive |
| Selected question | `confirm_research_goal` | deterministic |
| Distinct outcomes over five runs | 1 | exactly 1 |
| Elapsed samples (ms) | 2872.916, 2855.542, 3140.868, 2905.002, 3286.034 | descriptive |
| Worst elapsed | 3286.034 ms | below 5000 ms |
| Peak process working set | 71,180,288 bytes (67.883 MiB) | below 256 MiB |
| State-cap abstentions | 0 | exactly 0 |

An earlier unoptimized measurement did not pass the time gate: approximately 10.8
seconds initially, then 5.663 seconds in a long-run sample after partial optimization.
Profiling showed repeated canonical serialization and repeated evaluation of the same
immutable fact/rule pairs. The accepted optimization retains the same 11,539 evaluated
states, 5,172 memo hits, selected question, formal loss, and trace contracts; it only
caches projected answer objects, per-fact digests, and rule traces inside one resolver
call. No cache persists across requests.

## Adversarial and metamorphic coverage

Executable coverage includes:

- a valid depth-two counterexample where the best root depends on the second question;
- a misleading branch that defeats optimistic `min` scoring;
- an E4/E3 ordering counterexample;
- duplicated rules that cannot multiply one fact address's risk;
- fact, registry, and branch-declaration order permutations;
- `unknown`, `conflict`, `stale`, imported/inferred trust failures, and
  `not_applicable` behavior;
- refusal projections that must not open recommendation or routing;
- actual `not_sure` answer transitions across budgets three to zero, with no repeated
  state or question;
- exact budget exhaustion and exact structural-cap exhaustion;
- malformed projection, question, rule, and fact contracts; and
- route evidence from unverified through roundtrip-verified.

The work also found and fixed a pre-existing boundary error: `not_applicable` had been
passed to empty/non-empty predicates as the non-empty string `"not_applicable"`. It now
satisfies `EMPTY`, fails `NONEMPTY`, and remains a literal value only for `IN` predicates.

## Executed gates

1. Focused Research OS gate after the final performance change:

   ```text
   pytest [13 Research OS and benchmark files] -q -p no:cacheprovider
   223 passed in 15.39s
   ```

2. Fresh locked benchmark:

   ```text
   python scripts/benchmark_counterfactual_clarification.py \
     --iterations 100 \
     --output .tmp/counterfactual-clarification-evidence.json
   exit code: 0
   JSON SHA-256: C733BE5CCB143180DEABE472986A6CED8C7CBE9FF89618009601FB8F3E31A33D
   ```

3. Final complete repository gate:

   ```text
   MODORI_RSCRIPT=C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe
   PYTHONPATH=<worktree>\src
   MPLCONFIGDIR=<worktree>\matplotlib-cache
   python -m pytest -q -p no:cacheprovider
   1979 passed, 5 skipped in 160.77s
   exit code: 0
   ```

   The five skips are the unchanged understood set: one analysis-module contract that
   does not require recommendation eligibility and four tests delegated to the explicit
   slow-statistics gate (`MODORI_RUN_SLOW_STATS=1`). The configured R reference runtime
   was present; the full output contains no missing-R skip.

   The first complete run was not silently discarded. It produced `1978 passed, 5
   skipped, 1 failed`: the new optional benchmark JSON writer had not yet been entered in
   the repository's direct-file-operation audit. The script was added to the exact audit
   allowlist with a documented developer-only, caller-selected single-file boundary;
   both audit tests then passed before the successful complete rerun.

4. Final static and source audit:

   ```text
   python -m ruff check .
   All checks passed!

   python -m compileall -q src tests scripts
   exit code: 0

   git diff --check
   exit code: 0

   git diff --name-only cc1e94b... -- src/modori/steps src/modori/core dist
   <empty>

   active branch: codex/research-os-contract-design
   active worktree: C:/Users/V/.codex/worktrees/b39f/TongTong
   ```

## Predeclared gate disposition

| Gate | Result |
| --- | --- |
| Exact independent-oracle agreement | Pass: 108/108 |
| Zero E4/E5 failure, leak, loop, or simulated-provenance mutation | Pass in locked executable scope |
| Exactly one question per clarification decision | Pass |
| Never worse than one-step on locked roots | Pass: 0 regressions |
| At least one strict nontrivial advantage | Pass: 2 roots |
| Declared permutation determinism | Pass |
| No state-cap abstention on locked P1 slice | Pass: 11,539 / 250,000 states |
| Development worst elapsed below 5 seconds | Pass: 3.286 seconds |
| Peak process memory below 256 MiB | Pass: 67.883 MiB |
| Full repository and static gates | Pass: 1979 passed, 5 understood skips; Ruff/compileall/diff check pass |
| Replay-stable question revision in AnalysisPassport | **Fail / unresolved** |
| Independent recommendation-validity evidence | **Not tested / unavailable** |

## Decision and residual limits

The bounded minimax architecture receives a **conditional-go as an internal,
deterministic clarification-policy implementation**. Its strict advantage is real but
narrow: two locked roots. That is sufficient to reject simplification to one-step greedy
under the predeclared rule, but not sufficient to call the work a validated product
innovation.

Product release integration is blocked for two independent reasons:

1. `ClarifyPayload` in AnalysisPassport schema version 1 binds question IDs and blocking
   fact addresses but not the selected question's version and digest. The decision trace
   detects drift, but the transition layer cannot prove that a later answer refers to the
   exact question revision originally asked. Schema version 1 must not be silently
   mutated.
2. Formal planner fidelity does not validate the scientific content of C1 rules. A
   qualified-reviewer or genuinely independent anchor is still needed before any public
   recommendation-accuracy, expert-equivalence, or broad-coverage claim.

The correct next design task is a separately approved, migrated AnalysisPassport schema
revision with typed clarification revision references, followed by recommendation-
validity work. UI work, calculation-engine coupling, SLM adoption, and automatic analysis
execution are not authorized by this evidence.
