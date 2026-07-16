# Authority-Free Question Rationale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. The current root session is the exclusive writer; the user prohibits subagents.

**Goal:** Explain why an outstanding AnalysisPassport V2 clarification question ranked ahead of its recorded alternatives without rerunning the resolver or planner, inventing prose, or granting any execution authority.

**Architecture:** `modori.research_memory.question_rationale` verifies one exact outstanding local passport, its registry preimage, and its embedded minimax trace, then emits a strict in-memory projection. `modori.ui.question_rationale_presenter` converts only that projection into closed Korean/English guided or standard read models. The existing heuristic recommendation UI, QML, ledger wire format, calculation engine, and static `ExplanationService` remain unchanged.

**Tech Stack:** Python 3.12 standard library (`dataclasses`, `enum`, `ast`, `time`, `tracemalloc`), existing Research OS and Decision Ledger contracts, pytest, ruff. No new dependency.

## Global Constraints

- Exclusive worktree: `C:\Users\V\.codex\worktrees\b39f\TongTong`.
- Exclusive branch: `codex/research-os-contract-design`.
- Do not merge, push, switch branches, modify another worktree, or use subagents.
- Approved design: `docs/superpowers/specs/2026-07-16-authority-free-question-rationale-design.md` through commit `f4a32d0`.
- No QML, controller, legacy `RecommendationService`, static `ExplanationService`, calculation engine, SQLite schema, evidence-bundle schema, export, package, or VM-payload changes.
- No model, retrieval, filesystem, network, subprocess, clock, randomness, resolver call, planner call, transition, or persistence in the production projector/presenter.
- Inputs are exact typed `PassportHistory` and `ClarificationRegistry` values; a bare passport, JSON mapping, or imported assertion is not accepted.
- Only an outstanding local V2 clarify record for the exact `(project_id, request_binding_digest, clarification_registry_digest)` key may produce `available`.
- `comparisons` is rank ordered by `(worst_loss, question_id)`; the first row is the verified winner and the second is the runner-up.
- `decisive_dimension` explains only winner versus runner-up. `guaranteed_e3_plus_blockers_removed` is context, never a selection cause.
- Guided copy contains no `E1`-`E5`, `severity`, `심각도`, or numeric risk rank. Standard evidence may show exact codes only with closed everyday labels.
- Unavailable and failure copy is exact, closed, bilingual, and never derived from exception text.
- Projection V1 is in-memory only. Do not add `to_mapping`, `from_mapping`, serialization, ledger persistence, evidence-bundle inclusion, or export.
- Every production change follows RED -> verify RED -> GREEN -> verify GREEN -> refactor.
- Resource gate: at least 1,000 post-warmup invocations, p95 projection plus presentation at most 10 ms, peak traced allocation at most 512 KiB, deterministic output.
- Passing proves planner-explanation fidelity only, not recommendation validity, statistical accuracy, expert equivalence, or SPSS superiority.

---

### Task 1: Make a false selected trace unconstructable

**Files:**
- Modify: `tests/test_research_os_counterfactual_planner.py`
- Modify: `src/modori/research_os/counterfactual_planner.py`

**Interfaces:**
- Consumes: `QuestionEvaluationTrace.rank_key` and the existing strict `ClarificationPlan.from_mapping` decoder.
- Produces: a constructor invariant requiring the marked trace to be `min(evaluations, key=rank_key)`.
- Preserves: every valid mapping and digest; no wire field changes.

- [ ] **Step 1: Add the forged-selection decoder test**

```python
def test_clarification_plan_rejects_nonminimal_selected_trace() -> None:
    payload = locked_p1_plan().to_mapping()
    selected = next(item for item in payload["evaluations"] if item["selected"])
    loser = next(item for item in payload["evaluations"] if not item["selected"])
    selected["selected"] = False
    loser["selected"] = True
    payload["selected_question_id"] = loser["question_id"]
    payload["selected_fact_address"] = loser["fact_address"]
    payload["selected_question_version"] = loser["question_version"]
    payload["selected_question_digest"] = loser["question_digest"]

    with pytest.raises(PlannerError, match="minimum rank key"):
        ClarificationPlan.from_mapping(payload)
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_research_os_counterfactual_planner.py::test_clarification_plan_rejects_nonminimal_selected_trace -q -p no:cacheprovider`

Expected: FAIL because the current constructor accepts a self-consistent but nonminimal selected trace.

- [ ] **Step 3: Add the no-wire-change invariant**

Immediately after the existing exactly-one-selected check in `ClarificationPlan.__post_init__` add:

```python
        minimum = min(self.evaluations, key=lambda item: item.rank_key)
        if selected[0].question_id != minimum.question_id:
            raise PlannerError(
                "selected evaluation must be the minimum rank key"
            )
```

- [ ] **Step 4: Verify GREEN and unchanged valid digest behavior**

Run: `python -m pytest tests/test_research_os_counterfactual_planner.py -q -p no:cacheprovider`

Expected: PASS, including the existing strict round-trip and digest equality test.

- [ ] **Step 5: Commit**

```text
git add tests/test_research_os_counterfactual_planner.py src/modori/research_os/counterfactual_planner.py
git commit -m "fix: bind clarification selection to minimum rank"
```

---

### Task 2: Add strict in-memory rationale contracts and shared fixtures

**Files:**
- Create: `src/modori/research_memory/question_rationale.py`
- Create: `tests/question_rationale_fixtures.py`
- Create: `tests/test_question_rationale_projection.py`

**Interfaces:**
- Produces: `QuestionRationaleStatus`, `DecisiveDimension`, `QuestionCopy`, `QuestionLossComparison`, `QuestionRationaleProjection`, `QuestionRationaleResult`, and `QuestionRationaleError`.
- Does not yet expose a wire mapping or invoke a resolver, planner, transition, store, or presenter.

- [ ] **Step 1: Add failing constructor-contract tests**

Create exact tests proving:

```python
def test_projection_is_in_memory_only_and_rejects_false_caution() -> None:
    projection = available_projection_fixture()

    assert projection.schema_id == "modori.question_rationale_projection"
    assert projection.schema_version == 1
    assert not hasattr(projection, "to_mapping")
    assert not hasattr(type(projection), "from_mapping")
    with pytest.raises(QuestionRationaleError, match="caution_code"):
        replace(projection, caution_code="recommendation_is_valid")


def test_result_requires_projection_exactly_when_available() -> None:
    with pytest.raises(QuestionRationaleError, match="available"):
        QuestionRationaleResult(
            status=QuestionRationaleStatus.AVAILABLE,
            reason_code="rationale_available",
            projection=None,
        )
```

Also reject unsorted comparisons, duplicate question IDs, a selected row other than row zero, mismatched candidate count, a runner-up not equal to row one, a false `not_sure_available`, malformed digests, negative counts, and a reason code outside the status-specific closed set.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_question_rationale_projection.py -q -p no:cacheprovider`

Expected: collection fails because `modori.research_memory.question_rationale` does not exist.

- [ ] **Step 3: Implement the closed enums and dataclasses**

Use these exact public names and field shapes:

```python
class QuestionRationaleStatus(str, Enum):
    AVAILABLE = "available"
    NOT_APPLICABLE = "not_applicable"
    UNAVAILABLE = "unavailable"
    FAILURE = "failure"


class DecisiveDimension(str, Enum):
    ONLY_CANDIDATE = "only_candidate"
    REMAINING_SEVERITY_5 = "remaining_severity_5"
    REMAINING_SEVERITY_4 = "remaining_severity_4"
    REMAINING_SEVERITY_3 = "remaining_severity_3"
    REMAINING_SEVERITY_2 = "remaining_severity_2"
    REMAINING_SEVERITY_1 = "remaining_severity_1"
    REMAINING_FRONTIER_SIZE = "remaining_frontier_size"
    REMAINING_BLOCKING_FACT_COUNT = "remaining_blocking_fact_count"
    QUESTIONS_ASKED = "questions_asked"
    DEPENDENCY_DEFICIT = "dependency_deficit"
    ANSWER_KIND_COST = "answer_kind_cost"
    STABLE_QUESTION_ID = "stable_question_id"


@dataclass(frozen=True)
class QuestionCopy:
    question_id: str
    question_version: int
    question_digest: str
    fact_address: str
    template_ko: str
    template_en: str
    why_ko: str
    why_en: str
    not_sure_enabled: bool


@dataclass(frozen=True)
class QuestionLossComparison:
    question_id: str
    question_version: int
    question_digest: str
    fact_address: str
    worst_case_risk_vector: tuple[int, int, int, int, int]
    worst_case_frontier_size: int
    worst_case_blocking_fact_count: int
    worst_case_questions_asked: int
    worst_case_dependency_deficit: int
    worst_case_answer_kind_cost: int
    guaranteed_e3_plus_blockers_removed: int
    selected: bool

    @property
    def rank_key(self) -> tuple[object, ...]:
        return (
            *self.worst_case_risk_vector,
            self.worst_case_frontier_size,
            self.worst_case_blocking_fact_count,
            self.worst_case_questions_asked,
            self.worst_case_dependency_deficit,
            self.worst_case_answer_kind_cost,
            self.question_id,
        )
```

`QuestionRationaleProjection` contains every field in design section 8.3. Set the
non-init defaults exactly to `schema_id="modori.question_rationale_projection"`,
`schema_version=1`,
`selection_basis="counterfactual_minimax_lexicographic"`,
`not_sure_available=True`, and
`caution_code="question_priority_not_recommendation_validity"`.
`QuestionRationaleResult` validates this closed mapping:

```python
_REASONS_BY_STATUS = {
    QuestionRationaleStatus.AVAILABLE: frozenset({"rationale_available"}),
    QuestionRationaleStatus.NOT_APPLICABLE: frozenset(
        {"current_clarification_absent", "passport_not_outstanding"}
    ),
    QuestionRationaleStatus.UNAVAILABLE: frozenset(
        {"registry_preimage_unavailable"}
    ),
    QuestionRationaleStatus.FAILURE: frozenset(
        {
            "registry_contract_invalid",
            "registry_digest_mismatch",
            "selected_question_missing",
            "selected_question_mismatch",
            "evaluation_question_mismatch",
            "selected_rank_mismatch",
            "selected_identity_mismatch",
            "plan_digest_mismatch",
        }
    ),
}
```

All text, digest, integer, tuple, row-order, source-identity, winner, runner-up, decisive-value, and result-presence checks raise `QuestionRationaleError`. For `ONLY_CANDIDATE`, require both decisive values to be `None`; otherwise require both values and an actual runner-up.

- [ ] **Step 4: Add a deterministic typed fixture builder**

`tests/question_rationale_fixtures.py` must construct fresh valid `ClarificationSpec`,
`QuestionEvaluationTrace`, `ClarificationPlan`, `ClarifyPayloadV2`,
`AnalysisPassport`, `CommittedPassportRecord`, and `PassportHistory` objects. It must
never mutate a cached production fixture. Define this exact return container:

```python
@dataclass(frozen=True)
class RationaleCase:
    history: PassportHistory
    project_id: str
    request_binding_digest: str
    clarification_registry_digest: str
    registry: ClarificationRegistry
    passport: AnalysisPassport
    plan: ClarificationPlan
```

Implement `rationale_case(*, selected_loss: TerminalLoss,
runner_up_loss: TerminalLoss | None,
selected_question_id: str = "confirm_z_selected",
runner_up_question_id: str = "confirm_a_runner") -> RationaleCase`. The helper sorts
plan evaluations by question ID but marks the minimum rank-key trace selected; it
returns every field above and uses fresh branch/refusal digests on each construction.
Also implement `available_projection_fixture() -> QuestionRationaleProjection` by
building two valid rank-ordered comparison rows, matching selected/runner-up
`QuestionCopy` values, `candidate_count=2`, one decisive severity-4 difference with
values `0` and `1`, and valid fixed source digests. This is the constructor-test source;
it does not bypass the projector in projector tests.

- [ ] **Step 5: Verify GREEN**

Run: `python -m pytest tests/test_question_rationale_projection.py -q -p no:cacheprovider`

Expected: all constructor tests pass.

- [ ] **Step 6: Commit**

```text
git add src/modori/research_memory/question_rationale.py tests/question_rationale_fixtures.py tests/test_question_rationale_projection.py
git commit -m "feat: add question rationale contracts"
```

---

### Task 3: Project one verified outstanding question without a second search

**Files:**
- Modify: `src/modori/research_memory/question_rationale.py`
- Modify: `src/modori/research_memory/__init__.py`
- Modify: `tests/test_question_rationale_projection.py`

**Interfaces:**
- Consumes: `PassportHistory.outstanding_for`, `audit_passport_registry`, `ClarifyPayloadV2`, exact `ClarificationRegistry` questions, and embedded `QuestionEvaluationTrace` values.
- Produces: `project_current_question_rationale(history: PassportHistory, *,
  project_id: str, request_binding_digest: str,
  clarification_registry_digest: str,
  registry: ClarificationRegistry | None) -> QuestionRationaleResult`.

- [ ] **Step 1: Add failing available, pairwise, and lifecycle tests**

Parameterize the ten numeric two-candidate decisive dimensions. For each case choose
losses whose first difference is exactly `0` versus `1`, then assert the enum and both
values. For example:

```python
@pytest.mark.parametrize(
    ("selected_loss", "runner_loss", "expected"),
    (
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 0, 0, 0),
            TerminalLoss((0, 1, 0, 0, 0), 0, 0, 0, 0, 0),
            DecisiveDimension.REMAINING_SEVERITY_4,
        ),
        (
            TerminalLoss((0, 0, 0, 0, 0), 0, 0, 0, 0, 0),
            TerminalLoss((0, 0, 0, 0, 0), 1, 0, 0, 0, 0),
            DecisiveDimension.REMAINING_FRONTIER_SIZE,
        ),
    ),
)
def test_projection_reports_first_pairwise_rank_difference(
    selected_loss: TerminalLoss,
    runner_loss: TerminalLoss,
    expected: DecisiveDimension,
) -> None:
    case = rationale_case(
        selected_loss=selected_loss,
        runner_up_loss=runner_loss,
    )

    result = project_current_question_rationale(
        case.history,
        project_id=case.project_id,
        request_binding_digest=case.request_binding_digest,
        clarification_registry_digest=case.clarification_registry_digest,
        registry=case.registry,
    )

    assert result.projection is not None
    assert result.projection.decisive_dimension is expected
    assert result.projection.selected_decisive_value == 0
    assert result.projection.runner_up_decisive_value == 1
```

Add a separate stable-ID case with identical loss values and question IDs
`confirm_a_selected` and `confirm_z_runner`; require
`STABLE_QUESTION_ID`, `"confirm_a_selected"`, and `"confirm_z_runner"`. Add a
single-candidate case requiring `ONLY_CANDIDATE` and `None` for both decisive values.

Add exact assertions that comparisons are rank ordered, selected/runner copies match registry copy, source passport/plan/event identities match, guaranteed-E3 context does not become decisive, absent registry is unavailable, wrong registry is failure, consumed/retracted is not applicable, and an exact inactive key uses `passport_not_outstanding`.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_question_rationale_projection.py -q -p no:cacheprovider`

Expected: projector imports or calls fail because the function is absent.

- [ ] **Step 3: Implement exact eligibility and audit ordering**

The function must:

1. validate typed inputs and lowercase SHA-256 key digests;
2. call `history.outstanding_for` exactly once;
3. return `passport_not_outstanding` only when a record with the exact key exists but is consumed or retracted, otherwise `current_clarification_absent`;
4. map `PassportRegistryAuditStatus.UNAVAILABLE` to unavailable and audit failure codes to failure;
5. independently rank `plan.evaluations` by `trace.rank_key` and reject a marked nonwinner;
6. compare selected identity across trace, plan, and `ClarificationRef`;
7. recompute `plan.digest()` and compare it with `clarification_plan_digest`;
8. verify every selected and alternative question's active lifecycle, ID, version, digest, and fact address against the exact registry;
9. create comparisons in rank order; and
10. emit the available projection without calling any search or transition service.

Use an explicit closed component table for the pairwise comparison:

```python
def _rank_components(
    trace: QuestionEvaluationTrace,
) -> tuple[tuple[DecisiveDimension, int | str], ...]:
    loss = trace.worst_loss
    return (
        (DecisiveDimension.REMAINING_SEVERITY_5, loss.risk_vector[0]),
        (DecisiveDimension.REMAINING_SEVERITY_4, loss.risk_vector[1]),
        (DecisiveDimension.REMAINING_SEVERITY_3, loss.risk_vector[2]),
        (DecisiveDimension.REMAINING_SEVERITY_2, loss.risk_vector[3]),
        (DecisiveDimension.REMAINING_SEVERITY_1, loss.risk_vector[4]),
        (DecisiveDimension.REMAINING_FRONTIER_SIZE, loss.frontier_size),
        (
            DecisiveDimension.REMAINING_BLOCKING_FACT_COUNT,
            loss.blocking_fact_count,
        ),
        (DecisiveDimension.QUESTIONS_ASKED, loss.questions_asked),
        (DecisiveDimension.DEPENDENCY_DEFICIT, loss.dependency_deficit),
        (DecisiveDimension.ANSWER_KIND_COST, loss.answer_kind_cost),
        (DecisiveDimension.STABLE_QUESTION_ID, trace.question_id),
    )
```

For a single candidate return `ONLY_CANDIDATE, None, None`. For two or more, compare only rows zero and one and return the first unequal component.

- [ ] **Step 4: Export only the public typed API**

Add the seven types and `project_current_question_rationale` to `modori.research_memory.__init__` and `__all__`. Do not export private validation or comparison helpers.

- [ ] **Step 5: Verify GREEN**

Run: `python -m pytest tests/test_question_rationale_projection.py tests/test_research_memory_passport_state.py tests/test_research_os_passport_audit.py -q -p no:cacheprovider`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```text
git add src/modori/research_memory/question_rationale.py src/modori/research_memory/__init__.py tests/test_question_rationale_projection.py
git commit -m "feat: project verified question rationale"
```

---

### Task 4: Render closed guided and standard read models

**Files:**
- Create: `src/modori/ui/question_rationale_presenter.py`
- Create: `tests/ui/test_question_rationale_presenter.py`

**Interfaces:**
- Consumes: `QuestionRationaleResult` only.
- Produces: `QuestionRationalePresentationError`,
  `QuestionRationaleEvidenceRow`, `QuestionRationaleView`, and
  `QuestionRationalePresenter.present`.
- Does not modify QML or controller services.

- [ ] **Step 1: Add failing bilingual status and mode tests**

Use the exact entry point:

```python
view = QuestionRationalePresenter().present(
    result,
    language="ko",
    mode="guided",
)
```

Assert:

- `not_applicable` returns `None`;
- unavailable Korean and English `status_message` exactly match design section 10.3;
- failure Korean and English `status_message` exactly match design section 10.3;
- status-only views have empty question/reason/summary/uncertainty/guidance/caution/source fields and no evidence rows;
- the guided severity-4 summary contains `안전한 분석 선택을 가로막을 수 있는 중대한 불확실성` and contains no `E4`, `severity`, or `심각도`;
- stable-ID ties say fixed order, not risk advantage;
- standard evidence includes distinct E5/E4 rows, both decisive values, context-labeled guaranteed-E3 removal, budget, candidate count, and digest prefixes;
- every available view contains the exact validity caution; and
- unknown language or mode raises `QuestionRationalePresentationError`.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/ui/test_question_rationale_presenter.py -q -p no:cacheprovider`

Expected: collection fails because the presenter module does not exist.

- [ ] **Step 3: Implement immutable view contracts and exact presenter API**

```python
@dataclass(frozen=True)
class QuestionRationaleEvidenceRow:
    code: str
    label: str
    selected_value: str
    runner_up_value: str


@dataclass(frozen=True)
class QuestionRationaleView:
    status: QuestionRationaleStatus
    status_message: str
    title: str
    question_text: str
    base_reason: str
    selection_summary: str
    remaining_uncertainty: str
    not_sure_guidance: str
    caution: str
    evidence_rows: tuple[QuestionRationaleEvidenceRow, ...]
    source_identity_text: str


```

Implement `QuestionRationalePresenter.present(result: QuestionRationaleResult, *,
language: Literal["ko", "en"], mode: Literal["guided", "standard"])
-> QuestionRationaleView | None`. It first validates the exact enum result and the two
closed string inputs, returns `None` for `not_applicable`, returns a status-only view for
`unavailable`/`failure`, and renders projection fields only for `available`.

The presenter validates exact language/mode strings. It uses dictionaries of complete closed sentence frames, not exception strings or general prose generation. The severity mapping is exactly:

```python
_GUIDED_RISK_LABELS = {
    "ko": {
        DecisiveDimension.REMAINING_SEVERITY_5: "안전한 분석 선택을 가로막을 수 있는 중대한 불확실성",
        DecisiveDimension.REMAINING_SEVERITY_4: "안전한 분석 선택을 가로막을 수 있는 중대한 불확실성",
        DecisiveDimension.REMAINING_SEVERITY_3: "분석 선택이나 결과 해석을 크게 바꿀 수 있는 불확실성",
        DecisiveDimension.REMAINING_SEVERITY_2: "더 적합한 분석을 좁히는 데 필요한 확인 사항",
        DecisiveDimension.REMAINING_SEVERITY_1: "사용 흐름을 다듬기 위한 낮은 위험의 확인 사항",
    },
    "en": {
        DecisiveDimension.REMAINING_SEVERITY_5: "critical uncertainty that could block a safe analysis choice",
        DecisiveDimension.REMAINING_SEVERITY_4: "critical uncertainty that could block a safe analysis choice",
        DecisiveDimension.REMAINING_SEVERITY_3: "uncertainty that could materially change the analysis choice or interpretation",
        DecisiveDimension.REMAINING_SEVERITY_2: "information needed to narrow the analysis to a more suitable choice",
        DecisiveDimension.REMAINING_SEVERITY_1: "low-risk information that helps streamline the workflow",
    },
}
```

Freeze status and caution copy as exact constants:

```python
_UNAVAILABLE_MESSAGE = {
    "ko": "이 질문이 먼저 선택된 근거를 재현하는 데 필요한 기록을 현재 확인할 수 없습니다. 근거를 추정해서 표시하지 않습니다.",
    "en": "The record needed to reproduce why this question was selected first is currently unavailable. Modori does not infer or display a reason.",
}
_FAILURE_MESSAGE = {
    "ko": "질문 선택 기록과 검증 정보가 일치하지 않아 근거를 표시하지 않습니다. 이 상태만으로 프로젝트 원장 전체가 손상되었다고 판단하지 않습니다.",
    "en": "The question-selection record does not match its verification evidence, so no rationale is shown. This status alone does not mean the entire project ledger is corrupt.",
}
_CAUTION = {
    "ko": "이 설명은 질문 우선순위의 근거입니다. 최종 분석 추천이나 연구 결론의 타당성을 보증하지 않습니다.",
    "en": "This explains the question's priority. It does not guarantee the validity of the final analysis recommendation or research conclusion.",
}
```

The stable-ID Korean frame is exactly `기록된 위험과 응답 부담이 같은 후보들이어서,
결과를 항상 재현할 수 있는 고정 질문 순서로 이 질문이 먼저 선택되었습니다.`;
the English frame is `The recorded risk and response burden were tied, so this
question came first under the fixed question order used for reproducibility.` The
guaranteed-E3 evidence label must include `문맥 정보이며 반드시 결정 원인은 아님` /
`context; not necessarily the deciding metric`.

- [ ] **Step 4: Verify GREEN and wording scan**

Run: `python -m pytest tests/ui/test_question_rationale_presenter.py -q -p no:cacheprovider`

Expected: all tests pass and a regex scan of guided output finds none of `\bE[1-5]\b`, `severity`, or `심각도`.

- [ ] **Step 5: Commit**

```text
git add src/modori/ui/question_rationale_presenter.py tests/ui/test_question_rationale_presenter.py
git commit -m "feat: present closed question rationale copy"
```

---

### Task 5: Attack lifecycle, provenance, mutation, and authority boundaries

**Files:**
- Create: `tests/test_question_rationale_adversarial.py`
- Modify: `tests/test_question_rationale_projection.py`
- Modify: `tests/ui/test_question_rationale_presenter.py`
- Modify: `src/modori/research_memory/question_rationale.py`
- Modify: `src/modori/ui/question_rationale_presenter.py`

**Interfaces:**
- Verifies: no second search, no stale explanation, no alternative-revision blind spot, no false status downgrade, no imported/bare source, and no forbidden production import.

- [ ] **Step 1: Add poison tests for resolver and planner calls**

Build the valid history and registry before installing poison functions, then patch:

```python
def forbidden(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError("projection attempted a second search")

monkeypatch.setattr(CounterfactualPlanner, "plan", forbidden)
monkeypatch.setattr(C1Resolver, "resolve", forbidden)
result = project_current_question_rationale(
    case.history,
    project_id=case.project_id,
    request_binding_digest=case.request_binding_digest,
    clarification_registry_digest=case.clarification_registry_digest,
    registry=case.registry,
)
assert result.status is QuestionRationaleStatus.AVAILABLE
```

- [ ] **Step 2: Add AST authority scans**

Parse both production files with `ast.parse`. Fail if they import `pathlib`, `os`, `sqlite3`, `socket`, `urllib`, `http`, `subprocess`, `requests`, model/retrieval packages, ledger-store append classes, `CounterfactualPlanner`, `C1Resolver`, `ResearchOsService`, or clarification transition services. Permit passive `QuestionEvaluationTrace`, `ClarificationRegistry`, audit, passport, and history contract types.

- [ ] **Step 3: Add lifecycle and mutation matrix**

Cover these exact mutations one at a time:

| Mutation | Required outcome |
|---|---|
| consumed or retracted exact passport | `not_applicable/passport_not_outstanding` |
| stale request or registry key | `not_applicable/current_clarification_absent` |
| registry absent | `unavailable/registry_preimage_unavailable` |
| registry digest changed | `failure/registry_digest_mismatch` |
| selected registry revision changed normally | `failure/registry_digest_mismatch` |
| selected registry revision changed under digest-method poison | `failure/selected_question_mismatch` |
| alternative trace revision/digest/fact mismatch after a digest-method poison | `failure/evaluation_question_mismatch` |
| selected marker moved by test-only frozen-object mutation | `failure/selected_rank_mismatch` |
| plan selected identity changed | `failure/selected_identity_mismatch` |
| embedded plan changed without ref digest change | `failure/plan_digest_mismatch` |
| wrong caution or catalog key | constructor/presenter error |
| bare `AnalysisPassport`, mapping, or `ImportedAssertion` as `history` | typed error; never available |

The alternative-question test must make the registry's selected question remain exact and temporarily poison only `ClarificationRegistry.digest` to return the originally bound digest. This proves the projector checks every alternative instead of relying only on the selected-question audit.

- [ ] **Step 4: Add metamorphic projection tests**

Permute registry declaration order and confirm identical projection. Change `guaranteed_e3_plus_blockers_removed` while preserving every rank-key field and confirm the selected question and `decisive_dimension` do not change, while only the contextual projection field changes.

- [ ] **Step 5: Verify the attack gate**

Run: `python -m pytest tests/test_question_rationale_projection.py tests/test_question_rationale_adversarial.py tests/ui/test_question_rationale_presenter.py -q -p no:cacheprovider`

Expected: all attacks are rejected or change only the truthful bounded projection.

- [ ] **Step 6: Commit**

```text
git add tests/test_question_rationale_projection.py tests/test_question_rationale_adversarial.py tests/ui/test_question_rationale_presenter.py
git commit -m "test: attack question rationale boundaries"
```

---

### Task 6: Measure resource bounds and close evidence

**Files:**
- Create: `tests/test_question_rationale_performance.py`
- Create: `docs/qa/authority-free-question-rationale-evidence.md`

**Interfaces:**
- Measures the full pure projection plus standard presenter over the real 15-candidate locked P1 passport fixture.
- Records fidelity evidence only; it does not create recommendation-validity evidence.

- [ ] **Step 1: Add the fixed resource test**

Construct `events, artifacts, request, passport = history_with_passport_commit()`, then
`history = PassportHistory.inspect(events, artifacts)`, the P1 registry, and the three
exact key values outside the timed region. Warm up 50 times. Then run exactly 1,000
timed invocations with `time.perf_counter_ns`, compute p95 as
`sorted(samples)[949]`, and assert:

```python
assert p95_ns <= 10_000_000
assert peak_bytes <= 512 * 1024
assert len({repr((result, view)).encode("utf-8") for _ in range(20)}) == 1
```

Measure peak allocation in a separate `tracemalloc` block after warmup so fixture construction and planner execution are excluded. The `repr` bytes are test-only determinism evidence, not a product serialization contract.

- [ ] **Step 2: Run the focused resource gate and retain exact values**

Run: `python -m pytest tests/test_question_rationale_performance.py -q -s -p no:cacheprovider`

Expected: at least 1,000 samples; p95 at most 10 ms; peak at most 524,288 bytes. If it fails, profile only pure validation/copy construction, preserve every contract, and stop rather than relaxing a gate that remains failed after rational optimization.

- [ ] **Step 3: Write the QA evidence record**

Record date, branch, implementation commit, Python/OS/CPU, candidate count, warmup/sample count, median/p95/max, traced peak, focused tests, mutation outcomes, no-second-search proof, static scan, full-suite result, and exact non-claims. Explicitly state that the evidence is `planner_explanation_fidelity_internal`, not human gold or recommendation validity.

- [ ] **Step 4: Run focused static and compile gates**

```text
python -m pytest tests/test_research_os_counterfactual_planner.py tests/test_question_rationale_projection.py tests/test_question_rationale_adversarial.py tests/test_question_rationale_performance.py tests/ui/test_question_rationale_presenter.py -q -p no:cacheprovider
python -m ruff check src/modori/research_os/counterfactual_planner.py src/modori/research_memory/question_rationale.py src/modori/ui/question_rationale_presenter.py tests/test_research_os_counterfactual_planner.py tests/question_rationale_fixtures.py tests/test_question_rationale_projection.py tests/test_question_rationale_adversarial.py tests/test_question_rationale_performance.py tests/ui/test_question_rationale_presenter.py
python -m compileall -q src tests
git diff --check
```

Expected: all focused tests pass, Ruff says `All checks passed!`, compileall and diff check exit zero.

- [ ] **Step 5: Run the complete repository gate**

Run: `python -m pytest -q -p no:cacheprovider`

Expected: zero unexpected failures. Report the exact passed/skipped count and every skip category; do not inherit an older count.

- [ ] **Step 6: Reconcile and commit evidence**

Update the QA record only with fresh outputs from steps 2-5, then run `git diff --check` again.

```text
git add tests/test_question_rationale_performance.py docs/qa/authority-free-question-rationale-evidence.md
git commit -m "test: verify question rationale resource bounds"
```

---

## Final verification and stop decision

Before claiming completion:

1. run `git status --short`, `git branch --show-current`, and `git log -7 --oneline`;
2. confirm no changed path is QML, controller, recommendation service, calculation, SQLite schema, bundle wire, package, VM payload, or another worktree;
3. rerun the exact focused gate after the last evidence edit;
4. confirm every production output is typed and in-memory with no serializer;
5. confirm the forged selected plan dies at construction;
6. confirm stable-ID copy says fixed order and no risk advantage;
7. confirm unavailable/failure copy is exact in Korean and English;
8. confirm poison planner/resolver tests pass;
9. confirm the resource gate remains within its predeclared limits; and
10. classify the result as pass, conditional pass, or stop without weakening any criterion.

Stop and retain only canonical ledger evidence if truthful explanation requires a second search, exact alternative revisions cannot be verified, production code needs raw/free text or execution authority, or the fixed resource gate remains failed after focused optimization.
