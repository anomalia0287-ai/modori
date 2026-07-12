# Research OS C1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. This plan is intentionally reserved for the current root session; subagents and other worktrees are prohibited.

**Goal:** Build the immutable, deterministic, estimand-aware Research OS foundation that can return exactly one of `recommend_local`, `clarify`, `route_external`, or `abstain` without reading user data, running calculations, or changing the existing recommendation UI.

**Architecture:** A new `modori.research_os` package owns strict canonical contracts, a versioned Method Space registry, and a pure C1 resolver. A P1 catalog supplies exact method identities and source-bound hard rules. A structure-only service adapts approved `QuestionSpec`, `EstimandSpec`, and `StudySpec` revisions into resolver facts; the existing heuristic `RecommendationService` remains unchanged in this foundation slice.

**Tech Stack:** Python 3.11, frozen dataclasses, closed string enums, standard-library JSON/SHA-256, pytest, ruff. No new dependency.

## Global Constraints

- Exclusive writer workspace: `C:\Users\V\.codex\worktrees\b39f\TongTong` on `codex/research-os-contract-design`.
- The current root session is the only writer. No subagents, no edits in any other worktree, and no branch switching.
- Before every edit batch and commit, compare `git status --short` with the files named by the active task. An unexpected path is a hard stop.
- Do not modify product packages, the existing recommendation benchmark, VM payloads, model artifacts, training data, or calculation-engine behavior.
- Do not add a network, filesystem, subprocess, registry, persistence, model, or arbitrary-code execution path.
- Do not connect this foundation to automatic selection or execution. The existing UI and `RecommendationService` behavior remain unchanged.
- Product exposure is experimental only. Validated and ordinary-product exposure are outside this slice.
- V1 schema decoding is strict: unknown fields, unknown enums, duplicate IDs, invalid revisions, and malformed provenance fail closed.
- The P1 catalog may contain only exact identities. `auto`, generic `ANOVA`, generic `correlation`, generic `nonparametric`, and automatic mean-to-rank substitutions are forbidden.
- `AssociationTarget` is added as the missing typed companion needed to distinguish product-moment from rank-monotonic association. This closes an implementation gap in the approved design without broadening its scientific scope.
- No external route is shipped as usable unless its selection evidence is validated and its route evidence is `roundtrip_verified`; the initial product catalog ships none.
- Every production behavior follows RED → GREEN → REFACTOR. A test must fail for the expected missing behavior before implementation.
- Baseline: 1,527 tests passed and 16 skipped; the four apparent failures pass when `MODORI_RSCRIPT` points to `C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe`.

## Locked Foundation Scope

Included:

1. `Fact<T>` public states and provenance invariants.
2. Canonical `QuestionSpec`, `EstimandSpec`, and `StudySpec` revisions.
3. Exact `CapabilityIdentity`, versioned hard rules, evidence axes, and duplicate detection.
4. Deterministic C1 total action selection and audit trace.
5. P1 exact identities for unweighted summaries/frequencies, Pearson, Spearman, independent Welch mean contrast, and paired-t mean change.
6. An experimental, structure-only service entry point.
7. Contract, property-style finite-state, metamorphic, architecture, and regression tests.

Excluded:

1. UI/QML changes, Guided/Pro screens, persistence, migrations, and project save/load.
2. Existing heuristic recommendation replacement or benchmark mutation.
3. Chi-square/Fisher sparse-cell execution policy, one-way ANOVA split, reliability variants, and all P2 families.
4. External route cards, package launching, export, or round-trip execution.
5. Teacher calls, silver-corpus generation, training, lexical index, classifier, encoder, or generative runtime.
6. Calculation-engine changes, automatic diagnostics, and result-driven route switching.

---

### Task 1: Canonical research contracts

**Files:**
- Create: `src/modori/research_os/__init__.py`
- Create: `src/modori/research_os/contracts.py`
- Test: `tests/test_research_os_contracts.py`

**Interfaces:**
- Produces: `FactState`, `Fact[T]`, `StaleSnapshot[T]`, `SchemaEnvelope`, `QuestionSpec`, `EstimandSpec`, `StudySpec`, their closed enums, `canonical_digest()`, and `ContractError`.
- Consumes: standard library only.

- [ ] **Step 1: Write failing public-state invariant tests**

```python
def test_observed_fact_requires_value_and_provenance() -> None:
    with pytest.raises(ContractError, match="observed fact requires"):
        Fact(state=FactState.OBSERVED, value="person")


def test_unknown_fact_rejects_value_and_alternatives() -> None:
    with pytest.raises(ContractError, match="unknown fact"):
        Fact(state=FactState.UNKNOWN, value="person")
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m pytest tests/test_research_os_contracts.py -q -p no:cacheprovider`

Expected: collection fails because `modori.research_os.contracts` does not exist.

- [ ] **Step 3: Implement the immutable fact and envelope primitives**

```python
class FactState(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    USER_CONFIRMED = "user_confirmed"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    NOT_APPLICABLE = "not_applicable"
    STALE = "stale"


@dataclass(frozen=True)
class Fact(Generic[T]):
    state: FactState
    value: T | None = None
    alternatives: tuple[T, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    reason_code: str | None = None
    stale_snapshot: StaleSnapshot[T] | None = None
```

Implement the approved state invariants exactly and reject blank provenance identifiers.

- [ ] **Step 4: Add strict contract and digest tests**

```python
def test_study_spec_digest_is_independent_of_mapping_key_order() -> None:
    left = _valid_study_spec().to_mapping()
    right = dict(reversed(tuple(left.items())))
    assert StudySpec.from_mapping(left).digest() == StudySpec.from_mapping(right).digest()


def test_study_spec_rejects_unknown_wire_key() -> None:
    payload = _valid_study_spec().to_mapping() | {"method": "anova"}
    with pytest.raises(ContractError, match="unknown field"):
        StudySpec.from_mapping(payload)
```

- [ ] **Step 5: Implement strict V1 specs and association target**

```python
class AssociationTarget(str, Enum):
    PRODUCT_MOMENT = "product_moment"
    RANK_MONOTONIC = "rank_monotonic"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class QuestionSpec:
    envelope: SchemaEnvelope
    capture_mode: CaptureMode
    language: Language
    local_text: str | None
    research_goal: Fact[ResearchGoal]
    causal_intent: Fact[CausalIntent]
    role_hints: tuple[RoleHintBinding, ...] = ()


@dataclass(frozen=True)
class EstimandSpec:
    envelope: SchemaEnvelope
    template: Fact[EstimandTemplate]
    claim_basis: Fact[ClaimBasis]
    target_population: Fact[str]
    unit_of_analysis: Fact[UnitKind]
    target_roles: tuple[TargetRoleBinding, ...]
    contrast: Fact[ContrastKind]
    time_scope: Fact[str]
    effect_scale: Fact[EffectScale]
    association_target: Fact[AssociationTarget]
```

`StudySpec` implements the approved design, role facts for pair/repeated/cluster/stratum/weight, strict SHA-256 fingerprints, missing-code meanings, repeated order, canonical mapping, and digest.

- [ ] **Step 6: Run contract tests and ruff**

Run: `python -m pytest tests/test_research_os_contracts.py -q -p no:cacheprovider`

Expected: all contract tests pass.

Run: `python -m ruff check src/modori/research_os/contracts.py tests/test_research_os_contracts.py`

Expected: zero errors.

- [ ] **Step 7: Commit Task 1**

Commit message: `feat: add research os canonical contracts`

---

### Task 2: Versioned Method Space registry

**Files:**
- Create: `src/modori/research_os/method_space.py`
- Modify: `src/modori/research_os/__init__.py`
- Test: `tests/test_research_os_method_space.py`

**Interfaces:**
- Consumes: `FactState` and canonical digest utilities from Task 1.
- Produces: `CapabilityIdentity`, `Capability`, `HardRule`, `ExternalRoute`, `MethodSpace`, `SupportStatus`, `RecommendationEvidence`, `RouteEvidence`, `LifecycleStatus`, `RuleMode`, `PredicateKind`, `TrustFloor`, and `MethodSpaceError`.

- [ ] **Step 1: Write failing exact-identity and duplicate tests**

```python
def test_capability_identity_keeps_pearson_and_spearman_distinct() -> None:
    assert _pearson_identity().key != _spearman_identity().key


def test_method_space_rejects_duplicate_capability_identity() -> None:
    capability = _capability(_pearson_identity())
    with pytest.raises(MethodSpaceError, match="duplicate capability"):
        MethodSpace(version="p1-v1", ruleset_version="c1-v1", capabilities=(capability, capability))
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_research_os_method_space.py -q -p no:cacheprovider`

Expected: import failure because the registry does not exist.

- [ ] **Step 3: Implement identity, evidence, and hard-rule structures**

```python
@dataclass(frozen=True, order=True)
class CapabilityIdentity:
    family_id: str
    variant_id: str
    estimand_template_id: str
    design_id: str
    role_schema_version: int

    @property
    def key(self) -> str:
        return ":".join((self.family_id, self.variant_id, self.estimand_template_id, self.design_id, f"roles-v{self.role_schema_version}"))


@dataclass(frozen=True)
class HardRule:
    rule_id: str
    rule_version: int
    ruleset_version: str
    capability_key: str
    fact_address: str
    mode: RuleMode
    predicate: PredicateKind
    expected_values: tuple[str, ...]
    trust_floor: TrustFloor
    clarification_id: str | None
    severity: str
    source_refs: tuple[str, ...]
```

`MethodSpace` rejects duplicate capability, route, and rule IDs; missing referenced rules; mixed ruleset versions; blank source references; and route/capability mismatches. Its digest is order-insensitive for registry members.

- [ ] **Step 4: Test evidence separation and route gating data**

```python
def test_calculation_support_does_not_imply_recommendation_validation() -> None:
    capability = _capability(_pearson_identity(), support=SupportStatus.LOCAL_COMPUTE, recommendation=RecommendationEvidence.EXPERIMENTAL)
    assert capability.support is SupportStatus.LOCAL_COMPUTE
    assert capability.recommendation_evidence is RecommendationEvidence.EXPERIMENTAL
```

- [ ] **Step 5: Run tests and ruff**

Run: `python -m pytest tests/test_research_os_method_space.py -q -p no:cacheprovider`

Expected: all Method Space tests pass.

Run: `python -m ruff check src/modori/research_os/method_space.py tests/test_research_os_method_space.py`

Expected: zero errors.

- [ ] **Step 6: Commit Task 2**

Commit message: `feat: add versioned research method space`

---

### Task 3: Deterministic C1 resolver

**Files:**
- Create: `src/modori/research_os/resolver.py`
- Modify: `src/modori/research_os/__init__.py`
- Test: `tests/test_research_os_resolver.py`

**Interfaces:**
- Consumes: `MethodSpace`, `HardRule`, and a `Mapping[str, Fact[object]]`.
- Produces: `C1Resolver.resolve(context) -> ResolutionDecision`, `PrimaryAction`, `ProductSurface`, `ResolutionContext`, `RuleTrace`, and closed abstention reasons.

- [ ] **Step 1: Write failing total-action precedence tests**

```python
def test_integrity_failure_precedes_every_candidate() -> None:
    decision = C1Resolver(_space()).resolve(_context(integrity_errors=("mixed_ruleset",)))
    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.capability_keys == ()


def test_unknown_human_fact_clarifies_before_recommendation() -> None:
    decision = C1Resolver(_space()).resolve(_context(dependence=Fact.unknown()))
    assert decision.action is PrimaryAction.CLARIFY
    assert decision.clarification_ids == ("confirm_dependence",)


def test_stable_experimental_local_identity_recommends_only_on_experimental_surface() -> None:
    decision = C1Resolver(_space()).resolve(_valid_context(surface=ProductSurface.EXPERIMENTAL))
    assert decision.action is PrimaryAction.RECOMMEND_LOCAL
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_research_os_resolver.py -q -p no:cacheprovider`

Expected: import failure because `resolver.py` does not exist.

- [ ] **Step 3: Implement conservative rule evaluation and precedence**

```python
class PrimaryAction(str, Enum):
    RECOMMEND_LOCAL = "recommend_local"
    CLARIFY = "clarify"
    ROUTE_EXTERNAL = "route_external"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class ResolutionDecision:
    action: PrimaryAction
    capability_keys: tuple[str, ...] = ()
    route_ids: tuple[str, ...] = ()
    clarification_ids: tuple[str, ...] = ()
    blocking_fact_addresses: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    rule_trace: tuple[RuleTrace, ...] = ()
```

Rules evaluate to `satisfied`, `excluded`, or `unresolved`. An inferred fact cannot satisfy a human-confirmed rule. Unknown, stale, or action-changing conflict remains unresolved. Hard exclusion cannot be offset by another rule. Decisions follow the approved six-step precedence and return sorted stable sets and traces.

- [ ] **Step 4: Add finite-state and metamorphic tests**

```python
@pytest.mark.parametrize("state", tuple(FactState))
def test_resolver_is_total_for_every_fact_state(state: FactState) -> None:
    decision = C1Resolver(_space()).resolve(_context(dependence=_fact_for_state(state)))
    assert decision.action in set(PrimaryAction)


def test_fact_and_rule_insertion_order_do_not_change_decision() -> None:
    assert C1Resolver(_space()).resolve(_context()).semantic_signature == C1Resolver(_reversed_space()).resolve(_reversed_context()).semantic_signature
```

- [ ] **Step 5: Add external-route and fail-closed tests**

```python
def test_only_validated_roundtrip_route_can_be_returned() -> None:
    assert C1Resolver(_space_with_route(RouteEvidence.ROUNDTRIP_VERIFIED)).resolve(_external_context()).action is PrimaryAction.ROUTE_EXTERNAL


@pytest.mark.parametrize("route_status", [RouteEvidence.UNVERIFIED, RouteEvidence.RECIPE_VERIFIED, RouteEvidence.STALE, RouteEvidence.WITHDRAWN])
def test_unready_route_never_emits(route_status: RouteEvidence) -> None:
    assert C1Resolver(_space_with_route(route_status)).resolve(_external_context()).action is PrimaryAction.ABSTAIN
```

- [ ] **Step 6: Run resolver tests and ruff**

Run: `python -m pytest tests/test_research_os_resolver.py -q -p no:cacheprovider`

Expected: all resolver tests pass.

Run: `python -m ruff check src/modori/research_os/resolver.py tests/test_research_os_resolver.py`

Expected: zero errors.

- [ ] **Step 7: Commit Task 3**

Commit message: `feat: add fail-closed c1 resolver`

---

### Task 4: P1 exact catalog and structure-only service

**Files:**
- Create: `src/modori/research_os/p1_catalog.py`
- Create: `src/modori/research_os/service.py`
- Modify: `src/modori/research_os/__init__.py`
- Test: `tests/test_research_os_p1_catalog.py`
- Test: `tests/test_research_os_service.py`

**Interfaces:**
- Produces: `build_p1_method_space()`, `ResearchOsService`, `ResearchRequest`, and `ResearchOsService.resolve(request)`.
- Consumes: canonical spec revisions and `C1Resolver`.

- [ ] **Step 1: Write failing identity and no-substitution tests**

```python
def test_p1_catalog_contains_exact_pearson_and_spearman_identities_without_auto() -> None:
    keys = tuple(capability.identity.key for capability in build_p1_method_space().capabilities)
    assert any(":pearson_product_moment:" in key for key in keys)
    assert any(":spearman_rank_monotonic:" in key for key in keys)
    assert not any("auto" in key for key in keys)


def test_mean_target_never_resolves_to_rank_variant() -> None:
    decision = ResearchOsService().resolve(_independent_mean_request())
    assert decision.capability_keys == ("compare_two_groups:welch_mean_difference:group_contrast_mean:independent_unweighted:roles-v1",)
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_research_os_p1_catalog.py tests/test_research_os_service.py -q -p no:cacheprovider`

Expected: imports fail because the catalog and service do not exist.

- [ ] **Step 3: Build the exact P1 catalog**

Add only these local experimental identities:

```text
descriptive_summary:unweighted_summary:summary:independent_unweighted:roles-v1
frequency_distribution:unweighted_frequency:frequency_distribution:independent_unweighted:roles-v1
bivariate_association:pearson_product_moment:association_correlation:independent_unweighted:roles-v1
bivariate_association:spearman_rank_monotonic:association_correlation:independent_unweighted:roles-v1
compare_two_groups:welch_mean_difference:group_contrast_mean:independent_unweighted:roles-v1
compare_two_groups:paired_t_mean_change:within_unit_mean_change:paired_unweighted:roles-v1
```

Every hard rule has a stable rule ID, source reference, test reference, human/observed trust floor, and clarification ID where applicable. No rank test, generic ANOVA, reliability, regression, causal, weighted, or clustered identity is included.

- [ ] **Step 4: Implement structure-only fact adaptation**

```python
@dataclass(frozen=True)
class ResearchRequest:
    question: QuestionSpec
    estimand: EstimandSpec
    study: StudySpec
    surface: ProductSurface = ProductSurface.EXPERIMENTAL


class ResearchOsService:
    def resolve(self, request: ResearchRequest) -> ResolutionDecision:
        context = ResolutionContext(
            facts=_facts_from_specs(request),
            surface=request.surface,
            component_versions=_component_versions(request),
        )
        return self._resolver.resolve(context)
```

The adapter validates project IDs, dataset bindings, revisions, variable references, and canonical component versions. It never accepts a dataframe or existing `Dataset` and has no calculation or persistence import.

- [ ] **Step 5: Add end-to-end action tests**

```python
def test_unknown_pairing_returns_clarification_without_candidate() -> None:
    decision = ResearchOsService().resolve(_paired_request(pairing=Fact.unknown()))
    assert decision.action is PrimaryAction.CLARIFY
    assert decision.capability_keys == ()


def test_causal_request_fails_closed_in_p1() -> None:
    decision = ResearchOsService().resolve(_causal_request())
    assert decision.action is PrimaryAction.ABSTAIN
    assert "unsupported_causal_target" in decision.reason_codes
```

- [ ] **Step 6: Run P1/service tests and ruff**

Run: `python -m pytest tests/test_research_os_p1_catalog.py tests/test_research_os_service.py -q -p no:cacheprovider`

Expected: all tests pass.

Run: `python -m ruff check src/modori/research_os tests/test_research_os_*.py`

Expected: zero errors.

- [ ] **Step 7: Commit Task 4**

Commit message: `feat: add exact p1 research os service`

---

### Task 5: Architecture guards and full verification

**Files:**
- Create: `tests/test_research_os_architecture.py`
- Modify only if a defect is demonstrated: files created in Tasks 1-4.

**Interfaces:**
- Verifies the foundation has no forbidden authority and does not alter the old recommendation surface.

- [ ] **Step 1: Write architecture-guard tests**

```python
def test_research_os_has_no_forbidden_runtime_imports() -> None:
    forbidden = {"requests", "httpx", "socket", "urllib", "subprocess", "pickle", "joblib"}
    assert _import_roots_under(Path("src/modori/research_os")).isdisjoint(forbidden)


def test_existing_recommendation_service_signature_is_unchanged() -> None:
    assert tuple(inspect.signature(RecommendationService.recommend).parameters) == ("self", "dataset", "active_analysis")
```

- [ ] **Step 2: Verify RED if any guard exposes a defect**

Run: `python -m pytest tests/test_research_os_architecture.py -q -p no:cacheprovider`

Expected: pass, or fail only on a demonstrated architecture violation that must be removed before proceeding.

- [ ] **Step 3: Run the focused foundation suite**

Run: `python -m pytest tests/test_research_os_*.py -q -p no:cacheprovider`

Expected: all foundation tests pass with zero warnings.

- [ ] **Step 4: Run existing recommendation regression tests**

Run: `python -m pytest tests/test_experimental_recommendation_boundary.py tests/test_recommendation_baseline.py tests/ui/test_experimental_recommendation_flow.py -q -p no:cacheprovider`

Expected: all existing boundary tests pass unchanged.

- [ ] **Step 5: Run the full suite with the pinned R anchor**

Run in PowerShell with `MODORI_RSCRIPT=C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe`: `python -m pytest -q -p no:cacheprovider`

Expected: 0 failures. Existing deliberate skips remain disclosed.

- [ ] **Step 6: Run repository lint and isolation checks**

Run: `python -m ruff check src/modori/research_os tests/test_research_os_*.py`

Expected: zero errors.

Run: `git status --short`

Expected: only the plan and Task 1-5 files before the final commit.

- [ ] **Step 7: Commit Task 5**

Commit message: `test: lock research os foundation boundaries`

## Completion Boundary

This plan is complete only when all five tasks are committed, the full suite has zero failures with the existing R anchor configured, and the existing recommendation UI and benchmark remain byte-for-byte unchanged. Completion authorizes planning of the next UI intake slice; it does not authorize that slice automatically.
