# Research OS Passport and Clarification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. The current root session is the exclusive writer; subagents are prohibited by the user.

**Goal:** Convert C1 decisions into complete, immutable clarification metadata and a version-bound AnalysisPassport that Guided and Pro surfaces can consume without gaining execution, persistence, file, or network authority.

**Architecture:** A P1 clarification registry translates resolver question IDs into closed bilingual answer contracts. A separate passport module binds exact QuestionSpec, EstimandSpec, StudySpec, dataset, Method Space, ruleset, and resolver decision digests to one mutually exclusive action payload. `ResearchOsService.plan()` composes these pure structures while the existing `resolve()` API and all current product UI remain unchanged.

**Tech Stack:** Python 3.11 frozen dataclasses, closed enums, standard-library JSON/SHA-256, pytest, ruff. No dependency change.

## Global Constraints

- Exclusive worktree and branch remain `C:\Users\V\.codex\worktrees\b39f\TongTong` and `codex/research-os-contract-design`.
- Do not merge, push, switch branches, invoke subagents, or edit another worktree.
- Do not modify the existing recommendation UI, benchmark, calculation engine, packages, VM payloads, or model artifacts.
- The passport is a route record, never an execution ticket. It cannot contain a command, worker token, filesystem path, arbitrary URL, pipeline mutation, or implicit selection.
- Every action payload is mutually exclusive. `clarify` and `abstain` expose no capability identity; `route_external` exposes no local capability; `recommend_local` exposes no route.
- Every clarification has a closed fact address, bilingual reviewed template, answer kind, `not_sure` branch, trigger, and answer schema. Question text cannot name or imply a recommended method.
- The registry must cover every clarification ID referenced by the frozen P1 Method Space and contain no unused ID.
- `ResearchOsService.plan()` accepts canonical structures and a caller-supplied passport envelope only. It does not read, save, open, download, execute, or mutate anything.
- All new behavior follows RED → GREEN → REFACTOR and is committed in independently verified checkpoints.
- Starting verification state: full suite 1,629 passed, 5 skipped, 0 failed; focused Research OS suite 87 passed; ruff clean; worktree clean at `f872cb7`.

## Locked Scope

Included:

1. `ClarificationSpec`, closed answer kinds/triggers, answer choices, and strict registry validation.
2. Exact bilingual P1 question registry for every current hard-rule clarification ID.
3. `AnalysisPassport`, component revision references, four closed payload types, strict wire round-trip, and deterministic digest.
4. `ResearchOsService.plan(request, passport_envelope)` composition.
5. Architecture guards proving the passport has no execution/persistence authority and existing UI remains untouched.

Excluded:

1. Rendering Guided/Pro screens or applying user answers.
2. Project persistence, migration, history storage, and imported-project trust.
3. Local/external execution, export, package launch, browser opening, or route-card installation.
4. P1 expansion, P2 methods, teacher data, retrieval, classifiers, encoders, and training.
5. Public recommendation-validity claims.

---

### Task 1: Closed P1 clarification registry

**Files:**
- Create: `src/modori/research_os/clarification.py`
- Create: `src/modori/research_os/p1_clarifications.py`
- Modify: `src/modori/research_os/__init__.py`
- Test: `tests/test_research_os_clarifications.py`

**Interfaces:**
- Produces: `AnswerKind`, `ClarificationTrigger`, `AnswerChoice`, `ClarificationSpec`, `ClarificationRegistry`, `build_p1_clarification_registry()`.
- Consumes: clarification IDs and fact addresses from `build_p1_method_space()`.

- [ ] **Step 1: Write failing contract tests**

```python
def test_choice_question_requires_two_distinct_answers_and_not_sure() -> None:
    with pytest.raises(ClarificationError, match="at least two choices"):
        ClarificationSpec(
            question_id="confirm_dependence",
            version=1,
            fact_address="study.dependence_structure",
            answer_kind=AnswerKind.SINGLE_CHOICE,
            template_ko="자료는 서로 독립입니까?",
            template_en="Are observations independent?",
            why_ko="의존 구조가 분석 경로를 바꿉니다.",
            why_en="Dependence changes the analysis route.",
            choices=(_choice("independent"),),
            triggers=(ClarificationTrigger.METHOD_IDENTITY_CHANGE,),
            not_sure_enabled=True,
        )
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_research_os_clarifications.py -q -p no:cacheprovider`

Expected: import failure because the clarification modules do not exist.

- [ ] **Step 3: Implement strict immutable clarification contracts**

```python
class AnswerKind(str, Enum):
    YES_NO = "yes_no"
    SINGLE_CHOICE = "single_choice"
    VARIABLE_SINGLE = "variable_single"
    VARIABLE_MULTI = "variable_multi"
    ORDERED_VARIABLES = "ordered_variables"
    LEVEL_CHOICE = "level_choice"
    BOUNDED_TEXT = "bounded_text"
    CONFLICT_RESOLUTION = "conflict_resolution"


@dataclass(frozen=True)
class ClarificationSpec:
    question_id: str
    version: int
    fact_address: str
    answer_kind: AnswerKind
    template_ko: str
    template_en: str
    why_ko: str
    why_en: str
    choices: tuple[AnswerChoice, ...]
    triggers: tuple[ClarificationTrigger, ...]
    not_sure_enabled: bool
```

Choice kinds require at least two unique choices; variable and ordered-variable kinds prohibit hard-coded choices. All questions require `not_sure_enabled=True`, nonblank bilingual text, nonduplicate triggers, strict wire mapping, and no method/test/module ID field.

- [ ] **Step 4: Build and test exact P1 coverage**

```python
def test_p1_registry_exactly_covers_method_space_question_ids() -> None:
    required = {
        rule.clarification_id
        for rule in build_p1_method_space().rules
        if rule.clarification_id is not None
    }
    registry = build_p1_clarification_registry()
    assert set(registry.question_ids) == required
```

Questions cover research goal, causal intent, estimand template, claim basis, effect scale, association target, dependence, weight, cluster, outcome, focal predictor, group, repeated measure, contrast, and repeated-measure order. Templates describe facts and consequences without naming Pearson, Spearman, Welch, t, or another recommended method.

- [ ] **Step 5: Run tests and ruff**

Run: `python -m pytest tests/test_research_os_clarifications.py -q -p no:cacheprovider`

Expected: all tests pass.

Run: `python -m ruff check src/modori/research_os/clarification.py src/modori/research_os/p1_clarifications.py tests/test_research_os_clarifications.py`

Expected: zero errors.

- [ ] **Step 6: Commit Task 1**

Commit message: `feat: add p1 clarification registry`

---

### Task 2: Immutable AnalysisPassport

**Files:**
- Create: `src/modori/research_os/passport.py`
- Modify: `src/modori/research_os/__init__.py`
- Test: `tests/test_research_os_passport.py`

**Interfaces:**
- Produces: `ComponentRevisionRef`, `ClaimClass`, `RecommendLocalPayload`, `ClarifyPayload`, `RouteExternalPayload`, `AbstainPayload`, `AnalysisPassport`, and `PassportError`.
- Consumes: `SchemaEnvelope`, canonical digests, `PrimaryAction`.

- [ ] **Step 1: Write failing action-exclusivity tests**

```python
def test_passport_rejects_mixed_action_payloads() -> None:
    with pytest.raises(PassportError, match="exactly one action payload"):
        AnalysisPassport(
            envelope=_passport_envelope(),
            question_ref=_question_ref(),
            estimand_ref=_estimand_ref(),
            study_ref=_study_ref(),
            dataset_fingerprint="a" * 64,
            method_space_version="research-os-p1-v1",
            method_space_digest="b" * 64,
            ruleset_version="research-os-c1-p1-v1",
            resolver_decision_digest="c" * 64,
            recommend_local=_recommend_payload(),
            clarify=_clarify_payload(),
        )
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_research_os_passport.py -q -p no:cacheprovider`

Expected: import failure because `passport.py` does not exist.

- [ ] **Step 3: Implement strict payloads and component references**

```python
@dataclass(frozen=True)
class ComponentRevisionRef:
    schema_id: str
    object_id: str
    revision: int
    digest: str


@dataclass(frozen=True)
class RecommendLocalPayload:
    capability_keys: tuple[str, ...]
    local_analysis_kinds: tuple[str, ...]
    claim_permissions: tuple[ClaimClass, ...]
    experimental: bool
    auto_selected: bool = False
    requires_explicit_configure_confirm_run: bool = True
```

`auto_selected` must be false and the explicit gate must be true. `ClarifyPayload` contains only question IDs and blocking fact addresses. `RouteExternalPayload` contains only verified route IDs and privacy-boundary IDs. `AbstainPayload` contains closed reason codes and recovery requirement IDs.

- [ ] **Step 4: Add strict wire and authority tests**

```python
def test_passport_strict_roundtrip_preserves_digest() -> None:
    passport = _valid_recommend_passport()
    restored = AnalysisPassport.from_mapping(passport.to_mapping())
    assert restored == passport
    assert restored.digest() == passport.digest()


def test_passport_wire_has_no_execution_authority_key() -> None:
    forbidden = {"command", "worker_token", "path", "url", "execute", "pipeline_mutation"}
    assert _all_keys(_valid_recommend_passport().to_mapping()).isdisjoint(forbidden)
```

- [ ] **Step 5: Run tests and ruff**

Run: `python -m pytest tests/test_research_os_passport.py -q -p no:cacheprovider`

Expected: all tests pass.

Run: `python -m ruff check src/modori/research_os/passport.py tests/test_research_os_passport.py`

Expected: zero errors.

- [ ] **Step 6: Commit Task 2**

Commit message: `feat: add immutable analysis passport`

---

### Task 3: Service plan composition

**Files:**
- Modify: `src/modori/research_os/service.py`
- Modify: `src/modori/research_os/__init__.py`
- Test: `tests/test_research_os_planning.py`

**Interfaces:**
- Produces: `ResearchOsService.plan(request, passport_envelope) -> AnalysisPassport` and `ResearchOsService.clarifications_for(decision) -> tuple[ClarificationSpec, ...]`.
- Preserves: `ResearchOsService.resolve(request) -> ResolutionDecision` unchanged.

- [ ] **Step 1: Write failing end-to-end passport tests**

```python
def test_plan_binds_exact_component_revisions_and_method_space() -> None:
    service = ResearchOsService()
    request = independent_mean_request()
    passport = service.plan(request, _passport_envelope())
    assert passport.question_ref.digest == request.question.digest()
    assert passport.estimand_ref.digest == request.estimand.digest()
    assert passport.study_ref.digest == request.study.digest()
    assert passport.method_space_digest == service.method_space_digest
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_research_os_planning.py -q -p no:cacheprovider`

Expected: `ResearchOsService` has no `plan` method.

- [ ] **Step 3: Implement pure composition**

`plan()` resolves once, binds the three exact component references, hashes the semantic decision, looks up only stable capability metadata for `recommend_local`, resolves only registered questions for `clarify`, and copies only verified route IDs for `route_external`. Passport project ID must match all request components. No default capability is selected.

- [ ] **Step 4: Test all four actions and question registry lookup**

```python
def test_clarify_passport_has_questions_but_no_capability() -> None:
    passport = ResearchOsService().plan(unknown_pairing_request(), _passport_envelope())
    assert passport.clarify is not None
    assert passport.recommend_local is None
    assert passport.clarify.question_ids
```

Use an injected test Method Space for `route_external`; the shipping P1 catalog remains route-free. Test abstention for causal and integrity cases.

- [ ] **Step 5: Run service/planning regression and ruff**

Run: `python -m pytest tests/test_research_os_service.py tests/test_research_os_planning.py -q -p no:cacheprovider`

Expected: all tests pass and the existing `resolve()` behavior is unchanged.

Run: `python -m ruff check src/modori/research_os/service.py tests/test_research_os_planning.py`

Expected: zero errors.

- [ ] **Step 6: Commit Task 3**

Commit message: `feat: compose research analysis passports`

---

### Task 4: Boundary and full verification

**Files:**
- Modify: `tests/test_research_os_architecture.py`
- Modify only if a failing test proves a defect: files created in Tasks 1-3.

- [ ] **Step 1: Extend architecture guards**

Assert the new modules have no network, file, subprocess, model, calculation, dynamic-execution, persistence, command, worker-token, path, or URL authority. Assert `ResearchOsService` exposes only `resolve`, `plan`, and `clarifications_for` as public callable methods.

- [ ] **Step 2: Run focused Research OS tests**

Run: `python -m pytest tests/test_research_os_*.py -q -p no:cacheprovider`

Expected: all pass with zero warnings.

- [ ] **Step 3: Run existing recommendation regressions**

Run: `python -m pytest tests/test_experimental_recommendation_boundary.py tests/test_recommendation_baseline.py tests/ui/test_experimental_recommendation_flow.py -q -p no:cacheprovider`

Expected: all pass unchanged.

- [ ] **Step 4: Run full suite with R anchor and lint**

Run with `MODORI_RSCRIPT=C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe`: `python -m pytest -q -p no:cacheprovider`

Expected: 0 failures.

Run: `python -m ruff check src/modori/research_os tests/test_research_os_*.py`

Expected: zero errors.

- [ ] **Step 5: Verify isolation and commit**

Run: `git status --short`

Expected: only Task 1-4 files before commit; existing recommendation UI, benchmark, packages, and VM payloads remain unchanged.

Commit message: `test: lock passport and clarification boundaries`

## Completion Boundary

Completion means C1 decisions can be rendered by a future Guided/Pro surface through strict clarification metadata and an authority-free passport. It does not authorize UI rendering, answer application, persistence, analysis execution, external route launching, or a recommendation-validity claim.
