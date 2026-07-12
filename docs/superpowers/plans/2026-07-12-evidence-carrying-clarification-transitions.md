# Evidence-Carrying Clarification Transitions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. The current root session is the exclusive writer; subagents are prohibited by the user.

**Goal:** Turn P1 clarification answers into immutable, stale-safe, explicitly accepted spec revisions whose evidence digests are carried into the next AnalysisPassport.

**Architecture:** Harden ClarificationSpec with auditable branches and lifecycle, then add immutable answer/acceptance/evidence contracts. A separate pure `ClarificationTransitionService` validates an answer against the exact clarify passport, creates an atomic revision candidate, and commits it only through the correct ready or acceptance path. ResearchOsService remains the sole resolver/planner and copies decision-evidence digests into passports without gaining execution or persistence authority.

**Tech Stack:** Python 3.12 frozen dataclasses, closed enums, standard-library JSON/SHA-256, pytest, ruff. No dependency change.

## Global Constraints

- Exclusive worktree and branch remain `C:\Users\V\.codex\worktrees\b39f\TongTong` and `codex/research-os-contract-design`.
- Do not merge, push, switch branches, invoke subagents, or modify another worktree.
- No UI, persistence, file/network/tool access, calculation, external launch, model, benchmark-data, package, or VM payload change.
- Existing specs and ResearchRequest instances are immutable; transitions return new objects.
- An answer must bind the exact active clarify passport, question revision, component revisions, dataset fingerprint, and project.
- `not_sure` becomes `FactState.UNKNOWN`; it never selects a default or inferred value.
- Any bundle containing an EstimandSpec revision requires a matching acceptance certificate and commits atomically.
- Transition output is planning state only. It cannot configure or run an analysis.
- All tasks follow RED -> GREEN -> REFACTOR and end in an independently verified commit.
- Baseline before this plan: 1,672 passed, 5 skipped, 0 failed with the R anchor; Research OS ruff clean; worktree clean at `1bcb711` before the one-line design correction committed with this plan.

---

### Task 1: Auditable clarification branches and lifecycle

**Files:**
- Modify: `src/modori/research_os/clarification.py`
- Modify: `src/modori/research_os/p1_clarifications.py`
- Modify: `src/modori/research_os/__init__.py`
- Modify: `tests/test_research_os_clarifications.py`

**Interfaces:**
- Produces: `ClarificationLifecycle`, `BranchMatchKind`, `ClarificationBranch`.
- Extends: `ClarificationSpec.dependencies`, `ClarificationSpec.branches`, and `ClarificationSpec.lifecycle`.
- Preserves: all existing P1 question IDs, fact addresses, wording, answer kinds, and neutral method-free copy.

- [ ] **Step 1: Write failing branch-completeness tests**

```python
def test_active_choice_question_must_cover_every_choice_and_not_sure() -> None:
    question = _choice_question()
    with pytest.raises(ClarificationError, match="uncovered choice"):
        replace(question, branches=question.branches[:-2])
    with pytest.raises(ClarificationError, match="not_sure branch"):
        replace(
            question,
            branches=tuple(
                branch
                for branch in question.branches
                if branch.match_kind is not BranchMatchKind.NOT_SURE
            ),
        )


def test_withdrawn_question_cannot_be_answered_by_transition_registry() -> None:
    withdrawn = replace(
        build_p1_clarification_registry().get("confirm_dependence"),
        lifecycle=ClarificationLifecycle.WITHDRAWN,
    )
    assert withdrawn.lifecycle is ClarificationLifecycle.WITHDRAWN
```

- [ ] **Step 2: Run RED**

Run: `C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest tests/test_research_os_clarifications.py -q -p no:cacheprovider`

Expected: import or constructor failures because branch/lifecycle contracts do not exist.

- [ ] **Step 3: Implement closed branch contracts**

```python
class ClarificationLifecycle(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


class BranchMatchKind(str, Enum):
    CHOICE_VALUES = "choice_values"
    EMPTY_VARIABLES = "empty_variables"
    NONEMPTY_VARIABLES = "nonempty_variables"
    ANSWERED = "answered"
    NOT_SURE = "not_sure"


@dataclass(frozen=True)
class ClarificationBranch:
    branch_id: str
    match_kind: BranchMatchKind
    choice_values: tuple[str, ...]
    effects: tuple[ClarificationTrigger, ...]
```

`ClarificationSpec` adds:

```python
dependencies: tuple[str, ...]
branches: tuple[ClarificationBranch, ...]
lifecycle: ClarificationLifecycle
```

Validate NFC text, strict identifiers, unique dependencies/branches, exact choice coverage, empty/nonempty coverage for `VARIABLE_MULTI`, answered coverage for other open kinds, exactly one `NOT_SURE` branch, and strict wire round-trip. Only `ACTIVE` P1 questions ship.

- [ ] **Step 4: Populate deterministic P1 metadata**

Use helper functions that generate one exact branch per choice plus `not_sure`, or empty/nonempty/not-sure branches for variable-multi questions. Declare dependencies explicitly; examples:

```python
"confirm_association_target": ("estimand.template",)
"confirm_claim_basis": (
    "question.research_goal",
    "question.causal_intent",
    "estimand.template",
)
"confirm_repeated_measure_order": (
    "study.dependence_structure",
    "estimand.role.repeated_measure",
)
```

- [ ] **Step 5: Verify Task 1**

Run the clarification tests, all Research OS tests, and ruff on the changed files. Expected: zero failures and zero lint errors.

- [ ] **Step 6: Commit Task 1**

Commit message: `feat: make clarification branches auditable`

---

### Task 2: Answer, acceptance, and decision-evidence contracts

**Files:**
- Create: `src/modori/research_os/decision_evidence.py`
- Modify: `src/modori/research_os/__init__.py`
- Create: `tests/test_research_os_decision_evidence.py`

**Interfaces:**
- Produces: `AnswerValueKind`, `AnswerValue`, `ClarificationAnswerEvent`, `RevisionAcceptanceCertificate`, `DecisionEvidenceKind`, `DecisionEvidenceRef`, `DecisionEvidenceError`.
- Consumes: `canonical_digest` only; no resolver, Method Space, UI, or I/O dependency.

- [ ] **Step 1: Write failing union and replay-evidence tests**

```python
def test_answer_value_has_exactly_one_active_representation() -> None:
    with pytest.raises(DecisionEvidenceError, match="exactly one"):
        AnswerValue(
            kind=AnswerValueKind.CHOICE,
            choice_value="paired",
            variable_ids=("id",),
        )


def test_answer_event_strict_roundtrip_preserves_digest() -> None:
    event = _answer_event()
    restored = ClarificationAnswerEvent.from_mapping(event.to_mapping())
    assert restored == event
    assert restored.digest() == event.digest()
```

- [ ] **Step 2: Run RED**

Run the new test file. Expected: module import failure.

- [ ] **Step 3: Implement strict immutable contracts**

```python
class AnswerValueKind(str, Enum):
    CHOICE = "choice"
    VARIABLES = "variables"
    TEXT = "text"
    NOT_SURE = "not_sure"


@dataclass(frozen=True)
class ClarificationAnswerEvent:
    event_id: str
    project_id: str
    event_sequence: int
    source_passport_digest: str
    question_id: str
    question_version: int
    question_digest: str
    fact_address: str
    answer_value: AnswerValue
```

The acceptance certificate binds candidate, answer, component digests, project, and a later positive event sequence. DecisionEvidenceRef binds ID, kind, sequence, digest, and subject digests. All digests are lowercase SHA-256; IDs are NFC nonblank closed references; tuples are immutable and unique; booleans cannot pass integer fields.

- [ ] **Step 4: Add authority and strict-wire attacks**

Reject unknown wire keys such as `command`, `url`, `path`, `worker_token`, and mixed answer representations. Verify nested mappings contain no authority field.

- [ ] **Step 5: Verify and commit Task 2**

Run the new tests, existing contract tests, and ruff. Commit message: `feat: add decision evidence contracts`.

---

### Task 3: Revision candidate and stale-passport validation

**Files:**
- Create: `src/modori/research_os/transition.py`
- Modify: `src/modori/research_os/__init__.py`
- Create: `tests/test_research_os_transitions.py`

**Interfaces:**
- Produces: `RevisionCandidate`, `ClarificationTransitionService`, `TransitionError`.
- Entry point: `propose(request, passport, answer, *, acceptance_certificate_id=None) -> RevisionCandidate`.
- Candidate exposes `digest()`, `changed_component_digests`, and optional proposed QuestionSpec/EstimandSpec/StudySpec revisions; it is never a ResearchRequest.

- [ ] **Step 1: Write stale and substitution attack tests**

```python
def test_answer_cannot_apply_to_a_different_passport_or_question_revision() -> None:
    with pytest.raises(TransitionError, match="source passport digest"):
        _transition().propose(
            _request(),
            _clarify_passport(),
            replace(_answer(), source_passport_digest="f" * 64),
        )


def test_answer_variable_must_exist_in_exact_request_snapshot() -> None:
    with pytest.raises(TransitionError, match="unknown variable"):
        _transition().propose(
            _request(),
            _clarify_passport(),
            _variable_answer(("substituted",)),
        )
```

- [ ] **Step 2: Run RED**

Expected: `transition.py` import failure.

- [ ] **Step 3: Implement source-proof validation**

Validate all ten conditions in design section 6. Match AnswerValue to AnswerKind and active ClarificationBranch. Reject draft/withdrawn questions, replayed evidence IDs, nonmonotonic event sequences, source component/dataset drift, wrong cardinality, and unknown variables.

- [ ] **Step 4: Implement immutable candidate envelope generation**

Generate changed envelopes from the current component: same schema/project/object ID, revision `current + 1`, `supersedes_revision=current`, and `created_event_ref` equal to the answer event ID for ready bundles or reserved certificate ID for acceptance-required bundles. Require a reserved certificate ID iff the candidate changes EstimandSpec.

- [ ] **Step 5: Verify candidate purity**

Assert source request and all three source spec digests are unchanged, repeated identical inputs produce identical candidate digests, and a changed answer or source digest changes the candidate digest.

- [ ] **Step 6: Verify and commit Task 3**

Run transition tests and ruff. Commit message: `feat: validate clarification revision candidates`.

---

### Task 4: Exact P1 revision mapping, invalidation, and atomic commit

**Files:**
- Modify: `src/modori/research_os/transition.py`
- Modify: `src/modori/research_os/service.py`
- Modify: `tests/test_research_os_transitions.py`
- Modify: `tests/test_research_os_service.py`

**Interfaces:**
- Extends `ResearchRequest` with `decision_evidence_refs: tuple[DecisionEvidenceRef, ...] = ()`.
- Produces:
  - `build_acceptance_certificate(candidate, *, event_sequence) -> RevisionAcceptanceCertificate`
  - `commit_ready(request, candidate) -> ResearchRequest`
  - `commit_accepted(request, candidate, certificate) -> ResearchRequest`

- [ ] **Step 1: Write one mapping test for every P1 question ID**

Parameterize all 15 IDs. Verify the exact target Fact becomes `USER_CONFIRMED` with answer-event provenance, or `UNKNOWN` with `user_not_sure` reason. Verify role insertion/replacement and address-specific cardinality.

- [ ] **Step 2: Write invalidation metamorphic tests**

```python
def test_goal_change_stales_estimand_dependents_and_preserves_snapshots() -> None:
    source = _request()
    candidate = _goal_change_candidate(source)
    proposed = candidate.proposed_estimand
    assert proposed is not None
    assert proposed.template.state is FactState.STALE
    assert proposed.template.stale_snapshot.value == source.estimand.template.value
    assert proposed.template.stale_snapshot.provenance_refs == (
        source.estimand.template.provenance_refs
    )
```

Also test template changes, causal-intent claim invalidation, dependence/repeated-order compatibility, and that source digests never change.

- [ ] **Step 3: Implement exact address codecs and invalidation policy**

Use closed dictionaries from question ID/fact address to enum decoder and spec updater. Do not use dynamic attribute assignment or `eval`. Rebuild role tuples deterministically. Use `StaleSnapshot` for current dependents and unknown for non-current dependents.

- [ ] **Step 4: Implement ready and accepted commit gates**

`commit_ready` rejects any candidate containing an EstimandSpec. `commit_accepted` verifies certificate ID, project, later sequence, candidate digest, answer digest, and the exact sorted changed-component digests. Both revalidate the candidate against base component refs, append evidence refs, decrement question budget once, and return a new ResearchRequest.

- [ ] **Step 5: Prove fresh C1 behavior**

Test `clarify -> answer -> commit -> resolve` for dependence, association target, not_sure budget exhaustion, and a goal change requiring acceptance. No path may auto-run or select a capability before fresh resolution.

- [ ] **Step 6: Verify and commit Task 4**

Run transition/service/resolver regressions and ruff. Commit message: `feat: commit atomic clarification revisions`.

---

### Task 5: Carry decision evidence into AnalysisPassport

**Files:**
- Modify: `src/modori/research_os/passport.py`
- Modify: `src/modori/research_os/service.py`
- Modify: `tests/test_research_os_passport.py`
- Modify: `tests/test_research_os_planning.py`

**Interfaces:**
- Adds: `AnalysisPassport.decision_evidence_digests: tuple[str, ...]`.
- `ResearchOsService.plan()` copies `tuple(ref.evidence_digest for ref in request.decision_evidence_refs)` exactly.

- [ ] **Step 1: Write failing evidence-binding tests**

```python
def test_transition_passport_binds_decision_evidence_in_order() -> None:
    request = _committed_transition_request()
    passport = ResearchOsService().plan(request, _passport_envelope())
    assert passport.decision_evidence_digests == tuple(
        ref.evidence_digest for ref in request.decision_evidence_refs
    )
```

Reject duplicate/malformed digests and unknown wire fields. Existing requests round-trip with an empty tuple.

- [ ] **Step 2: Run RED and implement the metadata field**

Update strict mapping keys, round-trip, digest, architecture field locks, and all passport fixtures. The field carries digests only.

- [ ] **Step 3: Add tamper tests**

Changing any evidence digest must change the passport digest. Reordering evidence must change the digest. A stale candidate or certificate cannot be used to produce a passport.

- [ ] **Step 4: Verify and commit Task 5**

Run passport/planning/transition tests and ruff. Commit message: `feat: bind decision evidence to passports`.

---

### Task 6: Boundary, attack, and full regression gate

**Files:**
- Modify: `tests/test_research_os_architecture.py`
- Modify only if a failing test proves a defect: Task 1-5 files.

- [ ] **Step 1: Extend architecture locks**

Lock the exact public methods of both services and exact dataclass fields. Assert no new module imports product execution, recommendation, calculation, file, network, model, tool, subprocess, persistence, or dynamic-execution authority.

- [ ] **Step 2: Run focused Research OS tests**

Run every `tests/test_research_os_*.py` file explicitly. Expected: all pass, no warnings.

- [ ] **Step 3: Run existing recommendation/UI regressions**

Run `tests/test_experimental_recommendation_boundary.py`, `tests/test_recommendation_baseline.py`, and `tests/ui/test_experimental_recommendation_flow.py` with the root venv. Expected: all pass unchanged.

- [ ] **Step 4: Run complete verification**

Set `MODORI_RSCRIPT=C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe` and run the full pytest suite with `C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe`. Run root-venv ruff on `src/modori/research_os` and every Research OS test. Expected: zero failures and zero lint errors.

- [ ] **Step 5: Verify isolation and commit**

`git status --short` must show only Task 1-6 files. Existing UI, calculation engine, recommendation benchmark data, package files, and VM payloads remain untouched.

Commit message: `test: lock evidence carrying transition boundaries`.

## Completion Boundary

Completion means every P1 clarification answer can be validated against the exact source decision, proposed as an immutable atomic revision bundle, explicitly accepted when it changes scientific meaning, freshly re-resolved, and carried into a tamper-evident passport. It does not authorize persistence, UI rendering, analysis execution, external route launch, model inference, or a recommendation-validity claim.
