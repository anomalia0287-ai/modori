# Recommendation Benchmark Scorer and Economics Pilot Plan

> **Execution:** Use `superpowers:test-driven-development` task by task. Keep this
> work in `codex/recommendation-benchmark-pilot`; do not implement product semantic
> profiling or an SLM in this plan.

**Goal:** Build a frozen, reproducible recommendation scorer and a human-operable
20-case pilot pack that measures expert-labeling cost without fabricating gold labels.

**Architecture:** Keep benchmark mathematics independent from the product recommender.
`recommendation_benchmark.py` owns immutable contracts and metrics;
`recommendation_benchmark_io.py` owns strict JSONL/XLSX boundaries;
`recommendation_baseline.py` adapts the existing `RecommendationService` into frozen
prediction records. A CLI orchestrates validation, baseline prediction, agreement,
scoring, and cost projection. The pilot pack contains synthetic data, study cards, and
blank reviewer workbooks. No AI-authored record is marked as gold.

**Tech Stack:** Python 3.11+, stdlib dataclasses/json/hashlib/statistics, scipy,
openpyxl, pandas, existing Modori import and recommendation paths, pytest.

## Global Constraints

- Run Python with
  `C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe` from the worktree.
- Follow RED -> verify expected failure -> GREEN for every production behavior.
- Reject unknown schema versions, unknown keys, duplicate case-stage keys, missing
  predictions, non-finite minutes/rates, and mismatched scorer fingerprints.
- Canonical candidate identity is `family + sorted role assignments + design_mode`.
- Public recommendation Top-1 uses only `recommendation_eligible` records. Correct
  clarification and abstention are separate metrics and cannot inflate it.
- A failed or opened frozen split is never silently reused after rules, labels, or the
  scorer change.
- Do not connect the network, add model dependencies, or change product recommendation
  behavior in this plan.
- The checked-in 20-case pack is an economics/annotation pilot, not accuracy evidence.

---

### Task 1: Freeze Core Case, Gold, and Prediction Contracts

**Files:**
- Create: `src/modori/recommendation_benchmark.py`
- Create: `tests/test_recommendation_benchmark.py`

**Interfaces:**
- `RecommendationIdentity(family, roles, design_mode)`
- `PrimaryAction(kind, value)` where kind is `recommend`, `clarify`, or `abstain`
- `GoldRecord(case_id, evidence_stage, action_class, ...)`
- `PredictionRecord(case_id, evidence_stage, primary_action, candidates, level, questions)`
- `ScorerConfig(schema_version, scorer_version, confidence_level)`
- `canonical_json(value) -> str`
- `scorer_fingerprint(config) -> str`

- [ ] Write strict-construction tests first.
- [ ] Verify RED because the module does not exist.
- [ ] Implement frozen dataclasses and explicit `from_mapping` validators. Do not use
      permissive `**mapping` construction.
- [ ] Reject empty IDs, duplicate normalized roles, more than three candidates,
      recommendation actions without identities, clarification actions without fact
      IDs, and abstention actions without reason codes.
- [ ] Canonicalize roles by role name and preserve variable order inside multi-variable
      roles. Hash UTF-8 canonical JSON with SHA-256.
- [ ] Verify GREEN:

```powershell
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_recommendation_benchmark.py -k "contract or fingerprint"
```

### Task 2: Implement Release Metrics and Confidence Bounds

**Files:**
- Modify: `src/modori/recommendation_benchmark.py`
- Modify: `tests/test_recommendation_benchmark.py`

**Interfaces:**
- `score_predictions(gold, predictions, config) -> BenchmarkScore`
- `wilson_lower_bound(successes, total, confidence_level) -> float | None`
- `newcombe_paired_difference_interval(baseline_correct, candidate_correct, confidence_level) -> tuple[float, float]`

- [ ] Write separate failing tests for recommendation Top-1, Top-3 case hit,
      recommendation coverage, clarification accuracy, abstention accuracy, strong
      precision, question efficiency, E1-E5 counts, and zero-denominator status.
- [ ] Prove that correct clarification/abstention does not enter the recommendation
      Top-1 denominator.
- [ ] Prove that a recommendation tie has no Top-1 default, can hit Top-3, and lowers
      coverage.
- [ ] Implement one-sided Wilson lower bounds and lock the known examples: 334/400 is
      above 0.80, 333/400 is below; 370/400 is above 0.90, 369/400 is below.
- [ ] Implement Newcombe 1998 method 10 from the paired 2x2 correctness table. Use
      Wilson marginal intervals and the paper's continuity-corrected positive phi
      numerator. Lock Table III examples, including `(e,f,g,h)=(20,12,2,16)` yielding
      approximately `[0.0562, 0.3292]` at 95 percent.
- [ ] Make missing or extra case-stage predictions a hard error rather than changing
      denominators.
- [ ] Verify GREEN for all metric tests.

Primary reference:
`https://doi.org/10.1002/(SICI)1097-0258(19981130)17:22%3C2635::AID-SIM954%3E3.0.CO;2-C`

### Task 3: Implement Reviewer Agreement and Cost Projection

**Files:**
- Modify: `src/modori/recommendation_benchmark.py`
- Modify: `tests/test_recommendation_benchmark.py`

**Interfaces:**
- `reviewer_agreement(a, b) -> AgreementReport`
- `project_labeling_cost(reviews, adjudications, stage_case_count, rates, contingency=0.25) -> CostProjection`

- [ ] Write failing tests for nominal Krippendorff alpha, mean Jaccard and exact-set
      agreement for recommendation sets and clarification sets.
- [ ] Treat no category variation as `not_estimable`, not a passing alpha of 1.
- [ ] Write failing cost tests using 20 cases, two independent active-minute streams,
      adjudication minutes, hourly rates, separate setup/steward/project-management
      costs, and 25 percent labor contingency.
- [ ] Use the pooled median reviewer case time exactly as the approved formula states:

```text
case_count * ((2 * median_reviewer_minutes) + median_adjudication_minutes) / 60
```

- [ ] Reject missing cases, duplicate reviewer IDs, negative/non-finite times, and a
      case adjudicated without both independent reviews.
- [ ] Verify GREEN.

### Task 4: Add Strict JSONL and Human Workbook Boundaries

**Files:**
- Create: `src/modori/recommendation_benchmark_io.py`
- Create: `tests/test_recommendation_benchmark_io.py`

**Interfaces:**
- `read_jsonl(path, record_loader) -> tuple[object, ...]`
- `write_jsonl(path, records) -> None`
- `load_reviewer_workbook(path, expected_cases) -> ReviewerSubmission`
- `load_adjudication_workbook(path, expected_cases) -> AdjudicatedGold`
- `build_blank_pilot_workbooks(cases, output_dir) -> tuple[Path, Path, Path]`

- [ ] Write RED tests for malformed JSONL, duplicate keys, BOM/encoding handling,
      workbook sheet/column drift, formulas in label cells, missing review time, and
      incomplete reviewer coverage.
- [ ] Use four reviewer workbook sheets: `Case Reviews`, `Recommendations`,
      `Clarifications`, and `Abstentions`. Use an `Instructions` sheet with Korean-first
      wording. The adjudication workbook adds `Adjudication` and `Resolution Minutes`.
- [ ] Use data validation/dropdowns for action class and evidence stage. Do not place a
      candidate answer in any reviewer cell.
- [ ] Hash the workbook template schema separately from reviewer content.
- [ ] Verify workbook round trips and strict rejection behavior.

### Task 5: Generate the 20-Case Economics Pilot Pack

**Files:**
- Create: `scripts/build_recommendation_pilot.py`
- Create: `tests/test_recommendation_pilot_fixtures.py`
- Create: `tests/fixtures/recommendation_benchmark/manifest.jsonl`
- Create: `tests/fixtures/recommendation_benchmark/public/LICENSE-TERMS.md`
- Create: `tests/fixtures/recommendation_benchmark/public/pilot/cases.jsonl`
- Create: `tests/fixtures/recommendation_benchmark/public/pilot/data/*.csv`
- Create: `tests/fixtures/recommendation_benchmark/public/pilot/reviewer-a.xlsx`
- Create: `tests/fixtures/recommendation_benchmark/public/pilot/reviewer-b.xlsx`
- Create: `tests/fixtures/recommendation_benchmark/public/pilot/adjudication.xlsx`

**Interfaces:**
- `build_recommendation_pilot.py --write`
- `build_recommendation_pilot.py --check`

- [ ] Write a RED fixture test requiring exactly 20 unique cases, valid checksums,
      declared license/sensitivity/language/split, valid relative paths, and no gold
      labels.
- [ ] Define deterministic synthetic cases covering: clean descriptives; Likert
      reliability; independent two-group comparison; three-group scale outcome;
      frequency; crosstab; correlation; OLS candidate; repeated wide measures; factor
      items; declared missing code; administrative ID; aggregate row; paired-design
      ambiguity; mixed Korean/English labels; unsupported survey weights/clusters;
      mediation intent; prompt-injection/PII-like text; and a same-data/different-question
      pair.
- [ ] Every study card records unit of observation, question, sampling/design facts,
      visible versus clarification-only facts, and known missing codes. It must not
      contain an asserted gold analysis.
- [ ] Mark all files `synthetic`, `public`, and `no_real_pii`; use stable generation
      seeds even when a case is fully deterministic.
- [ ] Generate the three blank workbooks from the case list and verify no answer cell is
      prefilled.
- [ ] Run `--check` and the fixture tests.

### Task 6: Capture the Current A Baseline Without Changing It

**Files:**
- Create: `src/modori/recommendation_baseline.py`
- Create: `tests/test_recommendation_baseline.py`
- Modify: `scripts/build_recommendation_pilot.py`

**Interfaces:**
- `load_case_dataset(case, root) -> Dataset`
- `candidate_identity(candidate) -> RecommendationIdentity`
- `predict_current_baseline(case, dataset) -> PredictionRecord`

- [ ] Write RED tests proving the adapter uses `read_full`, `metadata_variables`, and
      the existing `RecommendationService` without changing rankings.
- [ ] Freeze the kind-to-family map, including `descriptives -> descriptives_table1`,
      `comparison -> compare_groups`, and `regression -> regression_ols`.
- [ ] Normalize candidate roles from current fields (`outcome_key`, `group_key`,
      `predictor_keys`, `item_keys`, `variable_keys`) and preserve candidate order.
- [ ] If current A has no default, emit an explicit baseline abstention reason; do not
      invent a clarification action that current A cannot produce.
- [ ] Generate an unlabeled `baseline-a-predictions.jsonl` for the 20 pilot cases. It is
      evidence of current behavior, not a score.
- [ ] Verify deterministic byte-identical regeneration.

### Task 7: Add CLI and Nondeveloper Runbook

**Files:**
- Create: `scripts/recommendation_benchmark.py`
- Create: `tests/test_recommendation_benchmark_cli.py`
- Create: `docs/qa/recommendation-benchmark-pilot-runbook.md`
- Modify: `tests/fixtures/README.md`

**CLI commands:**
- `validate-pack`
- `predict-a`
- `validate-submissions`
- `agreement`
- `cost --stage-cases {150,200,800}`
- `score` only after adjudicated gold exists

- [ ] Write RED CLI tests for success JSON, stable exit codes, missing-gold refusal,
      fingerprint mismatch, and malformed workbook diagnostics.
- [ ] Make every command local-only and non-destructive; outputs require an explicit
      path and existing files are not overwritten without `--force`.
- [ ] Write a Korean-first runbook with exact click/type instructions for the two
      reviewers and adjudicator, timing rules, save locations, and the files the owner
      returns. State clearly that Modori/Codex/Claude cannot replace the two qualified
      human reviewers.
- [ ] Verify CLI tests and run the documented `validate-pack` and `predict-a` commands.

### Task 8: Quality Gate, Evidence, and Commit

**Files:**
- Modify: `docs/superpowers/specs/2026-07-10-semantic-profiling-recommendation-memory-design.md`
  only if implementation exposes a necessary contract correction
- Modify: `docs/qa/recommendation-benchmark-pilot-runbook.md`

- [ ] Run focused tests:

```powershell
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_recommendation_benchmark.py tests/test_recommendation_benchmark_io.py tests/test_recommendation_pilot_fixtures.py tests/test_recommendation_baseline.py tests/test_recommendation_benchmark_cli.py tests/ui/test_recommendations.py tests/test_analysis_catalog.py
```

- [ ] Run static checks:

```powershell
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m compileall -q src tests scripts
C:\Users\V\Desktop\TongTong\.venv\Scripts\ruff.exe check src tests scripts
```

- [ ] Run the full default quality gate:

```powershell
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts/quality_gate.py
```

- [ ] Confirm `git diff --check`, validate all manifest hashes, and inspect all three
      workbook renders before claiming completion.
- [ ] Commit the implementation as a focused commit, then report the exact remaining
      human action: two independent qualified reviews and one adjudication pass.
