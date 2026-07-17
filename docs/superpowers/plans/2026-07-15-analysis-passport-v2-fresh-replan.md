# AnalysisPassport V2 Fresh-Replan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. The current root session is the exclusive writer; the user prohibits subagents.

**Goal:** Ship an exact V1/V2 AnalysisPassport contract, single-pass V2 planning, V1 answer rejection with fresh replanning, and one-active-passport durable coordination without direct V1 migration.

**Architecture:** `modori.research_os` remains pure and model-free. It gains strict historical-plan decoding, a schema-tagged AnalysisPassport wire contract, canonical ResearchRequest binding, and exact V2 transition validation. `modori.research_memory` gains a pure passport-history reducer and a coordinator that commits one V2 passport before any durable answer; SQLite remains an unchanged append-only transport.

**Tech Stack:** Python 3.12 standard library (`dataclasses`, `enum`, `hashlib`, `json`, `tracemalloc`), existing SQLite Decision Ledger, pytest, ruff. No new dependency.

## Global Constraints

- Exclusive worktree: `C:\Users\V\.codex\worktrees\b39f\TongTong`.
- Exclusive branch: `codex/research-os-contract-design`.
- Do not merge, push, switch branches, modify another worktree, or use subagents.
- Approved design: `docs/superpowers/specs/2026-07-15-analysis-passport-v2-explicit-migration-design.md` at commit `2be9fc7`.
- Preserve exact V1 mapping and golden digest `256019034d7fb5fbe1ac1547c5c3516dfc83ae0f125f059c5ceb91f6c9d41ec8`.
- New service writes only `modori.analysis_passport` schema version 2.
- `migration_applied` remains reserved. No production producer, migration disposition, or V1-to-V2 lineage edge is added.
- A V1 passport never authorizes a new answer. Recovery resolves the current local request once and creates a fresh V2 object.
- One visible decision invokes the resolver/counterfactual planner at most once.
- Available-variable binding uses sorted canonical NFC IDs; evidence references retain event-sequence order.
- At most one outstanding V2 clarify passport exists per `(project_id, request_binding_digest, clarification_registry_digest)` key.
- A new durable V2 answer requires a prior outstanding local `passport_committed` event for its exact passport artifact.
- Historical V1 answer events replay without a synthetic commit.
- Imported V1/V2 passports remain authority-free and never become Fact, answer, or local decision authority.
- Embedded plan gate: less than 64 KiB canonical JSON.
- V2 construction/round-trip overhead gate, excluding the resolver call: less than 50 ms and 5 MiB on the locked P1 case.
- Preserve the accepted 30-second office-PC interaction budget and do not relax any gate to obtain a pass.
- Do not add UI, explanation rendering, cloud transfer, SLM, analysis execution, package payload, VM payload, or SQLite schema changes.
- Every production change follows RED → verify RED → GREEN → verify GREEN → refactor.
- Fresh focused baseline at `2be9fc7`: 193 passed in 10.70 seconds. This is not a full-suite completion claim.

---

### Task 1: Strict historical ClarificationPlan decoder

**Files:**
- Modify: `src/modori/research_os/counterfactual_planner.py`
- Create: `tests/research_os_v2_fixtures.py`
- Modify: `tests/test_research_os_counterfactual_planner.py`
- Modify: `tests/test_research_os_passport.py`

**Interfaces:**
- Consumes: existing `ClarificationPlan.to_mapping()` output.
- Produces: `TerminalLoss.from_mapping(payload)`, `QuestionEvaluationTrace.from_mapping(payload)`, and `ClarificationPlan.from_mapping(payload)`.
- Preserves: existing planner output, digest, rank ordering, and `PLANNER_VERSION = "research-os-counterfactual-minimax-v1"`.

Create one shared worst-case plan fixture instead of importing private helpers from
another test module:

```python
def locked_p1_plan() -> ClarificationPlan:
    method_space = build_p1_method_space()
    registry = build_p1_clarification_registry()
    resolver = C1Resolver(method_space, registry)
    addresses = tuple(
        sorted({rule.fact_address for rule in method_space.rules})
    )
    decision = resolver.resolve(
        ResolutionContext(
            facts={
                address: Fact.unknown(reason_code="p1_locked_slice_unknown")
                for address in addresses
            },
            surface=ProductSurface.EXPERIMENTAL,
            question_budget_remaining=3,
        )
    )
    plan = decision.clarification_plan
    assert plan is not None
    assert len(plan.evaluations) == 15
    return plan
```

- [ ] **Step 1: Add the V1 passport characterization test before changing any contract**

```python
def test_v1_wire_mapping_and_digest_are_frozen() -> None:
    passport = _valid_recommend_passport()

    assert passport.envelope.schema_version == 1
    assert "request_binding_digest" not in passport.to_mapping()
    assert "clarification_registry_digest" not in passport.to_mapping()
    assert passport.digest() == (
        "256019034d7fb5fbe1ac1547c5c3516dfc83ae0f125f059c5ceb91f6c9d41ec8"
    )
    assert AnalysisPassport.from_mapping(passport.to_mapping()) == passport
```

- [ ] **Step 2: Add failing strict plan-decoder tests**

Use a real P1 clarify decision so the test covers every nested evaluation:

```python
def test_clarification_plan_strict_roundtrip_recomputes_derived_rank_key() -> None:
    plan = locked_p1_plan()

    restored = ClarificationPlan.from_mapping(plan.to_mapping())

    assert restored == plan
    assert restored.digest() == plan.digest()
    forged = plan.to_mapping()
    forged["evaluations"][0]["rank_key"][-1] = "forged_question"
    with pytest.raises(PlannerError, match="rank_key"):
        ClarificationPlan.from_mapping(forged)


@pytest.mark.parametrize(
    ("mutator", "message"),
    (
        (lambda value: value.__setitem__("unknown", True), "unknown field"),
        (
            lambda value: value.__setitem__("selected_question_version", True),
            "positive integer",
        ),
        (lambda value: value.pop("evaluated_state_count"), "missing field"),
    ),
)
def test_clarification_plan_decoder_rejects_open_or_ambiguous_wire(
    mutator,
    message: str,
) -> None:
    plan = locked_p1_plan()
    payload = plan.to_mapping()
    mutator(payload)
    with pytest.raises(PlannerError, match=message):
        ClarificationPlan.from_mapping(payload)
```

Import `locked_p1_plan` from `tests.research_os_v2_fixtures` in both test modules.

- [ ] **Step 3: Verify RED**

Run:

`python -m pytest tests/test_research_os_counterfactual_planner.py tests/test_research_os_passport.py -q -p no:cacheprovider`

Expected: the V1 characterization passes; decoder tests fail because the three
`from_mapping` methods do not exist.

- [ ] **Step 4: Add exact decoder helpers and the three classmethods**

Add closed helpers near the existing planner validators:

```python
def _require_mapping(value: object, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PlannerError(f"{context} must be an object")
    return value


def _require_exact_keys(
    payload: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise PlannerError(f"{context} unknown field(s): {', '.join(unknown)}")
    missing = sorted(allowed - set(payload))
    if missing:
        raise PlannerError(f"{context} missing field(s): {', '.join(missing)}")


def _decode_integer_list(
    value: object,
    field_name: str,
    *,
    length: int,
) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise PlannerError(f"{field_name} must contain {length} integers")
    if any(type(item) is not int for item in value):
        raise PlannerError(f"{field_name} must contain integers")
    return tuple(value)
```

Freeze the emitted name separately from the historical decoder allowlist:

```python
PLANNER_VERSION_V1 = "research-os-counterfactual-minimax-v1"
PLANNER_VERSION = PLANNER_VERSION_V1
_DECODABLE_PLANNER_VERSIONS = frozenset({PLANNER_VERSION_V1})
```

`ClarificationPlan.__post_init__` accepts only
`_DECODABLE_PLANNER_VERSIONS`. The running planner still emits
`PLANNER_VERSION`. A future constant change may not remove V1 from the decoder without
a passport schema decision.

Implement `TerminalLoss.from_mapping` with its exact six keys and let
`TerminalLoss.__post_init__` reject negative and Boolean integers:

```python
@classmethod
def from_mapping(cls, payload: Mapping[str, Any]) -> TerminalLoss:
    payload = _require_mapping(payload, "TerminalLoss")
    _require_exact_keys(
        payload,
        frozenset(
            {
                "risk_vector",
                "frontier_size",
                "blocking_fact_count",
                "questions_asked",
                "dependency_deficit",
                "answer_kind_cost",
            }
        ),
        "TerminalLoss",
    )
    risk = _decode_integer_list(payload["risk_vector"], "risk_vector", length=5)
    return cls(
        risk_vector=risk,  # type: ignore[arg-type]
        frontier_size=payload["frontier_size"],
        blocking_fact_count=payload["blocking_fact_count"],
        questions_asked=payload["questions_asked"],
        dependency_deficit=payload["dependency_deficit"],
        answer_kind_cost=payload["answer_kind_cost"],
    )
```

Implement `QuestionEvaluationTrace.from_mapping` with all fourteen stored keys. Decode
`branch_snapshot_digests` as a list of two-item lists, construct the trace, then compare
the supplied `rank_key` with:

```python
expected_rank_key = [
    *trace.worst_loss.to_mapping().values(),
    trace.question_id,
]
if payload["rank_key"] != expected_rank_key:
    raise PlannerError("QuestionEvaluationTrace rank_key does not recompute")
```

Implement `ClarificationPlan.from_mapping` with its eleven exact keys, list-to-tuple
decoding for risk and evaluations, and construction through the existing invariant-rich
dataclass. Do not accept a planner-version alias or infer a missing derived field.

- [ ] **Step 5: Verify GREEN and lint**

Run:

`python -m pytest tests/test_research_os_counterfactual_planner.py tests/test_research_os_passport.py -q -p no:cacheprovider`

`python -m ruff check src/modori/research_os/counterfactual_planner.py tests/research_os_v2_fixtures.py tests/test_research_os_counterfactual_planner.py tests/test_research_os_passport.py`

Expected: both commands pass; the V1 golden digest is unchanged.

- [ ] **Step 6: Commit**

Commit message: `feat: add strict clarification plan decoder`

---

### Task 2: Schema-tagged V1/V2 AnalysisPassport wire contract

**Files:**
- Modify: `src/modori/research_os/passport.py`
- Modify: `src/modori/research_os/__init__.py`
- Modify: `tests/research_os_v2_fixtures.py`
- Modify: `tests/test_research_os_passport.py`
- Modify: `tests/test_research_os_architecture.py`

**Interfaces:**
- Consumes: `ClarificationPlan.from_mapping()` from Task 1.
- Produces: `ClarificationRef`, `ClarifyPayloadV2`,
  `clarify_decision_digest(question_id=..., fact_address=..., plan=...)`, and version-tagged
  `AnalysisPassport.from_mapping()`.
- Preserves: the public `AnalysisPassport` runtime class and exact V1 constructor,
  mapping, and digest.

- [ ] **Step 1: Add failing V2 contract tests**

```python
def test_v2_clarify_roundtrip_binds_exact_plan_and_question_revision() -> None:
    plan = locked_p1_plan()
    decision_digest = clarify_decision_digest(
        question_id=plan.selected_question_id,
        fact_address=plan.selected_fact_address,
        plan=plan,
    )
    reference = ClarificationRef(
        question_id=plan.selected_question_id,
        question_version=plan.selected_question_version,
        question_digest=plan.selected_question_digest,
        fact_address=plan.selected_fact_address,
        planner_version=plan.planner_version,
        clarification_plan_digest=plan.digest(),
        source_decision_digest=decision_digest,
    )
    passport = replace(
        _passport(clarify=_clarify_payload()),
        envelope=replace(_passport_envelope(), schema_version=2),
        resolver_decision_digest=decision_digest,
        request_binding_digest="d" * 64,
        clarification_registry_digest="e" * 64,
        clarify=ClarifyPayloadV2(reference, plan),
    )

    restored = AnalysisPassport.from_mapping(passport.to_mapping())

    assert restored == passport
    assert restored.clarify == ClarifyPayloadV2(reference, plan)


def test_v1_and_v2_shapes_are_structurally_exclusive() -> None:
    v1 = _passport(clarify=_clarify_payload()).to_mapping()
    v1["request_binding_digest"] = "d" * 64
    with pytest.raises(PassportError, match="unknown field"):
        AnalysisPassport.from_mapping(v1)

    v2 = _valid_v2_clarify().to_mapping()
    v2["clarify"] = _clarify_payload().to_mapping()
    with pytest.raises(PassportError, match="version 2 clarify"):
        AnalysisPassport.from_mapping(v2)


def test_unknown_passport_version_fails_closed() -> None:
    payload = _valid_v2_clarify().to_mapping()
    payload["envelope"]["schema_version"] = 3
    with pytest.raises(PassportError, match="unsupported schema version"):
        AnalysisPassport.from_mapping(payload)
```

Use this exact local helper for the second and third tests:

```python
def _valid_v2_clarify() -> AnalysisPassport:
    plan = locked_p1_plan()
    decision_digest = clarify_decision_digest(
        question_id=plan.selected_question_id,
        fact_address=plan.selected_fact_address,
        plan=plan,
    )
    reference = ClarificationRef(
        question_id=plan.selected_question_id,
        question_version=plan.selected_question_version,
        question_digest=plan.selected_question_digest,
        fact_address=plan.selected_fact_address,
        planner_version=plan.planner_version,
        clarification_plan_digest=plan.digest(),
        source_decision_digest=decision_digest,
    )
    return replace(
        _passport(clarify=_clarify_payload()),
        envelope=replace(_passport_envelope(), schema_version=2),
        resolver_decision_digest=decision_digest,
        request_binding_digest="d" * 64,
        clarification_registry_digest="e" * 64,
        clarify=ClarifyPayloadV2(reference, plan),
    )
```

Also parameterize one-field mutations for `question_version=True`, plan digest,
question digest, fact address, selected question, source decision digest, missing V2
binding digest, and a V2 plan carrying an unknown key.

- [ ] **Step 2: Verify RED**

Run:

`python -m pytest tests/test_research_os_passport.py tests/test_research_os_architecture.py -q -p no:cacheprovider`

Expected: import failures for `ClarificationRef` and `ClarifyPayloadV2`.

- [ ] **Step 3: Implement the V2 clarify types**

Add these exact immutable types:

```python
@dataclass(frozen=True)
class ClarificationRef:
    question_id: str
    question_version: int
    question_digest: str
    fact_address: str
    planner_version: str
    clarification_plan_digest: str
    source_decision_digest: str

    def __post_init__(self) -> None:
        _require_closed_id(self.question_id, "question_id")
        if type(self.question_version) is not int or self.question_version < 1:
            raise PassportError("question_version must be a positive integer")
        _require_digest(self.question_digest, "question_digest")
        _require_closed_id(self.fact_address, "fact_address")
        _require_closed_id(self.planner_version, "planner_version")
        _require_digest(
            self.clarification_plan_digest,
            "clarification_plan_digest",
        )
        _require_digest(self.source_decision_digest, "source_decision_digest")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question_version": self.question_version,
            "question_digest": self.question_digest,
            "fact_address": self.fact_address,
            "planner_version": self.planner_version,
            "clarification_plan_digest": self.clarification_plan_digest,
            "source_decision_digest": self.source_decision_digest,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ClarificationRef:
        payload = _require_mapping(payload, "ClarificationRef")
        _require_exact_keys(
            payload,
            frozenset(
                {
                    "question_id",
                    "question_version",
                    "question_digest",
                    "fact_address",
                    "planner_version",
                    "clarification_plan_digest",
                    "source_decision_digest",
                }
            ),
            "ClarificationRef",
        )
        return cls(**payload)
```

The closed decision-digest helper must reproduce
`ResolutionDecision.semantic_signature` exactly:

```python
def clarify_decision_digest(
    *,
    question_id: str,
    fact_address: str,
    plan: ClarificationPlan,
) -> str:
    return canonical_digest(
        {
            "semantic_signature": (
                PrimaryAction.CLARIFY.value,
                (),
                (),
                (question_id,),
                (fact_address,),
                (),
                plan.to_mapping(),
            )
        }
    )
```

Implement the payload without fallback fields:

```python
@dataclass(frozen=True)
class ClarifyPayloadV2:
    clarification_ref: ClarificationRef
    clarification_plan: ClarificationPlan

    def __post_init__(self) -> None:
        if not isinstance(self.clarification_ref, ClarificationRef):
            raise PassportError(
                "clarification_ref must be a ClarificationRef"
            )
        if not isinstance(self.clarification_plan, ClarificationPlan):
            raise PassportError(
                "clarification_plan must be a ClarificationPlan"
            )
        ref = self.clarification_ref
        plan = self.clarification_plan
        expected = (
            (ref.question_id, plan.selected_question_id, "question ID"),
            (ref.fact_address, plan.selected_fact_address, "fact address"),
            (
                ref.question_version,
                plan.selected_question_version,
                "question version",
            ),
            (
                ref.question_digest,
                plan.selected_question_digest,
                "question digest",
            ),
            (ref.planner_version, plan.planner_version, "planner version"),
            (
                ref.clarification_plan_digest,
                plan.digest(),
                "clarification plan digest",
            ),
            (
                ref.source_decision_digest,
                clarify_decision_digest(
                    question_id=ref.question_id,
                    fact_address=ref.fact_address,
                    plan=plan,
                ),
                "source decision digest",
            ),
        )
        for actual, wanted, field_name in expected:
            if actual != wanted:
                raise PassportError(f"clarify {field_name} mismatch")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "clarification_ref": self.clarification_ref.to_mapping(),
            "clarification_plan": self.clarification_plan.to_mapping(),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ClarifyPayloadV2:
        payload = _require_mapping(payload, "ClarifyPayloadV2")
        _require_exact_keys(
            payload,
            frozenset({"clarification_ref", "clarification_plan"}),
            "ClarifyPayloadV2",
        )
        return cls(
            clarification_ref=ClarificationRef.from_mapping(
                _require_mapping(
                    payload["clarification_ref"],
                    "clarification_ref",
                )
            ),
            clarification_plan=ClarificationPlan.from_mapping(
                _require_mapping(
                    payload["clarification_plan"],
                    "clarification_plan",
                )
            ),
        )
```

- [ ] **Step 4: Make AnalysisPassport a strict envelope-tagged union**

Add nullable internal fields only as the representation of the outer version tag:

```python
request_binding_digest: str | None = None
clarification_registry_digest: str | None = None
clarify: ClarifyPayload | ClarifyPayloadV2 | None = None
```

Enforce:

```python
version = self.envelope.schema_version
if version == 1:
    if (
        self.request_binding_digest is not None
        or self.clarification_registry_digest is not None
        or (
            self.clarify is not None
            and not isinstance(self.clarify, ClarifyPayload)
        )
    ):
        raise PassportError("version 1 passport has version 2 fields")
elif version == 2:
    _require_digest(self.request_binding_digest, "request_binding_digest")
    _require_digest(
        self.clarification_registry_digest,
        "clarification_registry_digest",
    )
    if self.clarify is not None and not isinstance(
        self.clarify,
        ClarifyPayloadV2,
    ):
        raise PassportError("version 2 clarify payload has the wrong type")
    if (
        isinstance(self.clarify, ClarifyPayloadV2)
        and self.clarify.clarification_ref.source_decision_digest
        != self.resolver_decision_digest
    ):
        raise PassportError("clarify source decision digest mismatch")
else:
    raise PassportError("passport schema version is unsupported")
```

`to_mapping()` must omit both new fields for V1 and require/include both for V2.
`from_mapping()` decodes the envelope first, selects one exact key set, and selects
`ClarifyPayload` only for V1 or `ClarifyPayloadV2` only for V2. No permissive union
decoder may try one shape and fall back to the other.

- [ ] **Step 5: Export the new contract and lock architecture**

Expose `ClarificationRef`, `ClarifyPayloadV2`, and `clarify_decision_digest` from
`modori.research_os`. Extend the architecture test's exact public dataclass-field
inventory and forbidden authority-key scan. The V2 plan may contain hashes, counters,
question IDs, and fact addresses, but the recursive mapping-key scan must still reject
`command`, `path`, `url`, `execute`, `worker_token`, and `pipeline_mutation`.

- [ ] **Step 6: Verify GREEN and V1 invariance**

Run:

`python -m pytest tests/test_research_os_passport.py tests/test_research_os_counterfactual_planner.py tests/test_research_os_architecture.py -q -p no:cacheprovider`

`python -m ruff check src/modori/research_os/passport.py src/modori/research_os/__init__.py tests/test_research_os_passport.py tests/test_research_os_architecture.py`

Expected: all pass and the V1 golden digest remains exact.

- [ ] **Step 7: Commit**

Commit message: `feat: add AnalysisPassport v2 contract`

---

### Task 3: Canonical request binding and single-pass V2 service

**Files:**
- Modify: `src/modori/research_os/service.py`
- Modify: `src/modori/research_os/__init__.py`
- Modify: `tests/test_research_os_service.py`
- Modify: `tests/test_research_os_planning.py`
- Modify: `tests/test_research_memory_ledger_contracts.py`
- Modify: `tests/test_research_memory_ledger_store.py`

**Interfaces:**
- Consumes: V2 passport contract from Task 2.
- Produces:
  - `ResearchRequest.request_binding_mapping() -> dict[str, Any]`
  - `ResearchRequest.request_binding_digest() -> str`
  - `ResolvedPassport(decision, passport)`
  - `ResearchOsService.resolve_and_plan(request, passport_envelope)`
  - `ResearchOsService.clarification_registry_digest`
  - `validate_passport_request_binding(passport, request)`

- [ ] **Step 1: Add failing request-binding tests**

```python
def test_request_binding_canonicalizes_variable_identity_set() -> None:
    request = _independent_mean_request()
    reversed_request = replace(
        request,
        available_variable_ids=tuple(reversed(request.available_variable_ids)),
    )

    assert request.request_binding_digest() == (
        reversed_request.request_binding_digest()
    )
    assert request.request_binding_mapping()["available_variable_ids"] == [
        "arm",
        "score",
    ]


def test_request_binding_changes_for_every_decision_relevant_input() -> None:
    request = _independent_mean_request()
    mutations = (
        replace(request, available_variable_ids=("arm", "other", "score")),
        replace(request, surface=ProductSurface.ORDINARY),
        replace(request, question_budget_remaining=2),
        replace(request, current_dataset_fingerprint="f" * 64),
    )

    assert all(
        changed.request_binding_digest() != request.request_binding_digest()
        for changed in mutations
    )
```

Add a two-reference case proving the complete `DecisionEvidenceRef.to_mapping()` values
are present in sequence order, not merely their digests.

- [ ] **Step 2: Add failing single-pass planning tests**

```python
def test_resolve_and_plan_returns_one_decision_and_matching_v2_passport() -> None:
    service = ResearchOsService()
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    with patch.object(service, "resolve", wraps=service.resolve) as resolve:
        result = service.resolve_and_plan(request, _passport_envelope(version=2))

    resolve.assert_called_once_with(request)
    assert result.passport.envelope.schema_version == 2
    assert result.passport.request_binding_digest == request.request_binding_digest()
    assert (
        result.passport.clarification_registry_digest
        == service.clarification_registry_digest
    )
    assert result.decision.clarification_plan is not None
    assert result.passport.clarify.clarification_plan == (
        result.decision.clarification_plan
    )


def test_plan_delegates_to_resolve_and_plan_without_second_resolution() -> None:
    service = ResearchOsService()
    request = _request()
    with patch.object(
        service,
        "resolve_and_plan",
        wraps=service.resolve_and_plan,
    ) as combined:
        passport = service.plan(request, _passport_envelope(version=2))

    combined.assert_called_once()
    assert passport.envelope.schema_version == 2
```

- [ ] **Step 3: Verify RED**

Run:

`python -m pytest tests/test_research_os_service.py tests/test_research_os_planning.py -q -p no:cacheprovider`

Expected: missing request-binding and `resolve_and_plan` APIs.

- [ ] **Step 4: Implement the canonical request binding**

Move component-reference construction to a module-level pure helper so
`ResearchRequest` can call it before `ResearchOsService` is defined. Add:

```python
def request_binding_mapping(self) -> dict[str, Any]:
    return {
        "schema_id": "modori.research_request_binding",
        "schema_version": 1,
        "question_ref": _component_ref(self.question).to_mapping(),
        "estimand_ref": _component_ref(self.estimand).to_mapping(),
        "study_ref": _component_ref(self.study).to_mapping(),
        "current_dataset_fingerprint": self.current_dataset_fingerprint,
        "available_variable_ids": sorted(self.available_variable_ids),
        "surface": self.surface.value,
        "question_budget_remaining": self.question_budget_remaining,
        "decision_evidence_refs": [
            reference.to_mapping()
            for reference in self.decision_evidence_refs
        ],
    }


def request_binding_digest(self) -> str:
    return canonical_digest(self.request_binding_mapping())
```

Do not normalize invalid input here; `ResearchRequest.__post_init__` must continue to
reject non-NFC values before a digest exists.

Implement the raising validator once and reuse it from transition and memory:

```python
def validate_passport_request_binding(
    passport: AnalysisPassport,
    request: ResearchRequest,
) -> None:
    if not isinstance(passport, AnalysisPassport):
        raise ResearchServiceError("passport must be an AnalysisPassport")
    if not isinstance(request, ResearchRequest):
        raise ResearchServiceError("request must be a ResearchRequest")
    if passport.envelope.schema_version != 2:
        raise ResearchServiceError(
            "complete request binding requires passport version 2"
        )
    project_ids = {
        request.question.envelope.project_id,
        request.estimand.envelope.project_id,
        request.study.envelope.project_id,
    }
    if len(project_ids) != 1:
        raise ResearchServiceError("request component projects do not match")
    expected_project = next(iter(project_ids))
    expected_refs = (
        (passport.question_ref, _component_ref(request.question)),
        (passport.estimand_ref, _component_ref(request.estimand)),
        (passport.study_ref, _component_ref(request.study)),
    )
    expected_evidence = tuple(
        item.evidence_digest for item in request.decision_evidence_refs
    )
    if passport.envelope.project_id != expected_project:
        raise ResearchServiceError("passport project no longer matches request")
    if any(left != right for left, right in expected_refs):
        raise ResearchServiceError("passport component no longer matches request")
    if passport.dataset_fingerprint != request.current_dataset_fingerprint:
        raise ResearchServiceError("passport dataset no longer matches request")
    if passport.decision_evidence_digests != expected_evidence:
        raise ResearchServiceError("passport evidence no longer matches request")
    if passport.request_binding_digest != request.request_binding_digest():
        raise ResearchServiceError("passport request binding no longer matches")
```

- [ ] **Step 5: Implement ResolvedPassport and V2-only planning**

```python
@dataclass(frozen=True)
class ResolvedPassport:
    decision: ResolutionDecision
    passport: AnalysisPassport

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ResolutionDecision):
            raise ResearchServiceError("decision must be a ResolutionDecision")
        if (
            not isinstance(self.passport, AnalysisPassport)
            or self.passport.envelope.schema_version != 2
        ):
            raise ResearchServiceError("resolved passport must use schema version 2")
```

`resolve_and_plan` validates a V2 envelope, calls `resolve(request)` once, computes the
decision digest once, and creates the action payload. For clarify:

```python
plan = decision.clarification_plan
if plan is None:
    raise ResearchServiceError("clarify decision is missing its plan")
decision_digest = canonical_digest(
    {"semantic_signature": decision.semantic_signature}
)
reference = ClarificationRef(
    question_id=plan.selected_question_id,
    question_version=plan.selected_question_version,
    question_digest=plan.selected_question_digest,
    fact_address=plan.selected_fact_address,
    planner_version=plan.planner_version,
    clarification_plan_digest=plan.digest(),
    source_decision_digest=decision_digest,
)
clarify = ClarifyPayloadV2(reference, plan)
```

Construct the passport with both new digests. `plan()` becomes a one-line delegate that
returns `resolve_and_plan(...).passport`. Reject a V1 envelope; no new API writes V1.

- [ ] **Step 6: Update service consumers without changing frozen historical fixtures**

Change service/planning test helpers to create passport envelopes with schema version 2.
Keep explicit V1 helpers in passport and transition tests. In ledger artifact tests,
pass V2 only where `ResearchOsService.plan()` is called; component envelopes and frozen
V1 fixtures remain version 1.

- [ ] **Step 7: Verify GREEN, one-pass behavior, and affected ledger codecs**

Run:

`python -m pytest tests/test_research_os_service.py tests/test_research_os_planning.py tests/test_research_memory_ledger_contracts.py tests/test_research_memory_ledger_store.py -q -p no:cacheprovider`

`python -m ruff check src/modori/research_os/service.py src/modori/research_os/__init__.py tests/test_research_os_service.py tests/test_research_os_planning.py tests/test_research_memory_ledger_contracts.py tests/test_research_memory_ledger_store.py`

Expected: all pass; no V1 digest changes.

- [ ] **Step 8: Commit**

Commit message: `feat: bind single-pass v2 planning`

---

### Task 4: V2 transition validation and typed registry audit

**Files:**
- Create: `src/modori/research_os/passport_audit.py`
- Modify: `src/modori/research_os/transition.py`
- Modify: `src/modori/research_os/__init__.py`
- Modify: `tests/research_os_v2_fixtures.py`
- Create: `tests/test_research_os_passport_audit.py`
- Modify: `tests/test_research_os_transitions.py`

**Interfaces:**
- Consumes: V2 passport and request binding from Tasks 2–3.
- Produces:
  - `PassportMigrationRequired(TransitionError)`
  - `PassportRegistryAuditStatus = verified | unavailable | failure`
  - `PassportRegistryAudit`
  - `audit_passport_registry(passport, registry)`
  - `ClarificationTransitionService.clarification_registry_digest`

- [ ] **Step 1: Add failing audit-status tests**

```python
def test_registry_audit_distinguishes_unavailable_failure_and_verified() -> None:
    passport = v2_clarify_passport(_request(), "confirm_dependence")
    registry = build_p1_clarification_registry()

    assert audit_passport_registry(passport, registry).status is (
        PassportRegistryAuditStatus.VERIFIED
    )
    assert audit_passport_registry(passport, None).status is (
        PassportRegistryAuditStatus.UNAVAILABLE
    )
    changed = ClarificationRegistry(
        questions=tuple(
            replace(item, version=item.version + 1)
            if item.question_id == "confirm_dependence"
            else item
            for item in registry.questions
        ),
        required_question_ids=registry.required_question_ids,
    )
    assert audit_passport_registry(passport, changed).status is (
        PassportRegistryAuditStatus.FAILURE
    )
```

V1 returns `UNAVAILABLE` with reason `v1_registry_unbound`. A supplied mismatching
registry returns `FAILURE`, never `UNAVAILABLE`.

- [ ] **Step 2: Add failing V1 rejection and V2 drift tests**

```python
def test_v1_answer_requires_fresh_replan_before_candidate_construction() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    passport = _legacy_clarify_passport(request, "confirm_dependence")
    answer = _answer_for_passport(request, passport, _choice("independent"))

    with pytest.raises(PassportMigrationRequired):
        ClarificationTransitionService().propose(request, passport, answer)


def test_v2_transition_rejects_request_registry_and_answer_identity_drift() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    passport = v2_clarify_passport(request, "confirm_dependence")
    answer = _answer_for_passport(
        request,
        passport,
        _choice("independent"),
    )

    with pytest.raises(TransitionError):
        ClarificationTransitionService().propose(
            replace(request, question_budget_remaining=2),
            passport,
            answer,
        )

    changed_registry = _registry_with_revised_question("confirm_dependence")
    with pytest.raises(TransitionError):
        ClarificationTransitionService(changed_registry).propose(
            request,
            passport,
            answer,
        )

    with pytest.raises(TransitionError):
        ClarificationTransitionService().propose(
            request,
            passport,
            replace(answer, question_version=answer.question_version + 1),
        )

    with pytest.raises(TransitionError):
        ClarificationTransitionService().propose(
            request,
            passport,
            replace(answer, question_digest="f" * 64),
        )
```

`_registry_with_revised_question` reconstructs the registry with the named question's
version incremented and no other change. In a separate valid-path test, monkeypatch
`CounterfactualPlanner.plan` to raise `AssertionError("second planner search")`; the
`propose()` call must still return a candidate.

- [ ] **Step 3: Verify RED**

Run:

`python -m pytest tests/test_research_os_passport_audit.py tests/test_research_os_transitions.py -q -p no:cacheprovider`

Expected: missing audit module and `PassportMigrationRequired`.

- [ ] **Step 4: Implement the closed audit result**

```python
class PassportRegistryAuditStatus(str, Enum):
    VERIFIED = "verified"
    UNAVAILABLE = "unavailable"
    FAILURE = "failure"


@dataclass(frozen=True)
class PassportRegistryAudit:
    status: PassportRegistryAuditStatus
    reason_code: str


def audit_passport_registry(
    passport: AnalysisPassport,
    registry: ClarificationRegistry | None,
) -> PassportRegistryAudit:
    if passport.envelope.schema_version == 1:
        return PassportRegistryAudit(
            PassportRegistryAuditStatus.UNAVAILABLE,
            "v1_registry_unbound",
        )
    if registry is None:
        return PassportRegistryAudit(
            PassportRegistryAuditStatus.UNAVAILABLE,
            "registry_preimage_unavailable",
        )
    if passport.clarification_registry_digest != registry.digest():
        return PassportRegistryAudit(
            PassportRegistryAuditStatus.FAILURE,
            "registry_digest_mismatch",
        )
    if isinstance(passport.clarify, ClarifyPayloadV2):
        ref = passport.clarify.clarification_ref
        try:
            question = registry.get(ref.question_id)
        except ClarificationError:
            return PassportRegistryAudit(
                PassportRegistryAuditStatus.FAILURE,
                "selected_question_missing",
            )
        if (
            question.lifecycle is not ClarificationLifecycle.ACTIVE
            or question.version != ref.question_version
            or question.digest() != ref.question_digest
            or question.fact_address != ref.fact_address
        ):
            return PassportRegistryAudit(
                PassportRegistryAuditStatus.FAILURE,
                "selected_question_mismatch",
            )
    return PassportRegistryAudit(
        PassportRegistryAuditStatus.VERIFIED,
        "registry_verified",
    )
```

This helper has no persistence, file, network, or execution authority.

- [ ] **Step 5: Replace V1 array matching with exact V2 reference validation**

At the start of `_validate_source`, after type checks:

```python
if passport.envelope.schema_version == 1:
    raise PassportMigrationRequired(
        "version 1 passport requires a fresh version 2 plan"
    )
if not isinstance(passport.clarify, ClarifyPayloadV2):
    raise TransitionError("source passport must have a version 2 clarify action")
validate_passport_request_binding(passport, request)
audit = audit_passport_registry(passport, self._registry)
if audit.status is not PassportRegistryAuditStatus.VERIFIED:
    raise TransitionError(f"source clarification registry is stale: {audit.reason_code}")
```

Compare the answer directly with all four question identity fields in
`clarification_ref`. Retain the existing project, component, dataset, evidence,
question-budget, event replay, answer-shape, and variable checks. Delete V1
`question_ids.index(...)` logic from the new-transition path.

- [ ] **Step 6: Build exact V2 test fixtures without pretending they are service output**

Keep `_legacy_clarify_passport` for the typed rejection test. Add this shared,
self-consistent test-only builder to `tests/research_os_v2_fixtures.py`:

```python
def v2_clarify_passport(
    request: ResearchRequest,
    question_id: str,
) -> AnalysisPassport:
    registry = build_p1_clarification_registry()
    question = registry.get(question_id)
    loss = TerminalLoss(
        risk_vector=(0, 0, 0, 0, 0),
        frontier_size=0,
        blocking_fact_count=0,
        questions_asked=1,
        dependency_deficit=0,
        answer_kind_cost=1,
    )
    trace = QuestionEvaluationTrace(
        question_id=question.question_id,
        question_version=question.version,
        question_digest=question.digest(),
        fact_address=question.fact_address,
        branch_snapshot_digests=(("synthetic_answer", "a" * 64),),
        refusal_snapshot_digest="b" * 64,
        worst_loss=loss,
        guaranteed_e3_plus_blockers_removed=0,
        dependency_deficit=0,
        answer_kind_cost=1,
        evaluated_state_count=1,
        memo_hit_count=0,
        selected=True,
    )
    plan = ClarificationPlan(
        planner_version=PLANNER_VERSION,
        selected_question_id=question.question_id,
        selected_fact_address=question.fact_address,
        selected_question_version=question.version,
        selected_question_digest=question.digest(),
        initial_snapshot_digest="c" * 64,
        initial_risk_vector=(0, 0, 0, 0, 0),
        question_budget_remaining=request.question_budget_remaining,
        evaluations=(trace,),
        evaluated_state_count=1,
        memo_hit_count=0,
    )
    decision_digest = clarify_decision_digest(
        question_id=question.question_id,
        fact_address=question.fact_address,
        plan=plan,
    )
    method_space = build_p1_method_space()

    def component_ref(value) -> ComponentRevisionRef:
        return ComponentRevisionRef(
            schema_id=value.envelope.schema_id,
            object_id=value.envelope.object_id,
            revision=value.envelope.revision,
            digest=value.digest(),
        )

    return AnalysisPassport(
        envelope=SchemaEnvelope(
            schema_id="modori.analysis_passport",
            schema_version=2,
            project_id=request.question.envelope.project_id,
            object_id=f"passport:test:{question_id}",
            revision=1,
            supersedes_revision=None,
            created_event_ref=f"event:passport:test:{question_id}",
        ),
        question_ref=component_ref(request.question),
        estimand_ref=component_ref(request.estimand),
        study_ref=component_ref(request.study),
        dataset_fingerprint=request.current_dataset_fingerprint,
        method_space_version=method_space.version,
        method_space_digest=method_space.digest(),
        ruleset_version=method_space.ruleset_version,
        resolver_decision_digest=decision_digest,
        decision_evidence_digests=tuple(
            item.evidence_digest for item in request.decision_evidence_refs
        ),
        request_binding_digest=request.request_binding_digest(),
        clarification_registry_digest=registry.digest(),
        clarify=ClarifyPayloadV2(
            clarification_ref=ClarificationRef(
                question_id=question.question_id,
                question_version=question.version,
                question_digest=question.digest(),
                fact_address=question.fact_address,
                planner_version=plan.planner_version,
                clarification_plan_digest=plan.digest(),
                source_decision_digest=decision_digest,
            ),
            clarification_plan=plan,
        ),
    )
```

In `test_research_os_transitions.py`, construct an answer from the passport rather than
reading today's registry again:

```python
def _answer_for_passport(
    request: ResearchRequest,
    passport: AnalysisPassport,
    value: AnswerValue,
    *,
    event_sequence: int = 1,
) -> ClarificationAnswerEvent:
    assert isinstance(passport.clarify, ClarifyPayloadV2)
    ref = passport.clarify.clarification_ref
    return ClarificationAnswerEvent(
        event_id=f"answer:{ref.question_id}:{event_sequence}",
        project_id=request.question.envelope.project_id,
        event_sequence=event_sequence,
        source_passport_digest=passport.digest(),
        question_id=ref.question_id,
        question_version=ref.question_version,
        question_digest=ref.question_digest,
        fact_address=ref.fact_address,
        answer_value=value,
    )
```

Durable coordinator tests must use `ResearchOsService.resolve_and_plan()` output, never
this synthetic helper.

For a budget-exhaustion transition test, issue the synthetic passport against an
otherwise identical request with budget 1, then present it with the current request at
budget 0. Do not manufacture a clarify plan whose creation-time budget was already 0.

- [ ] **Step 7: Verify GREEN and transition regression**

Run:

`python -m pytest tests/test_research_os_passport_audit.py tests/test_research_os_transitions.py tests/test_research_os_planning.py -q -p no:cacheprovider`

`python -m ruff check src/modori/research_os/passport_audit.py src/modori/research_os/transition.py src/modori/research_os/__init__.py tests/research_os_v2_fixtures.py tests/test_research_os_passport_audit.py tests/test_research_os_transitions.py`

Expected: all pass; valid propose calls the planner zero times.

- [ ] **Step 8: Commit**

Commit message: `feat: require v2 clarification authority`

---

### Task 5: Pure passport-history reducer and ledger invariants

**Files:**
- Create: `src/modori/research_memory/passport_state.py`
- Create: `tests/research_memory_passport_fixtures.py`
- Create: `tests/test_research_memory_passport_state.py`
- Modify: `src/modori/research_memory/__init__.py`

**Interfaces:**
- Consumes: ordered verified `LedgerEvent` values and content-addressed
  `LedgerArtifact` values.
- Produces:
  - `PassportStateError`
  - `CommittedPassportRecord`
  - `PassportHistory.inspect(events, artifacts)`
  - `PassportHistory.outstanding_for(project_id=..., request_binding_digest=..., clarification_registry_digest=...)`
- Does not read SQLite or the current registry.

- [ ] **Step 1: Add failing history-reducer tests**

Build a genesis event and a V2 `passport_committed` event from a real service-produced
clarify passport through this shared fixture:

```python
def history_with_passport_commit():
    request = _paired_request(
        Fact.unknown(reason_code="pairing_not_confirmed")
    )
    _snapshot, snapshot_artifacts = ResearchRequestSnapshot.capture(request)
    snapshot_artifact = next(
        item
        for item in snapshot_artifacts
        if item.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT
    )
    project_event = LedgerEvent.create(
        project_id="project-1",
        event_id="event:project:1",
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=tuple(
            sorted(item.artifact_id for item in snapshot_artifacts)
        ),
        payload={
            "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id
        },
        previous_event_hash=ZERO_HASH,
        recorded_at_utc=None,
    )
    passport = ResearchOsService().plan(
        request,
        SchemaEnvelope(
            schema_id="modori.analysis_passport",
            schema_version=2,
            project_id="project-1",
            object_id="passport:decision:1",
            revision=1,
            supersedes_revision=None,
            created_event_ref="event:passport:2",
        ),
    )
    assert isinstance(passport.clarify, ClarifyPayloadV2)
    passport_artifact = LedgerArtifact.from_value(passport)
    artifacts = tuple(
        sorted(
            (*snapshot_artifacts, passport_artifact),
            key=lambda item: item.artifact_id,
        )
    )
    commit_event = LedgerEvent.create(
        project_id="project-1",
        event_id="event:passport:2",
        sequence=2,
        event_kind=LedgerEventKind.PASSPORT_COMMITTED,
        subject_artifact_ids=tuple(
            sorted(item.artifact_id for item in artifacts)
        ),
        payload={
            "passport_artifact_id": passport_artifact.artifact_id,
            "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
        },
        previous_event_hash=project_event.event_hash,
        recorded_at_utc=None,
    )
    return (
        (project_event, commit_event),
        artifacts,
        request,
        passport,
    )
```

Then assert:

```python
def test_passport_commit_is_outstanding_only_after_exact_unchanged_snapshot() -> None:
    events, artifacts, request, passport = history_with_passport_commit()

    history = PassportHistory.inspect(events, artifacts)
    records = history.outstanding_for(
        project_id="project-1",
        request_binding_digest=request.request_binding_digest(),
        clarification_registry_digest=passport.clarification_registry_digest,
    )

    assert len(records) == 1
    assert records[0].passport == passport
    assert records[0].commit_event_id == passport.envelope.created_event_ref
```

Add explicit failures for:

```python
@pytest.mark.parametrize(
    "forgery",
    (
        "wrong_created_event_ref",
        "changed_resulting_snapshot",
        "missing_snapshot_subject",
        "extra_subject",
        "request_binding_splice",
        "second_outstanding_same_key",
    ),
)
def test_passport_history_rejects_commit_forgery(forgery: str) -> None:
    events, artifacts = forged_passport_history(forgery)
    with pytest.raises(PassportStateError):
        PassportHistory.inspect(events, artifacts)
```

Add two answer cases: a V2 answer without a prior commit is rejected; a historical V1
answer without a commit remains valid replay evidence. A valid V2 answer marks the
record consumed, so `outstanding_for` returns empty.

`forged_passport_history` starts from the same source request but reconstructs the
passport artifact and event chain after applying exactly one named mutation; it never
edits frozen objects or hashes after construction. `second_outstanding_same_key` appends
a separately created V2 passport event with a new event/object ID but the same request
and registry digests.

- [ ] **Step 2: Verify RED**

Run:

`python -m pytest tests/test_research_memory_passport_state.py -q -p no:cacheprovider`

Expected: import failure because `passport_state` does not exist.

- [ ] **Step 3: Implement immutable record and query types**

```python
PassportKey = tuple[str, str, str]


@dataclass(frozen=True)
class CommittedPassportRecord:
    commit_event_id: str
    commit_sequence: int
    passport_artifact_id: str
    passport: AnalysisPassport
    consumed_by_event_id: str | None = None
    retracted_by_event_id: str | None = None

    @property
    def key(self) -> PassportKey | None:
        if (
            self.passport.envelope.schema_version != 2
            or not isinstance(self.passport.clarify, ClarifyPayloadV2)
        ):
            return None
        request_digest = self.passport.request_binding_digest
        registry_digest = self.passport.clarification_registry_digest
        assert request_digest is not None and registry_digest is not None
        return (
            self.passport.envelope.project_id,
            request_digest,
            registry_digest,
        )

    @property
    def outstanding(self) -> bool:
        return (
            self.consumed_by_event_id is None
            and self.retracted_by_event_id is None
        )


@dataclass(frozen=True)
class PassportHistory:
    records: tuple[CommittedPassportRecord, ...]

    def outstanding_for(
        self,
        *,
        project_id: str,
        request_binding_digest: str,
        clarification_registry_digest: str,
    ) -> tuple[CommittedPassportRecord, ...]:
        key = (
            project_id,
            request_binding_digest,
            clarification_registry_digest,
        )
        return tuple(
            item for item in self.records if item.outstanding and item.key == key
        )
```

- [ ] **Step 4: Implement one deterministic event fold**

`PassportHistory.inspect` must:

1. build one artifact lookup and reject duplicate IDs;
2. walk events in sequence order while tracking the prior resulting snapshot ID;
3. for V2 `passport_committed`, require the unchanged prior snapshot, exact snapshot
   subject closure, exact `created_event_ref`, and
   `validate_passport_request_binding(passport, restored_request)`;
4. reject a second outstanding clarify record with the same key;
5. for `clarification_answered`, require exactly one passport subject in total and
   require its digest to match `answer.source_passport_digest`;
6. require a prior outstanding commit for V2, but preserve legacy V1 replay;
7. require the V2 record's request digest to match the pre-answer current snapshot;
8. require the answer event's exact subject closure: resulting snapshot closure plus
   one passport, the payload answer artifact, and the payload evidence artifact;
9. mark the record consumed with `dataclasses.replace`; and
10. mark a commit retracted when a later `decision_retracted` names its event ID.

The snapshot subject closure for a commit is exactly:

```python
expected_subjects = {
    event.payload["passport_artifact_id"],
    snapshot_artifact.artifact_id,
    snapshot.question_artifact_id,
    snapshot.estimand_artifact_id,
    snapshot.study_artifact_id,
    *snapshot.decision_evidence_artifact_ids,
}
if set(event.subject_artifact_ids) != expected_subjects:
    raise PassportStateError("passport commit subjects are not exact")
```

Return records sorted by `commit_sequence`. Wrap decoder and request-binding errors as
`PassportStateError` without turning missing historical registry into corruption.

- [ ] **Step 5: Verify GREEN and purity**

Run:

`python -m pytest tests/test_research_memory_passport_state.py -q -p no:cacheprovider`

`python -m ruff check src/modori/research_memory/passport_state.py src/modori/research_memory/__init__.py tests/research_memory_passport_fixtures.py tests/test_research_memory_passport_state.py`

Add an architecture assertion that `passport_state.py` imports no `sqlite3`,
`pathlib`, network, UI, subprocess, calculation, or model module.

- [ ] **Step 6: Commit**

Commit message: `feat: derive committed passport state`

---

### Task 6: Durable passport coordinator, active-answer gate, and concurrency

**Files:**
- Modify: `src/modori/research_memory/ledger_store.py`
- Modify: `src/modori/research_memory/evidence_bundle.py`
- Modify: `src/modori/research_memory/promotion.py`
- Modify: `src/modori/research_memory/__init__.py`
- Modify: `tests/test_research_memory_ledger_store.py`
- Modify: `tests/test_research_memory_evidence_bundle.py`
- Modify: `tests/test_research_memory_promotion.py`

**Interfaces:**
- Consumes: `PassportHistory` and V2 transition service.
- Produces:
  - `PassportCommitReceipt`
  - `ResearchMemoryCoordinator.commit_current_passport(...)`
  - exact active-passport precondition for `commit_ready_answer` and
    `commit_accepted_answer`.

- [ ] **Step 1: Add failing coordinator commit tests**

```python
def test_commit_current_passport_preallocates_event_and_preserves_snapshot(
    tmp_path: Path,
) -> None:
    request = _paired_request(
        Fact.unknown(reason_code="pairing_not_confirmed")
    )
    store, request = _initialized(tmp_path, request=request)
    receipt = ResearchMemoryCoordinator().commit_current_passport(
        store,
        request,
        event_id="event:passport:2",
        passport_object_id="passport:decision:1",
        recorded_at_utc=None,
    )

    assert receipt.appended is True
    assert receipt.passport.envelope.created_event_ref == "event:passport:2"
    assert receipt.passport.envelope.schema_version == 2
    assert store.load_request() == request
    assert [item.event_kind for item in store.events()] == [
        LedgerEventKind.PROJECT_CREATED,
        LedgerEventKind.PASSPORT_COMMITTED,
    ]
```

Extend `_initialized` with a keyword-only optional request and initialize that exact
request at event 1. Never mutate a persisted snapshot out of band.

Add:

- a second call on the same request/registry returns the existing passport with
  `appended is False` and does not call `resolve_and_plan`;
- after the prior passport is consumed or stale, reusing its object ID is rejected;
- a V2 answer without prior commit is rejected with no append;
- a committed V2 answer succeeds and consumes the record;
- the consumed passport cannot answer again;
- a V1 passport is rejected by the coordinator while a separately constructed
  historical V1 ledger still opens and replays; and
- after that historical V1 answer, planning the restored current request creates a
  fresh V2 object at revision 1 with `supersedes_revision is None`, leaves the V1
  artifact untouched, and emits `passport_committed` rather than
  `migration_applied`.

- [ ] **Step 2: Add the two-connection race test**

Open the same initialized ledger in two verified stores. Use a
`threading.Barrier(2)` inside a test-only `ResearchOsService` wrapper so both
coordinators read the same head before either append. Call
`commit_current_passport` with different event and object IDs in two threads.

Assert:

```python
assert sum(receipt.appended for receipt in receipts) == 1
assert receipts[0].passport.digest() == receipts[1].passport.digest()
assert DecisionLedgerStore.open(path, "project-1").verify().event_count == 2
```

The losing coordinator must reverify after `LedgerConflictError` and return the winner's
active passport. If the head changed for a different reason, it raises
`PromotionError` rather than retrying with stale inputs.

- [ ] **Step 3: Verify RED**

Run:

`python -m pytest tests/test_research_memory_promotion.py tests/test_research_memory_ledger_store.py tests/test_research_memory_evidence_bundle.py -q -p no:cacheprovider`

Expected: missing `commit_current_passport` and no history enforcement in store/bundle.

- [ ] **Step 4: Integrate PassportHistory into authoritative verification**

In `DecisionLedgerStore._verify_authoritative()`, after structural event and artifact
verification, call:

```python
try:
    PassportHistory.inspect(events, artifacts)
except PassportStateError as exc:
    raise LedgerIntegrityError("passport event history is invalid") from exc
```

Inside `append()`, after expected-head verification and before inserts, merge existing
and commit artifacts by ID, call `_require_verified_data_version()`, append the proposed
events in memory, and run the same history fold. Reject a duplicate artifact ID whose
bytes or metadata differ. Any failure rolls back the transaction.

At the end of `EvidenceBundle._verify_with_limits()`, run the fold and map
`PassportStateError` to `EvidenceBundleErrorCode.CHAIN_INVALID`. This ensures a foreign
bundle may carry V2 only when its own chain is structurally valid; quarantine still
grants it no local authority.

- [ ] **Step 5: Implement PassportCommitReceipt**

```python
@dataclass(frozen=True)
class PassportCommitReceipt:
    request: ResearchRequest
    passport: AnalysisPassport
    head: LedgerHead
    passport_event_id: str
    appended: bool

    def __post_init__(self) -> None:
        if self.passport.envelope.schema_version != 2:
            raise PromotionError("passport receipt requires schema version 2")
        if self.passport.envelope.created_event_ref != self.passport_event_id:
            raise PromotionError("passport receipt event identity mismatch")
        if type(self.appended) is not bool:
            raise PromotionError("appended must be a boolean")
```

- [ ] **Step 6: Implement the exact preallocation/append protocol**

Add `ResearchOsService` to the coordinator constructor and require its registry digest
to equal `ClarificationTransitionService.clarification_registry_digest`.

`commit_current_passport`:

1. calls `_ensure_store_binding` and obtains the verified head;
2. folds current history and returns an existing outstanding record for the current
   request/registry key;
3. rejects `passport_object_id` if any local passport artifact already uses that object
   identity;
4. constructs a fresh V2 `SchemaEnvelope` with revision 1, no supersedes revision, the
   supplied fresh object ID, and `created_event_ref=event_id`;
5. calls `resolve_and_plan` exactly once;
6. captures the unchanged request snapshot and passport artifact;
7. creates `passport_committed` at `head.sequence + 1` with the exact subjects and
   existing payload fields;
8. appends one `LedgerCommit`; and
9. on `LedgerConflictError`, reverifies and returns the winner only if the exact current
   key now has one outstanding record.

No placeholder row is inserted before the final transaction.

- [ ] **Step 7: Gate both durable answer methods**

Before calling the pure transition in `commit_ready_answer` and
`commit_accepted_answer`:

```python
record = self._require_active_committed_passport(store, request, passport)
if (
    record.passport_artifact_id != _artifact_for_value(passport).artifact_id
    or passport.clarification_registry_digest
    != self._research_service.clarification_registry_digest
):
    raise PromotionError("clarification passport is not active")
```

Then retain all existing transition and atomic append behavior. Update test event
sequences: project creation is 1, passport commit is 2, answer is 3, and optional
acceptance is 4.

- [ ] **Step 8: Verify GREEN, race closure, and backward replay**

Run:

`python -m pytest tests/test_research_memory_passport_state.py tests/test_research_memory_ledger_store.py tests/test_research_memory_evidence_bundle.py tests/test_research_memory_promotion.py -q -p no:cacheprovider`

`python -m ruff check src/modori/research_memory/ledger_store.py src/modori/research_memory/evidence_bundle.py src/modori/research_memory/promotion.py src/modori/research_memory/__init__.py tests/test_research_memory_passport_state.py tests/test_research_memory_ledger_store.py tests/test_research_memory_evidence_bundle.py tests/test_research_memory_promotion.py`

Expected: one durable winner in the race, exact existing-passport return for the loser,
and historical V1 replay unchanged.

- [ ] **Step 9: Commit**

Commit message: `feat: commit one active v2 passport`

---

### Task 7: Crash, adversarial, import, and resource closure

**Files:**
- Modify: `src/modori/research_memory/quarantine.py`
- Modify: `tests/test_research_memory_crash_recovery.py`
- Modify: `tests/test_research_memory_quarantine.py`
- Modify: `tests/test_research_memory_performance.py`
- Modify: `tests/test_research_os_architecture.py`
- Modify: `tests/test_research_os_planning.py`
- Create: `docs/qa/analysis-passport-v2-verification.md`

**Interfaces:**
- Consumes: completed V2 and memory paths.
- Produces: final evidence only; no new product authority.

- [ ] **Step 1: Add passport-specific forced-death coverage**

Extend the existing ten-stage child-process crash harness with a
`--passport-child` mode. The parent initializes event 1. The child opens and verifies
the ledger, loads the request, and calls `commit_current_passport` for event 2 while the
existing SQL trace blocks at:

```python
_STAGES = (
    "before_begin",
    "after_begin",
    "after_head_check",
    "after_artifacts",
    "after_event_row",
    "after_relationships",
    "after_materialized",
    "after_head_update",
    "before_commit",
    "after_commit_before_receipt",
)
```

After forced death, full verification must yield exactly:

- stages before commit: one project event, no passport artifact, original snapshot;
- after commit before receipt: project + passport events, one V2 passport artifact,
  unchanged snapshot; and
- never an artifact-only or event-only intermediate state.

- [ ] **Step 2: Add import and catalog-drift tests**

For a valid foreign V2 evidence bundle, assert quarantine can integrity-inspect it but
returns no passport, Fact, or transition authority. Change only the embedded V2
`clarification_registry_digest` while rebuilding a self-consistent foreign bundle and
assert the catalog check returns the existing closed stale-catalog rejection. V1
bundles continue to use the Method Space/ruleset check and remain authority-free.

Update `_catalogs_are_current`:

```python
registry_digest = build_p1_clarification_registry().digest()
if (
    passport.envelope.schema_version == 2
    and passport.clarification_registry_digest != registry_digest
):
    return False
```

- [ ] **Step 3: Add explicit no-migration producer and mutation tests**

Add an architecture scan over `src/modori` that permits the
`MIGRATION_APPLIED` enum/payload declaration in `ledger_contracts.py` but fails if any
production file contains:

```python
event_kind=LedgerEventKind.MIGRATION_APPLIED
```

Add V2 wire mutations for request digest, registry digest, plan digest, source decision
digest, question version/digest, event ref, passport artifact role, and duplicate active
commit. Every mutation must fail before a transition or durable append.

- [ ] **Step 4: Add the fixed resource gates**

For the locked all-unknown P1 clarify request:

```python
def test_v2_embedded_plan_and_contract_overhead_stay_below_fixed_gates(
    monkeypatch,
) -> None:
    worst_plan_bytes = canonical_bytes(locked_p1_plan().to_mapping())
    assert len(worst_plan_bytes) == 14_267
    assert len(worst_plan_bytes) < 64 * 1024

    service = ResearchOsService()
    request = _paired_request(
        Fact.unknown(reason_code="pairing_not_confirmed")
    )
    decision = service.resolve(request)
    assert decision.clarification_plan is not None
    monkeypatch.setattr(service, "resolve", lambda current: decision)
    envelope = _passport_envelope(version=2)

    tracemalloc.start()
    started = time.perf_counter_ns()
    result = service.resolve_and_plan(request, envelope)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert elapsed_ms < 50
    assert peak_bytes < 5 * 1024 * 1024
```

Use `modori.research_memory.canonical.canonical_bytes` only in the test measurement;
do not introduce a Research OS → Research Memory import.

Run the existing 1,000-event open/full-integrity ceiling and durable append ceiling
without changing their thresholds.

- [ ] **Step 5: Verify focused closure**

Run:

`python -m pytest tests/test_research_os_passport.py tests/test_research_os_passport_audit.py tests/test_research_os_service.py tests/test_research_os_planning.py tests/test_research_os_transitions.py tests/test_research_memory_passport_state.py tests/test_research_memory_ledger_contracts.py tests/test_research_memory_ledger_store.py tests/test_research_memory_evidence_bundle.py tests/test_research_memory_promotion.py tests/test_research_memory_quarantine.py tests/test_research_memory_crash_recovery.py tests/test_research_memory_performance.py tests/test_research_os_architecture.py -q -p no:cacheprovider`

Expected: all pass, including twenty forced-death cases: ten existing generic append
cases and ten passport-commit cases.

- [ ] **Step 6: Run static and bytecode gates**

`python -m ruff check src tests`

`python -m compileall -q src tests`

Expected: zero errors.

- [ ] **Step 7: Run the complete repository suite**

`python -m pytest -q -p no:cacheprovider`

Expected: complete pass with only predeclared environmental skips. Record the exact
count and elapsed time; do not reuse the 193-test focused baseline as completion
evidence.

- [ ] **Step 8: Run locked planner and memory evidence**

`python scripts/benchmark_counterfactual_clarification.py --iterations 1`

`python -m pytest tests/test_counterfactual_clarification_benchmark.py tests/test_research_memory_performance.py tests/test_research_memory_constrained_benchmark.py -q -p no:cacheprovider`

Required:

- zero independent-oracle disagreement in the locked planner matrix;
- all deliberate planner mutants killed;
- P1 plan below 64 KiB;
- V2 overhead below 50 ms/5 MiB excluding resolution;
- existing 1,000-event and append ceilings unchanged; and
- no claim that these are recommendation-validity or office-hardware results.

- [ ] **Step 9: Write the verification record from fresh output**

`docs/qa/analysis-passport-v2-verification.md` records:

- implementation commit IDs;
- V1 golden mapping/digest result;
- V2 field and plan-size results;
- exact focused/full pytest counts and times;
- Ruff and compileall results;
- mutation and crash matrix;
- one-pass spy result;
- concurrency winner/loser result;
- quarantine result;
- resource measurements;
- stopped or passed status against every design criterion; and
- nonclaims: no human gold, recommendation validity, numerical accuracy, SPSS
  superiority, broad coverage, office-PC remeasurement, or direct migration.

Do not write “passed” before the corresponding fresh command has completed.

- [ ] **Step 10: Commit**

Commit message: `test: close AnalysisPassport v2 evidence`

---

## Execution Order and Stop Rules

1. Execute Tasks 1–7 in order with `superpowers:executing-plans`.
2. After each RED run, stop if the test passes for an unexplained reason; repair the
   test before implementation.
3. After each GREEN run, stop and diagnose any unrelated regression before continuing.
4. If exact V1 mapping or digest changes, revert only this slice's offending edit and
   stop V2 implementation until the cause is resolved.
5. If a V2 answer can append without a prior commit, or two outstanding passports can
   share one request/registry key, stop the persistence slice.
6. If crash recovery exposes an artifact without its event, stop the persistence slice.
7. If one visible plan triggers two counterfactual searches, stop and redesign the
   service boundary.
8. If the fixed resource gates fail, attempt focused rational optimization. If they
   continue to fail, retain pure fresh V2 planning and do not adopt durable passport
   persistence.
9. Never activate direct migration as a workaround.

## Spec Coverage Matrix

| Design requirement | Implemented by |
| --- | --- |
| Exact V1 dual read and unchanged digest | Tasks 1–2 |
| Strict V2 fields and embedded plan | Tasks 1–2 |
| Canonical variable/evidence ordering | Task 3 |
| Single-pass fresh replan | Task 3 |
| Typed V1 transition rejection | Task 4 |
| Audit unavailable/failure/corruption separation | Tasks 4–6 |
| Event-ID preallocation and no hash cycle | Task 6 |
| Consumed passport cannot reissue authority | Tasks 5–6 |
| One outstanding clarify passport per key | Tasks 5–6 |
| Historical V1 replay | Tasks 5–6 |
| Foreign passport remains authority-free | Tasks 6–7 |
| No `migration_applied` producer | Task 7 |
| Crash, mutation, resource, and full-suite gates | Task 7 |
| “Why this question?” UI | Explicitly excluded for a later slice |
