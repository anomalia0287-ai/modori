# Risk-Bounded Counterfactual Clarification Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Subagents are
> prohibited for this work by the user.

**Goal:** Replace C1's severity/count clarification sorter with a pure, bounded
counterfactual minimax planner that asks one question per round, never repeats a
`not_sure` question, and proves its root choice against an independent finite oracle.

**Architecture:** A new `counterfactual_planner` module owns immutable planner
contracts, answer projections, exact depth-limited search, memoization, structural
resource limits, and non-authority audit traces. `C1Resolver` remains the scientific
snapshot authority and supplies a pure callback that reevaluates ephemeral fact maps.
`ResearchOsService` injects the already frozen clarification registry. Product UI,
calculation, persistence, and the AnalysisPassport schema remain unchanged.

**Tech Stack:** Python 3.12 frozen dataclasses, closed enums already present in the
Research OS, standard-library SHA-256/JSON through `canonical_digest`, pytest, Ruff.
No new dependency.

## Global Constraints

- Work only in `C:\Users\V\.codex\worktrees\b39f\TongTong` on branch
  `codex/research-os-contract-design`.
- Do not switch branches, merge, push, edit another worktree, or delete any worktree.
- Baseline before implementation: commit `6ac45a1` descends from `cc1e94b`; full suite
  `1942 passed, 5 skipped`; focused Research OS `187 passed`; focused Ruff passed.
- Use no subagents.
- Ask exactly one clarification question per resolver decision; the total inline budget
  remains an integer from zero through three.
- A simulated answer is never production evidence and cannot mutate a request, spec,
  dataset, ledger, analysis configuration, or passport.
- `not_sure` is safety-tested but excluded from information-gain minimax; after an actual
  `not_sure` answer, the same question cannot be automatically asked again.
- E5, E4, E3, E2, and E1 residual risk is lexicographic and never a weighted average.
- A fixed state-evaluation cap, not elapsed time, controls resource exhaustion. Cap
  exhaustion produces typed abstention with no heuristic fallback.
- Do not change `modori.analysis_passport` schema version 1 or any clarification question
  text/version in this plan. The question-revision binding gap remains an explicit
  integration blocker.
- Research OS production code retains no file, network, UI, calculation, subprocess,
  dynamic execution, or persistence imports/calls.
- Formal-oracle and policy-comparison results are planner-fidelity evidence only, not
  human gold or recommendation-validity evidence.

---

### Task 1: Freeze planner contracts and counterfactual branch projection

**Files:**
- Create: `src/modori/research_os/counterfactual_planner.py`
- Create: `tests/test_research_os_counterfactual_planner.py`
- Modify: `src/modori/research_os/__init__.py`
- Modify: `tests/test_research_os_architecture.py`

**Interfaces:**
- Consumes: `Fact`, `FactState`, `canonical_digest`, `ClarificationRegistry`,
  `ClarificationSpec`, `AnswerKind`, and `BranchMatchKind`.
- Produces: `PLANNER_VERSION`, `BlockingFact`, `DecisionSnapshot`, `TerminalLoss`,
  `QuestionEvaluationTrace`, `ClarificationPlan`, `PlannerResult`, `PlannerError`, and
  `CounterfactualPlanner`; `project_question_answers(question)` is the only public
  answer-projection helper.

- [ ] **Step 1: Write failing contract tests**

Add tests that construct real `ClarificationSpec` objects from the P1 registry and assert:

```python
def test_choice_projection_has_one_substantive_state_per_registered_value() -> None:
    question = build_p1_clarification_registry().get("confirm_dependence")
    projections = project_question_answers(question)

    assert tuple(item.projection_id for item in projections.substantive) == (
        "choice_independent:independent",
        "choice_paired:paired",
    )
    assert tuple(item.fact.value for item in projections.substantive) == (
        "independent",
        "paired",
    )
    assert projections.not_sure.fact.state is FactState.UNKNOWN
    assert projections.not_sure.fact.reason_code == (
        "user_not_sure:confirm_dependence"
    )


def test_terminal_loss_never_trades_one_e4_for_lower_risk_or_burden() -> None:
    one_e4 = TerminalLoss((0, 1, 0, 0, 0), 0, 0, 0, 0, 0)
    many_e3 = TerminalLoss(
        (0, 0, 999, 999, 999), 999, 999, 3, 999, 999
    )

    assert many_e3 < one_e4


def test_decision_snapshot_rejects_unsorted_or_duplicate_contract_values() -> None:
    with pytest.raises(PlannerError, match="possible_local_keys must be sorted"):
        _snapshot(possible_local_keys=("method.b", "method.a"))
```

Add an architecture test that includes the new module in the existing no-I/O/no-network
AST scan and asserts the public planner contracts have no `run`, `save`, `execute`,
`open`, or `persist` method.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest `
  tests/test_research_os_counterfactual_planner.py `
  tests/test_research_os_architecture.py -q -p no:cacheprovider
```

Expected: collection fails because `modori.research_os.counterfactual_planner` does not
exist.

- [ ] **Step 3: Implement immutable contracts and projections**

Create the module with the exact public boundary:

```python
PLANNER_VERSION = "research-os-counterfactual-minimax-v1"
DEFAULT_MAX_STATE_EVALUATIONS = 250_000


class PlannerError(ValueError):
    """Raised when planner inputs or invariants violate the closed contract."""


@dataclass(frozen=True, order=True)
class BlockingFact:
    fact_address: str
    question_id: str
    severity_rank: int


@dataclass(frozen=True)
class DecisionSnapshot:
    action: str
    stable_local_keys: tuple[str, ...]
    possible_local_keys: tuple[str, ...]
    ready_route_ids: tuple[str, ...]
    possible_route_ids: tuple[str, ...]
    estimand_template_ids: tuple[str, ...]
    role_fact_digests: tuple[tuple[str, str], ...]
    design_ids: tuple[str, ...]
    claim_permission_sets: tuple[tuple[str, ...], ...]
    blockers: tuple[BlockingFact, ...]
    route_classes: tuple[str, ...]
    data_policy_marks: tuple[str, ...]

    @property
    def risk_vector(self) -> tuple[int, int, int, int, int]:
        counts = [0, 0, 0, 0, 0]
        for blocker in self.blockers:
            counts[5 - blocker.severity_rank] += 1
        return tuple(counts)  # type: ignore[return-value]

    @property
    def frontier_size(self) -> int:
        return len(self.possible_local_keys) + len(self.possible_route_ids)

    @property
    def semantic_signature(self) -> tuple[object, ...]:
        return (
            self.action,
            self.stable_local_keys,
            self.possible_local_keys,
            self.ready_route_ids,
            self.possible_route_ids,
            self.estimand_template_ids,
            self.role_fact_digests,
            self.design_ids,
            self.claim_permission_sets,
            tuple(
                (item.fact_address, item.question_id, item.severity_rank)
                for item in self.blockers
            ),
            self.risk_vector,
            self.route_classes,
            self.data_policy_marks,
        )

    def digest(self) -> str:
        return canonical_digest({"semantic_signature": self.semantic_signature})


@dataclass(frozen=True, order=True)
class TerminalLoss:
    risk_vector: tuple[int, int, int, int, int]
    frontier_size: int
    blocking_fact_count: int
    questions_asked: int
    dependency_deficit: int
    answer_kind_cost: int
```

Implement strict sorted/unique validation in every public dataclass. Implement internal
`AnswerProjection` and `ProjectedAnswers`, plus public
`project_question_answers(question)`. Choice branches expand once per registered value;
empty/non-empty/answered branches use structural values appropriate to their answer kind;
the single refusal branch creates `Fact.unknown` with the exact reason code. All simulated
current facts use provenance beginning `planner-simulation:`.

Add `to_mapping()` methods for every trace object so the resolver decision can bind the
planner evidence without exposing execution authority.

- [ ] **Step 4: Run GREEN and focused Ruff**

Run the Step 2 pytest command, then:

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m ruff check `
  src/modori/research_os/counterfactual_planner.py `
  src/modori/research_os/__init__.py `
  tests/test_research_os_counterfactual_planner.py `
  tests/test_research_os_architecture.py
```

Expected: all selected tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 5: Commit Task 1**

```powershell
git add -- src/modori/research_os/counterfactual_planner.py `
  src/modori/research_os/__init__.py `
  tests/test_research_os_counterfactual_planner.py `
  tests/test_research_os_architecture.py
git commit -m "feat: add counterfactual planner contracts"
```

---

### Task 2: Implement exact bounded minimax search

**Files:**
- Modify: `src/modori/research_os/counterfactual_planner.py`
- Modify: `tests/test_research_os_counterfactual_planner.py`

**Interfaces:**
- Consumes: `SnapshotProvider = Callable[[Mapping[str, Fact[Any]]],
  DecisionSnapshot]` and the contracts from Task 1.
- Produces: `CounterfactualPlanner.plan(facts, question_budget_remaining) ->
  PlannerResult`.

- [ ] **Step 1: Write failing one-step and lookahead tests**

Use a test-only snapshot provider with two questions. The `selector` question splits two
possible capabilities immediately; the `common` question affects more rules but leaves a
larger worst frontier. Assert the planner selects `confirm_selector` while a frozen local
implementation of the legacy severity/impact policy selects `confirm_common`.

Add a depth-two counterexample where the best immediate frontier split forces a worse
second-round terminal loss than another root. Assert:

```python
def test_bounded_search_beats_one_step_greedy_on_locked_counterexample() -> None:
    planner = CounterfactualPlanner(
        registry=_lookahead_registry(),
        snapshot_provider=_lookahead_snapshot,
        max_state_evaluations=10_000,
    )

    result = planner.plan(_lookahead_facts(), question_budget_remaining=2)

    assert result.plan is not None
    assert result.plan.selected_question_id == "confirm_balanced_root"
    assert result.plan.selected_worst_loss < _one_step_greedy_terminal_loss()
```

Also add tests for:

- budget zero returning `clarification_budget_exhausted`;
- fixed state cap returning `planner_search_limit_exceeded`;
- refusal branch never opening `recommend_local` or `route_external`;
- refusal questions being excluded by exact reason code;
- branch and registry order invariance;
- memo hits on equivalent states; and
- exactly one selected candidate in the audit trace.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest `
  tests/test_research_os_counterfactual_planner.py -q -p no:cacheprovider
```

Expected: tests fail because `CounterfactualPlanner.plan` does not yet search policies.

- [ ] **Step 3: Implement the recursive search**

Implement a fresh per-call search session containing:

```python
@dataclass(frozen=True)
class _SearchResult:
    loss: TerminalLoss
    selected_question_id: str | None


def _search(
    self,
    facts: Mapping[str, Fact[Any]],
    remaining_budget: int,
) -> _SearchResult:
    snapshot = self._snapshot(facts)
    if snapshot.action != "clarify" or remaining_budget == 0:
        return _SearchResult(self._terminal_loss(snapshot), None)

    evaluations = tuple(
        evaluation
        for question_id in self._candidate_question_ids(snapshot, facts)
        if (
            evaluation := self._evaluate_candidate(
                facts,
                snapshot,
                question_id,
                remaining_budget,
            )
        )
        is not None
    )
    if not evaluations:
        return _SearchResult(self._terminal_loss(snapshot), None)
    selected = min(evaluations, key=lambda item: (item.worst_loss, item.question_id))
    return _SearchResult(selected.worst_loss, selected.question_id)
```

The implementation must:

- create a canonical relevant-fact digest from sorted `Fact.to_mapping()` values;
- memoize `_SearchResult` by `(remaining_budget, fact_digest)`;
- increment the state-evaluation counter only on snapshot cache misses;
- raise an internal typed limit signal as soon as the fixed count would be exceeded;
- add the current question cost to every child loss before choosing the worst branch;
- choose the lexicographic maximum child, then the lexicographic minimum question;
- collapse duplicate projected fact-state digests;
- compute dependency deficit from dependencies not in `OBSERVED` or
  `USER_CONFIRMED` state;
- use the frozen answer-kind cost mapping `yes_no=1`, `single_choice=2`,
  `level_choice=2`, `variable_single=3`, `variable_multi=4`,
  `ordered_variables=5`, `bounded_text=6`, `conflict_resolution=7`; and
- evaluate `not_sure` for safety and trace only, never in the minimax maximum.

`PlannerResult` must contain either one `ClarificationPlan` or one closed abstention
reason. Its plan records every legal root candidate in question-ID order, the selected
flag, branch snapshot digests, refusal snapshot digest, worst terminal loss, guaranteed
E3+ blockers removed, counters, and planner version.

- [ ] **Step 4: Run GREEN, permutation tests, and Ruff**

Run the Step 2 command three times, once with
`PYTHONHASHSEED=1`, once with `PYTHONHASHSEED=7`, and once with
`PYTHONHASHSEED=12345`. Run focused Ruff on the new module and test.

Expected: all runs select identical question IDs and trace mappings; Ruff passes.

- [ ] **Step 5: Commit Task 2**

```powershell
git add -- src/modori/research_os/counterfactual_planner.py `
  tests/test_research_os_counterfactual_planner.py
git commit -m "feat: add bounded minimax clarification search"
```

---

### Task 3: Make C1 produce decision snapshots and use one-question plans

**Files:**
- Modify: `src/modori/research_os/resolver.py`
- Modify: `tests/test_research_os_resolver.py`
- Modify: `src/modori/research_os/service.py`
- Modify: `tests/test_research_os_service.py`

**Interfaces:**
- Consumes: `ClarificationRegistry`, `DecisionSnapshot`, `BlockingFact`, and
  `CounterfactualPlanner`.
- Produces: `C1Resolver(method_space, clarification_registry)` and
  `ResolutionDecision.clarification_plan`.

- [ ] **Step 1: Write failing resolver integration tests**

Update the resolver test helper to pass an exact registry filtered from the P1 registry:

```python
def _registry_for(space: MethodSpace) -> ClarificationRegistry:
    required = tuple(
        sorted(
            {
                rule.clarification_id
                for rule in space.rules
                if rule.clarification_id is not None
            }
        )
    )
    source = build_p1_clarification_registry()
    return ClarificationRegistry(
        questions=tuple(
            question
            for question in source.questions
            if question.question_id in required
        ),
        required_question_ids=required,
    )
```

Add failing tests asserting:

```python
def test_multiple_unknowns_return_exactly_one_counterfactually_selected_question() -> None:
    context = _context(
        goal=Fact.unknown(reason_code="not_answered"),
        dependence=Fact.unknown(reason_code="not_answered"),
        weight=Fact.unknown(reason_code="not_answered"),
    )

    decision = _resolver(_space()).resolve(context)

    assert decision.action is PrimaryAction.CLARIFY
    assert len(decision.clarification_ids) == 1
    assert decision.clarification_plan is not None
    assert decision.clarification_plan.selected_question_id == (
        decision.clarification_ids[0]
    )


def test_duplicate_capability_rules_do_not_multiply_unique_fact_risk() -> None:
    decision = _resolver(_duplicated_rule_space()).resolve(_all_unknown_context())

    assert decision.clarification_plan is not None
    assert decision.clarification_plan.initial_risk_vector[1] == 1
```

The public non-authority plan trace therefore carries `initial_risk_vector`; do not expose
a test-only resolver snapshot method in production.

Add route, stable-local, malformed predicate/branch, and state-cap tests proving typed
abstention and no candidate leakage.

- [ ] **Step 2: Run the resolver/service tests and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest `
  tests/test_research_os_resolver.py `
  tests/test_research_os_service.py -q -p no:cacheprovider
```

Expected: failures show the resolver still accepts no registry, returns several questions,
and has no planner trace.

- [ ] **Step 3: Refactor resolver evaluation without changing hard-rule semantics**

Change construction to:

```python
class C1Resolver:
    def __init__(
        self,
        method_space: MethodSpace,
        clarification_registry: ClarificationRegistry,
        *,
        planner_state_cap: int = DEFAULT_MAX_STATE_EVALUATIONS,
    ) -> None:
        self._method_space = method_space
        self._clarification_registry = clarification_registry
        self._planner_state_cap = planner_state_cap
        self._rules = {rule.rule_id: rule for rule in method_space.rules}
        self._validate_registry_contract()
```

Extract the existing evaluation into a pure `_snapshot(context, facts)` path. Aggregate
unresolved actionable rules by fact address, reject conflicting question IDs for one
address, and retain the maximum severity rank. Construct possible local/route identities
only from non-excluded capabilities and current surface/route evidence.

Action precedence inside a snapshot remains:

1. stable surface-authorized local recommendation;
2. clarification when unresolved actionable blockers remain;
3. current roundtrip-verified route;
4. definite abstention.

The outer `resolve` keeps integrity abstention first. When the snapshot action is
`clarify`, call the planner and return exactly its selected question/address. If the
planner returns a typed abstention reason, return `PrimaryAction.ABSTAIN` with the same
rule trace and no question/capability/route payload.

Add `clarification_plan: ClarificationPlan | None = None` to `ResolutionDecision`, require
it exactly for clarify decisions, and include its mapping in `semantic_signature`.

- [ ] **Step 4: Inject the exact registry from the service**

Change only the constructor line:

```python
self._resolver = C1Resolver(
    self._method_space,
    self._clarification_registry,
)
```

Add closed recovery mappings:

```python
"clarification_answer_unavailable": "complete_structured_intake_or_revise_scope",
"planner_search_limit_exceeded": "complete_structured_intake_or_reduce_method_space",
"integrity:no_decision_relevant_clarification": "repair_clarification_registry",
```

- [ ] **Step 5: Run GREEN and all focused Research OS tests**

Run the Step 2 command, then:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest `
  tests/test_research_os_architecture.py `
  tests/test_research_os_clarifications.py `
  tests/test_research_os_contracts.py `
  tests/test_research_os_decision_evidence.py `
  tests/test_research_os_method_space.py `
  tests/test_research_os_p1_catalog.py `
  tests/test_research_os_passport.py `
  tests/test_research_os_planning.py `
  tests/test_research_os_resolver.py `
  tests/test_research_os_service.py `
  tests/test_research_os_transitions.py `
  tests/test_research_os_counterfactual_planner.py `
  -q -p no:cacheprovider
```

Expected: all Research OS tests pass.

- [ ] **Step 6: Commit Task 3**

```powershell
git add -- src/modori/research_os/resolver.py `
  src/modori/research_os/service.py `
  tests/test_research_os_resolver.py `
  tests/test_research_os_service.py
git commit -m "feat: integrate minimax clarification planning"
```

---

### Task 4: Close refusal loops and evidence-transition edge cases

**Files:**
- Modify: `tests/test_research_os_transitions.py`
- Modify: `tests/test_research_os_planning.py`
- Modify: `src/modori/research_os/counterfactual_planner.py`
- Modify: `src/modori/research_os/resolver.py`

**Interfaces:**
- Consumes: existing immutable `ClarificationTransitionService` and actual
  `user_not_sure:<question_id>` reason codes.
- Produces: finite, no-repeat multi-round behavior without changing transition authority.

- [ ] **Step 1: Write a failing full-round refusal regression**

Use the existing request/passport/answer helpers to execute a real `NOT_SURE` answer,
commit the resulting ready revision, and re-resolve:

```python
def test_not_sure_answer_never_repeats_the_same_question() -> None:
    service = ResearchOsService()
    request = _request_with_two_independent_blockers()
    first = service.plan(request, _passport_envelope())
    assert first.clarify is not None
    refused_id = first.clarify.question_ids[0]

    revised = _commit_not_sure(request, first, refused_id)
    second = service.resolve(revised)

    assert refused_id not in second.clarification_ids
    assert second.action in {PrimaryAction.CLARIFY, PrimaryAction.ABSTAIN}
```

Add a one-blocker case asserting typed `clarification_answer_unavailable` abstention, and a
three-round path asserting the budget decreases `3 -> 2 -> 1 -> 0` with no repeated state
or question.

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest `
  tests/test_research_os_transitions.py `
  tests/test_research_os_planning.py -q -p no:cacheprovider
```

Expected: at least the refusal regression fails by selecting the same question or by
returning an untyped generic abstention.

- [ ] **Step 3: Implement refusal exclusion at candidate selection**

Treat a candidate as refused only when all are exact:

```python
fact.state is FactState.UNKNOWN
and fact.reason_code == f"user_not_sure:{question.question_id}"
and question.fact_address == blocker.fact_address
```

Do not exclude ordinary unknown, stale, or conflict facts. When every current candidate
is refused, return `PlannerResult` with `clarification_answer_unavailable`. When a blocker
has no active compatible registered question for another reason, return
`integrity:no_decision_relevant_clarification`.

- [ ] **Step 4: Run GREEN, transition suite, and Ruff**

Run the Step 2 command, the full focused Research OS command from Task 3, and focused
Ruff. Expected: all pass with no warnings.

- [ ] **Step 5: Commit Task 4**

```powershell
git add -- src/modori/research_os/counterfactual_planner.py `
  src/modori/research_os/resolver.py `
  tests/test_research_os_transitions.py `
  tests/test_research_os_planning.py
git commit -m "fix: prevent repeated clarification refusals"
```

---

### Task 5: Build an independent oracle and locked policy comparison

**Files:**
- Create: `scripts/benchmark_counterfactual_clarification.py`
- Create: `tests/test_counterfactual_clarification_benchmark.py`
- Modify: `tests/test_research_os_counterfactual_planner.py`

**Interfaces:**
- Consumes: production planner only through its public contracts.
- Produces: deterministic JSON containing separate results for batch form, fixed tree,
  legacy severity-impact, one-step greedy, bounded minimax, and independent oracle.

- [ ] **Step 1: Write failing oracle-agreement tests**

Implement a test-only exhaustive enumerator that does not call the production planner's
private recursion. It may call the same pure snapshot provider because scientific rule
evaluation is not the policy under test. Freeze exactly three binary questions. Enumerate
each fact as `unknown`, first choice, or second choice (3^3 = 27 starting states) and each
budget from zero through three, yielding exactly 108 state-budget cases. Branch, rule,
question, and fact-order permutations are metamorphic repetitions of these 108 cases, not
extra policy cases.

Assert:

```python
@pytest.mark.parametrize("budget", (0, 1, 2, 3))
def test_production_policy_matches_independent_oracle_for_complete_small_matrix(
    budget: int,
) -> None:
    for facts in _all_small_fact_states():
        expected = _oracle_policy(facts, budget)
        actual = _production_policy(facts, budget)
        assert actual.selected_question_id == expected.selected_question_id
        assert actual.worst_loss == expected.worst_loss
```

Add mutation checks that deliberately replace minimax `max` with `min`, reverse E4/E3,
or count duplicated rules; each mutant must fail at least one locked case.

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest `
  tests/test_counterfactual_clarification_benchmark.py `
  tests/test_research_os_counterfactual_planner.py -q -p no:cacheprovider
```

Expected: collection or assertion fails because the independent oracle and benchmark do
not exist.

- [ ] **Step 3: Implement the deterministic comparison script**

The script accepts only:

```text
--iterations <positive integer, default 50>
--output <optional path>
```

It emits canonical UTF-8 JSON with:

```json
{
  "schema_version": 1,
  "evidence_class": "planner_fidelity_internal",
  "planner_version": "research-os-counterfactual-minimax-v1",
  "method_space_digest": "<sha256>",
  "clarification_registry_digest": "<sha256>",
  "case_count": 108,
  "policies": {},
  "oracle_disagreements": [],
  "e4_e5_failures": [],
  "performance": {}
}
```

Assert the generated count is exactly 108 before emitting output. Each policy reports
worst risk vector, worst/median questions, unnecessary questions, repeated-question
attempts, strictly suboptimal roots, and elapsed-time samples. The performance section
also records `tracemalloc` peak bytes. Output ordering and numeric rounding are fixed. The
script never calls a network, reads a dataset, or labels any result human gold.

- [ ] **Step 4: Run GREEN and record fresh output outside tracked fixtures**

Run the Step 2 tests, then:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' `
  scripts/benchmark_counterfactual_clarification.py `
  --iterations 100 `
  --output .tmp/counterfactual-clarification-evidence.json
```

Expected: zero oracle disagreements and zero E4/E5 failures. Do not relax the condition if
the output differs.

- [ ] **Step 5: Commit Task 5**

```powershell
git add -- scripts/benchmark_counterfactual_clarification.py `
  tests/test_counterfactual_clarification_benchmark.py `
  tests/test_research_os_counterfactual_planner.py
git commit -m "test: add clarification policy oracle"
```

---

### Task 6: Reconcile evidence, performance, and repository gates

**Files:**
- Create: `docs/qa/counterfactual-clarification-planner-evidence.md`
- Modify: `docs/superpowers/specs/2026-07-12-research-os-method-space-c1-design.md`
- Modify: `docs/superpowers/specs/2026-07-15-risk-bounded-counterfactual-clarification-planner-design.md`
- Modify only if a failing test requires it: files from Tasks 1--5

**Interfaces:**
- Consumes: fresh benchmark JSON, test output, Ruff output, git diff, and the frozen stop
  criteria.
- Produces: an evidence ledger that clearly separates formal planner fidelity from
  recommendation validity and product claims.

- [ ] **Step 1: Run the complete focused verification**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest `
  tests/test_research_os_architecture.py `
  tests/test_research_os_clarifications.py `
  tests/test_research_os_contracts.py `
  tests/test_research_os_counterfactual_planner.py `
  tests/test_research_os_decision_evidence.py `
  tests/test_research_os_method_space.py `
  tests/test_research_os_p1_catalog.py `
  tests/test_research_os_passport.py `
  tests/test_research_os_planning.py `
  tests/test_research_os_resolver.py `
  tests/test_research_os_service.py `
  tests/test_research_os_transitions.py `
  tests/test_counterfactual_clarification_benchmark.py `
  -q -p no:cacheprovider
```

Expected: zero failures and zero warnings.

- [ ] **Step 2: Apply the predeclared performance and simplification gate**

Read the fresh JSON. If bounded minimax has no strict loss/question advantage over
one-step greedy on any nontrivial locked case, stop and remove bounded recursion through a
new TDD cycle before proceeding. If any P1 case hits the state cap, profile exactly once;
make one cause-specific optimization with a failing regression, or stop bounded lookahead.

If the selected architecture survives, require development-machine worst elapsed time
below 5 seconds and peak process memory below 256 MiB. The user's 30-second office-PC
tolerance is not used to conceal a slower development result.

- [ ] **Step 3: Write the QA evidence document**

Record exact commands, commit, environment, case count, policy metrics, oracle agreement,
E4/E5 result, state-cap result, elapsed-time distribution, peak memory, and the explicit
nonclaims. Link the 2026-07-15 design. State the AnalysisPassport question-revision
binding gap as unresolved and block product integration on it.

Update Section 9.3 of the 2026-07-12 design with a short normative pointer to the
2026-07-15 refinement; do not rewrite history or replace the original text.

- [ ] **Step 4: Run full static and repository verification freshly**

Run:

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
$env:PATH='C:\Users\V\Desktop\TongTong\.tools\r-env\Library\bin;C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts;C:\Users\V\Desktop\TongTong\.tools\r-env\lib\R\bin;C:\Users\V\Desktop\TongTong\.tools\r-env\lib\R\bin\x64;' + $env:PATH
$env:PYTHONPATH=(Resolve-Path 'src').Path
$env:MPLCONFIGDIR=(Resolve-Path 'matplotlib-cache').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest `
  -q -p no:cacheprovider
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m ruff check .
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m compileall `
  -q src tests scripts
git diff --check
git status --short
```

Expected: the full pytest count is at least the 1942-test baseline plus the newly added
tests, with only understood skips; Ruff, compileall, and diff check exit zero; status lists
only this plan's intended files before the final commit.

- [ ] **Step 5: Commit Task 6**

```powershell
git add -- docs/qa/counterfactual-clarification-planner-evidence.md `
  docs/superpowers/specs/2026-07-12-research-os-method-space-c1-design.md `
  docs/superpowers/specs/2026-07-15-risk-bounded-counterfactual-clarification-planner-design.md
git commit -m "docs: record clarification planner evidence"
```

- [ ] **Step 6: Final branch audit**

Run:

```powershell
git status --short --branch
git log --oneline --decorate -8
git diff cc1e94bce5d147717447e195179bb68584a2574e -- `
  src/modori/research_os `
  tests/test_research_os_counterfactual_planner.py `
  tests/test_counterfactual_clarification_benchmark.py `
  scripts/benchmark_counterfactual_clarification.py `
  docs/superpowers/specs/2026-07-15-risk-bounded-counterfactual-clarification-planner-design.md `
  docs/superpowers/plans/2026-07-15-risk-bounded-counterfactual-clarification-planner.md `
  docs/qa/counterfactual-clarification-planner-evidence.md
```

Confirm no other worktree, branch, benchmark fixture, package, VM payload, UI, calculation
module, or persisted passport schema was modified.
