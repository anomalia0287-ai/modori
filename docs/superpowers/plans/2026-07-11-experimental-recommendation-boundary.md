# Experimental Recommendation Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Modori's validated calculation core stable while moving every live
recommendation into an explicit, non-default, non-auto-running experimental review
surface without changing the frozen recommendation benchmark.

**Architecture:** Separate calculation execution status, recommendation evidence
status, internal review routing, and historical benchmark levels. Live recommendation
state starts with no selection and produces a pure preparation DTO; only existing
manual configuration commands may mutate the pipeline. Selection provenance is local
UI-session metadata passed to report export as a fixed enum, never a numerical step
parameter.

**Tech Stack:** Python 3.12, dataclasses, `str` enums, PySide6/QML, python-docx,
pytest, existing Modori pipeline and PyInstaller tooling, PowerShell/Hyper-V payload
scripts.

## Global Constraints

- Work only on `codex/recommendation-benchmark-pilot` or a descendant containing
  commits `145a4485d4dd29f68573b318ce1f4f301c464bde` and
  `ec092d55046d3348000bb6e05dfed744963e85cb`.
- Treat `aa04d4347e065f44ef3431ffc59e31c53ca844b9` as the implementation
  baseline. Numerical-code drift checks compare against this commit, not against the
  older release tip that already predates the completed accuracy work.
- Preserve baseline prediction SHA-256
  `FC5D3E9032D086225B0C7C62F4E3145217BA44F8FDDF73CB10E4F5EADD485650`.
- Preserve scorer fingerprint
  `sha256:1d232ac88bc705b8c31735aa6e997d253a388a478c9337d146f6798d50f33aac`.
- Preserve scorer implementation digest
  `sha256:127d7cd7c1f313a592ed6d491307e891fee138f59212ecbbe8e1da8a78765679`.
- Keep every currently executable calculation module `AnalysisStatus.EXECUTABLE`.
- Do not change statistical algorithms, calculation result DTOs, tolerances, or the 22
  V1 calculation-smoke identities.
- Every process starts in `standard`; experimental-mode choice is never persisted.
- No candidate is selected automatically in live product state.
- No candidate selection or preparation mutates steps, cache, results, pipeline
  version, dataset, or worker queue.
- Production UI exposes no `강한 추천`, `기본 추천`, `추천 분석 실행`, recommendation
  accuracy percentage, or expert-equivalence claim.
- Frozen benchmark files may retain historical `strong`/`candidate`/`caution` terms
  through an explicit allowlist.
- Recommendation failure cannot block manual calculation, data access, report export
  for manual analyses, or shutdown.
- Use test-first changes and focused commits. Do not use subagents for this execution;
  the owner previously selected inline execution.

---

## File Structure

- `src/modori/recommendation_policy.py`: shared evidence, routing-policy, and
  routing-tier enums with no UI or benchmark dependencies.
- `src/modori/analysis_catalog.py`: calculation capability plus independent
  recommendation evidence/routing declarations.
- `src/modori/recommendations.py`: live candidates, no-selection state, pure
  `RecommendationPreparation`, and deterministic ordering.
- `src/modori/*_recommendation.py`: provider-emitted routing tiers; no product trust
  labels.
- `src/modori/recommendation_baseline.py`: the only adapter from review routing to the
  frozen benchmark levels and historical default selection.
- `src/modori/ui/recommendation_controller.py`: selected/prepared/confirmed state and
  QML-facing preparation fields; no pipeline mutation or rerun helper.
- `src/modori/ui/controller.py`: standard process default, selection-origin lifecycle,
  report option injection, and invalidation hooks.
- `src/modori/ui/qml/screens/EntryScreen.qml`: explicit experimental entry.
- `src/modori/ui/qml/screens/WorkScreen.qml`: stable standard/experimental switching.
- `src/modori/ui/qml/components/GuideRail.qml`: list, disclaimer, select, prepare,
  confirm, and manual-run flow.
- `src/modori/ui/strings.py`: Korean-first experimental wording.
- `src/modori/ui/contracts.py`: fixed report selection-origin enum field.
- `src/modori/ui/pipeline_ops.py`: pass selection origin into `ReportStep`.
- `src/modori/steps/reporting.py`: fixed bilingual disclosure for assisted selection.
- `scripts/check_product_wording.py`: reusable production-text classifier and banned
  claim scanner.
- `tests/test_experimental_recommendation_boundary.py`: policy, state, benchmark, and
  product-wording boundary tests.
- `tests/ui/test_experimental_recommendation_flow.py`: controller and QML interaction
  contract.
- `.visual-qa/clean-win-vm-payload/experimental-*.csv`: three bounded VM fixtures.
- `docs/qa/experimental-recommendation-vm-runbook.md`: nondeveloper visual acceptance
  steps and evidence checklist.

---

### Task 1: Split Calculation, Evidence, and Review Routing

**Files:**
- Create: `src/modori/recommendation_policy.py`
- Modify: `src/modori/analysis_catalog.py`
- Modify: `tests/test_analysis_catalog.py`
- Modify: `tests/test_analysis_catalog_module_specs.py`
- Modify: `tests/test_analysis_module_contract.py`
- Modify: `tests/test_descriptives_table1_step.py`
- Modify: `tests/test_logistic_regression_recommendation.py`
- Create: `tests/test_experimental_recommendation_boundary.py`

**Interfaces:**
- Produces: `RecommendationEvidenceStatus`, `RecommendationRoutingPolicy`, and
  `RecommendationRoutingTier`.
- Produces: `AnalysisModuleSpec.recommendation_evidence_status` independent of
  `AnalysisModuleSpec.status`.
- Consumes: no later-task types.

- [ ] **Step 1: Write failing enum and catalog-contract tests**

```python
from modori.analysis_catalog import AnalysisStatus, module_specs
from modori.recommendation_policy import (
    RecommendationEvidenceStatus,
    RecommendationRoutingPolicy,
)


ROUTED = {
    RecommendationRoutingPolicy.PRIMARY_REVIEW,
    RecommendationRoutingPolicy.SECONDARY_REVIEW,
    RecommendationRoutingPolicy.HEIGHTENED_REVIEW,
}


def test_all_live_recommendation_families_are_experimental() -> None:
    for spec in module_specs():
        assert spec.status is AnalysisStatus.EXECUTABLE
        if spec.recommendation_policy in ROUTED:
            assert (
                spec.recommendation_evidence_status
                is RecommendationEvidenceStatus.EXPERIMENTAL
            )
        else:
            assert (
                spec.recommendation_evidence_status
                is RecommendationEvidenceStatus.NOT_APPLICABLE
            )


def test_no_live_family_is_validated() -> None:
    assert all(
        spec.recommendation_evidence_status
        is not RecommendationEvidenceStatus.VALIDATED
        for spec in module_specs()
    )
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_experimental_recommendation_boundary.py tests/test_analysis_catalog.py tests/test_analysis_catalog_module_specs.py tests/test_analysis_module_contract.py tests/test_descriptives_table1_step.py tests/test_logistic_regression_recommendation.py
```

Expected: collection fails because `modori.recommendation_policy` and the evidence
field do not exist.

- [ ] **Step 3: Add the shared policy enums**

```python
from enum import Enum


class RecommendationEvidenceStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    EXPERIMENTAL = "experimental"
    VALIDATED = "validated"


class RecommendationRoutingPolicy(str, Enum):
    PRIMARY_REVIEW = "primary_review"
    SECONDARY_REVIEW = "secondary_review"
    HEIGHTENED_REVIEW = "heightened_review"
    MANUAL_ONLY = "manual_only"
    NEVER = "never"


class RecommendationRoutingTier(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    HEIGHTENED_REVIEW = "heightened_review"
```

- [ ] **Step 4: Migrate the catalog exactly**

In `AnalysisModuleSpec`, add:

```python
recommendation_policy: RecommendationRoutingPolicy = RecommendationRoutingPolicy.NEVER
recommendation_evidence_status: RecommendationEvidenceStatus = (
    RecommendationEvidenceStatus.NOT_APPLICABLE
)
```

Every routed module still sets both fields explicitly. The defaults exist only for
manual/never declarations and to preserve valid dataclass field ordering.

Apply this exact routing map:

| Existing policy | New policy | Evidence |
| --- | --- | --- |
| `STRONG` | `PRIMARY_REVIEW` | `EXPERIMENTAL` |
| `CANDIDATE` | `SECONDARY_REVIEW` | `EXPERIMENTAL` |
| `CAUTION_ONLY` | `HEIGHTENED_REVIEW` | `EXPERIMENTAL` |
| `MANUAL_ONLY` | `MANUAL_ONLY` | `NOT_APPLICABLE` |
| `NEVER` | `NEVER` | `NOT_APPLICABLE` |

Delete the old `RecommendationPolicy` enum from `analysis_catalog.py`; import the new
types from `recommendation_policy.py`. Update contract tests to treat only
`MANUAL_ONLY` and `NEVER` as provider-exempt.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all tests pass with only the existing explicit
manual/never skips.

- [ ] **Step 6: Commit the policy split**

```powershell
git add src/modori/recommendation_policy.py src/modori/analysis_catalog.py tests/test_analysis_catalog.py tests/test_analysis_catalog_module_specs.py tests/test_analysis_module_contract.py tests/test_descriptives_table1_step.py tests/test_logistic_regression_recommendation.py tests/test_experimental_recommendation_boundary.py
git commit -m "refactor: separate recommendation evidence policy"
```

---

### Task 2: Remove Live Defaults and Preserve Frozen Baseline A

**Files:**
- Modify: `src/modori/recommendations.py`
- Modify: `src/modori/recommendation_baseline.py`
- Modify: `src/modori/ui/recommendation_controller.py`
- Modify: every `src/modori/*_recommendation.py` provider
- Modify: `tests/test_recommendation_baseline.py`
- Modify: provider recommendation tests
- Modify: `tests/ui/test_recommendations.py`
- Modify: `tests/test_experimental_recommendation_boundary.py`

**Interfaces:**
- Consumes: `RecommendationEvidenceStatus` and `RecommendationRoutingTier`.
- Produces: `RecommendationCandidate.routing_tier` and `.evidence_status`.
- Produces: `RecommendationState(candidates, selected_candidate=None, message_ko)`.
- Produces: private `recommendation_baseline._historical_baseline_default(candidates)`
  for benchmark adapter use only.

- [ ] **Step 1: Write RED tests for no live selection and historical preservation**

```python
def test_live_recommendation_state_starts_without_selection() -> None:
    pilot_root = Path("tests/fixtures/recommendation_benchmark/public/pilot")
    case = {
        "case_id": "pilot-003-two-groups",
        "evidence_stage": "cold_start",
        "data_file": "data/pilot-003-two-groups.csv",
    }
    dataset = load_case_dataset(case, pilot_root)
    state = RecommendationService().recommend(dataset)
    assert state.candidates
    assert state.selected_candidate is None
    assert not hasattr(state, "default_candidate")


def test_historical_baseline_default_is_not_live_state() -> None:
    pilot_root = Path("tests/fixtures/recommendation_benchmark/public/pilot")
    case = {
        "case_id": "pilot-003-two-groups",
        "evidence_stage": "cold_start",
        "data_file": "data/pilot-003-two-groups.csv",
    }
    dataset = load_case_dataset(case, pilot_root)
    state = RecommendationService().recommend(dataset)
    historical = _historical_baseline_default(state.candidates)
    assert historical is state.candidates[0]
    assert state.selected_candidate is None
```

Add a subprocess test that runs `predict-a` into `tmp_path`, reads both files as bytes,
and asserts the canonical SHA-256 above.

- [ ] **Step 2: Run recommendation and baseline tests and verify RED**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests -k recommendation
```

Expected: failures reference missing routing tiers and the still-populated
`default_candidate`.

- [ ] **Step 3: Replace product levels with routing tiers**

Use this DTO shape:

```python
@dataclass(frozen=True)
class RecommendationCandidate:
    candidate_id: str
    kind: RecommendationKind
    title_ko: str
    routing_tier: RecommendationRoutingTier
    reason_ko: str
    evidence_status: RecommendationEvidenceStatus = (
        RecommendationEvidenceStatus.EXPERIMENTAL
    )
    variable_keys: list[str] = field(default_factory=list)
    item_keys: list[str] = field(default_factory=list)
    outcome_key: str = ""
    group_key: str = ""
    predictor_keys: list[str] = field(default_factory=list)
    factor_a_key: str = ""
    factor_b_key: str = ""
    x_key: str = ""
    mediator_key: str = ""
    moderator_key: str = ""
    y_key: str = ""
    model: str = ""
    requires_configuration: bool = False
```

Apply this exact provider migration:

| Old product value | New routing tier |
| --- | --- |
| `강한 추천` | `RecommendationRoutingTier.PRIMARY` |
| `가능한 후보` | `RecommendationRoutingTier.SECONDARY` |
| `주의 필요` | `RecommendationRoutingTier.HEIGHTENED_REVIEW` |

Update ordering to enum keys and keep the existing kind/candidate-id tie breakers.
Migrate mediation and moderated-mediation providers from positional
`variable_keys` interpretation to the explicit `x_key`, `mediator_key`,
`moderator_key`, `y_key`, and `model` fields. Preserve `variable_keys` only where it
is itself the declared analysis role. This prevents a future field reorder from
silently changing a mediation model.

The private baseline adapter remains responsible for historical serialization. For
mediation-family candidates only, `candidate_identity()` reconstructs the frozen
historical `variables` role in X/M/Y or X/M/W/Y order from the named fields. No live
product caller may consume that positional reconstruction. The byte-identity gate in
Step 5 proves that this compatibility adapter does not alter Baseline A.

Keep Task 2 independently runnable while the old QML is still present: the controller
may temporarily retain its existing `recommendationLevel` and
`recommendationCandidateLevelAt` QML properties, but both return only the fixed text
`실험적 후보` and never expose routing tiers. Task 4 removes those compatibility
properties together with the old default-card QML. Update the transitional legacy
shortcut to consume named mediation fields so no positional role path survives even
between commits.

- [ ] **Step 4: Remove the live default and add the historical adapter**

```python
@dataclass(frozen=True)
class RecommendationState:
    candidates: list[RecommendationCandidate]
    selected_candidate: RecommendationCandidate | None
    message_ko: str = ""


def _historical_baseline_default(
    candidates: list[RecommendationCandidate],
) -> RecommendationCandidate | None:
    for candidate in candidates:
        if (
            candidate.routing_tier
            is not RecommendationRoutingTier.HEIGHTENED_REVIEW
            and not candidate.requires_configuration
        ):
            return candidate
    return None
```

Define this private function in `recommendation_baseline.py`, not
`recommendations.py`. `RecommendationService.recommend()` always returns
`selected_candidate=None`. `predict_current_baseline()` calls the private helper and maps routing
tiers to the frozen JSONL levels. No production UI/controller caller may call the
historical helper.

- [ ] **Step 5: Prove the baseline artifact is byte-identical**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts\recommendation_benchmark.py predict-a --pack-root tests\fixtures\recommendation_benchmark --output .tmp\experimental-boundary-baseline.jsonl --force
Get-FileHash -Algorithm SHA256 .tmp\experimental-boundary-baseline.jsonl
```

Expected hash:
`FC5D3E9032D086225B0C7C62F4E3145217BA44F8FDDF73CB10E4F5EADD485650`.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run the Step 2 command plus:

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts\build_recommendation_pilot.py --check
```

Expected: recommendation tests pass and pilot check reports `ok: true`, 20 cases, 19
unique data files.

- [ ] **Step 7: Commit the live-state and baseline separation**

```powershell
git add src/modori/recommendations.py src/modori/recommendation_baseline.py src/modori/ui/recommendation_controller.py src/modori/*_recommendation.py tests
git commit -m "refactor: isolate historical recommendation baseline"
```

---

### Task 3: Add the Pure Recommendation Preparation Boundary

**Files:**
- Modify: `src/modori/recommendations.py`
- Modify: `src/modori/ui/recommendation_controller.py`
- Modify: `src/modori/ui/controller.py`
- Modify: `tests/ui/test_controller.py`
- Create: `tests/ui/test_experimental_recommendation_flow.py`

**Interfaces:**
- Produces: `RecommendationPreparation` and
  `preparation_for_candidate(candidate) -> RecommendationPreparation`.
- Produces QML properties `recommendationPreparationPending`,
  `experimentalRecommendationConfirmed`, `preparedRecommendationIntent`, and
  `preparedRecommendationField(key)`.
- Leaves the current execution shortcut temporarily intact until Task 4 replaces its
  QML caller in the same commit; no new caller may use it.

- [ ] **Step 1: Write RED preparation-purity tests**

```python
class NoSubmitWorker:
    def __init__(self) -> None:
        self.submissions = 0

    def submit(self, job, callback) -> None:
        self.submissions += 1
        raise AssertionError("preparation must not submit a worker job")


def test_select_and_prepare_do_not_touch_pipeline() -> None:
    dataset = _dataset(pd.DataFrame({"score": [1, 2, 3, 4, 5, 6]}))
    pipeline = Pipeline(dataset)
    worker = NoSubmitWorker()
    controller = UiController(pipeline=pipeline, worker=worker)
    controller._refresh_recommendations()
    before_steps = list(pipeline.steps)
    before_version = controller.pipeline_version
    assert controller.selectRecommendationAt(0)
    assert controller.prepareSelectedRecommendationNow()
    assert pipeline.steps == before_steps
    assert controller.pipeline_version == before_version
    assert worker.submissions == 0
```

- [ ] **Step 2: Run the focused controller tests and verify RED**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/ui/test_controller.py tests/ui/test_experimental_recommendation_flow.py
```

- [ ] **Step 3: Implement immutable preparation**

```python
@dataclass(frozen=True)
class RecommendationPreparation:
    candidate_id: str
    analysis_intent: RecommendationKind
    prefill_fields: Mapping[str, object]
    evidence_status: RecommendationEvidenceStatus
    review_requirement: Literal[
        "standard", "configuration_required", "heightened_review"
    ]
```

`preparation_for_candidate()` copies only existing candidate role fields. Wrap the
field dictionary in `MappingProxyType` so frozen DTO callers cannot mutate it.

```python
def preparation_for_candidate(
    candidate: RecommendationCandidate,
) -> RecommendationPreparation:
    if candidate.requires_configuration:
        review_requirement = "configuration_required"
    elif candidate.routing_tier is RecommendationRoutingTier.HEIGHTENED_REVIEW:
        review_requirement = "heightened_review"
    else:
        review_requirement = "standard"
    fields = MappingProxyType(
        {
            "variable_keys": tuple(candidate.variable_keys),
            "item_keys": tuple(candidate.item_keys),
            "outcome_key": candidate.outcome_key,
            "group_key": candidate.group_key,
            "predictor_keys": tuple(candidate.predictor_keys),
            "factor_a_key": candidate.factor_a_key,
            "factor_b_key": candidate.factor_b_key,
            "x_key": candidate.x_key,
            "mediator_key": candidate.mediator_key,
            "moderator_key": candidate.moderator_key,
            "y_key": candidate.y_key,
            "model": candidate.model,
        }
    )
    return RecommendationPreparation(
        candidate_id=candidate.candidate_id,
        analysis_intent=candidate.kind,
        prefill_fields=fields,
        evidence_status=candidate.evidence_status,
        review_requirement=review_requirement,
    )
```

- [ ] **Step 4: Refactor the controller into state-only operations**

`selectRecommendationAt(index)` selects only. `prepareSelectedRecommendationNow()`
creates/stores the DTO and resets confirmation. Add:

```python
@Slot(bool, result=bool)
def setExperimentalRecommendationConfirmed(self, confirmed: bool) -> bool:
    if self._recommendation_preparation is None:
        self._experimental_recommendation_confirmed = False
        return not bool(confirmed)
    self._experimental_recommendation_confirmed = bool(confirmed)
    self._emit_recommendation_state_changed()
    return True

@Slot(result=bool)
def clearExperimentalRecommendationPreparation(self) -> bool:
    self._recommendation_preparation = None
    self._experimental_recommendation_confirmed = False
    self._emit_recommendation_state_changed()
    return True

@Slot(str, result="QVariant")
def preparedRecommendationField(self, key: str) -> object:
    preparation = self._recommendation_preparation
    if preparation is None:
        return None
    return preparation.prefill_fields.get(str(key))
```

`_refresh_recommendations()` and `_clear_recommendations()` clear selected,
preparation, and confirmation state. Dataset/metadata/transform refresh therefore
cannot reuse a stale acknowledgment.

Do not remove the old combined execution methods in this task because production QML
still references them. Task 4 removes the QML reference and methods atomically.

- [ ] **Step 5: Run tests and verify GREEN**

Run the Step 2 command. Expected: selection/preparation is non-mutating. The legacy
shortcut remains temporarily covered by its old tests until Task 4 replaces its QML
caller and deletes it atomically.

- [ ] **Step 6: Commit the pure preparation boundary**

```powershell
git add src/modori/recommendations.py src/modori/ui/recommendation_controller.py src/modori/ui/controller.py tests/ui
git commit -m "refactor: make recommendation preparation non-mutating"
```

---

### Task 4: Make Experimental Guidance Explicit and Confirmed

**Files:**
- Modify: `src/modori/ui/controller.py`
- Modify: `src/modori/ui/strings.py`
- Modify: `src/modori/ui/qml/screens/EntryScreen.qml`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `tests/ui/test_security_privacy.py`
- Modify: `tests/ui/test_mode_action_surfaces.py`
- Modify: `tests/ui/test_guided_standard_variable_selection_flow.py`
- Modify: `tests/ui/test_qml_runtime_load.py`
- Modify: `tests/ui/test_smoke_qml.py`
- Modify: `tests/ui/test_experimental_recommendation_flow.py`

**Interfaces:**
- Consumes: preparation/confirmation properties from Task 3.
- Produces: explicit per-process experimental entry and a list with no preselection.
- Produces: candidate-assisted manual form fill; only the existing manual commit/run
  action may calculate.
- Produces: an explicit manual-form path for every one of the 16 emitted candidate
  kinds, including the four advanced kinds that currently depend on the shortcut
  being removed.
- Removes: `applySelectedRecommendation`, `runPreparedRecommendation`, and
  `runPreparedRecommendationNow` from production controller API after QML no longer
  calls them.

- [ ] **Step 1: Write RED mode, wording, and QML-flow tests**

```python
def test_controller_starts_standard_and_does_not_persist_experimental(tmp_path) -> None:
    store = UiSettingsStore(tmp_path / "settings.json")
    first = UiController(settings_store=store)
    assert first.mode == "standard"
    assert first.chooseMode("guided")
    assert first.mode == "guided"
    second = UiController(settings_store=store)
    assert second.mode == "standard"


def test_experimental_surface_starts_without_selection(controller_with_data) -> None:
    controller = controller_with_data
    assert controller.recommendationCount > 0
    assert controller.recommendationTitle == ""
    assert not controller.recommendationPreparationPending


def test_no_combined_recommendation_execution_api(controller) -> None:
    assert not hasattr(controller, "applySelectedRecommendation")
    assert not hasattr(controller, "runPreparedRecommendation")
    assert not hasattr(controller, "runPreparedRecommendationNow")
```

Add QML source assertions for the persistent status text key, ordering-disclaimer key,
confirmation checkbox, and absence of `runPreparedRecommendationNow`.

Add an exhaustive form-coverage test over this exact candidate-to-configurator map:

| Candidate kind | Manual configurator |
| --- | --- |
| `descriptives` | `configureDescriptivesFromText` |
| `reliability` | `configureReliabilityFromText` |
| `frequency_crosstab` | `configureFrequencyCrosstabFromText` |
| `correlation` | `configureCorrelationFromText` |
| `factor_pca` | `configureFactorPcaFromText` |
| `comparison` | `configureComparisonFromText` |
| `anova_oneway` | `configureAnovaOneWayFromText` |
| `anova_factorial` | `configureFactorialAnovaFromKeys` |
| `kruskal_wallis` | `configureKruskalWallisFromText` |
| `ancova` | `configureAncovaFromText` |
| `regression` | `configureRegressionFromText` |
| `logistic_regression` | `configureLogisticRegressionFromTokens` |
| `repeated_measures_anova` | `configureRepeatedMeasuresAnovaFromText` |
| `friedman` | `configureFriedmanFromText` |
| `mediation` | `configureMediationFromText` |
| `moderated_mediation` | `configureModeratedMediationFromText` |

The test must fail if a new `RecommendationKind` is added without a manual form
mapping. Also test mediation preparation by named roles, not positional list indexes.

- [ ] **Step 2: Run focused UI tests and verify RED**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/ui/test_security_privacy.py tests/ui/test_mode_action_surfaces.py tests/ui/test_guided_standard_variable_selection_flow.py tests/ui/test_qml_runtime_load.py tests/ui/test_smoke_qml.py tests/ui/test_experimental_recommendation_flow.py
```

- [ ] **Step 3: Make standard the process default and replace product wording**

Set `self._mode = "standard"`. Use exact Korean strings:

```python
"entry.guided": "실험적 후보 안내",
"work.guided": "실험적 후보",
"guide.title": "분석 후보 안내 (실험적)",
"guide.experimental_status": "검증 중인 분석 후보 · 자동 실행 안 함",
"guide.order_disclaimer": "후보 순서는 검증된 정확도나 우선순위가 아니라 현재의 결정론적 정렬 규칙입니다.",
"guide.candidate_list": "실험적 후보 목록",
"guide.current_candidate": "현재 검토 후보",
"guide.review_state": "검토 상태",
"guide.prepare_candidate": "설정 검토",
"guide.confirm_candidate": "연구 질문, 변수 역할, 표본 구조를 확인했습니다.",
"guide.run_manual": "이 설정으로 계산 실행",
"guide.no_recommendation": "현재 규칙으로 표시할 실험적 후보가 없습니다. 수동 분석을 사용할 수 있습니다.",
```

Delete production keys `guide.default_recommendation`,
`guide.other_recommendations`, `guide.level`, and `guide.run_recommended`.

- [ ] **Step 4: Implement no-selection list and preparation flow in QML**

The candidate list is visible in guided mode. Candidate click calls only
`selectRecommendationAt(index)`. `설정 검토` calls
`prepareSelectedRecommendationNow()`, enters the existing manual form, and pre-fills
fields through `preparedRecommendationField()`.

Use this final-run gate:

```qml
enabled: root.canCommitSelection
    && (!root.experimentalPreparation
        || uiController.experimentalRecommendationConfirmed)
onClicked: {
    if (root.experimentalPreparation
            && !uiController.experimentalRecommendationConfirmed) {
        return
    }
    if (root.commitSelectedIntent()) {
        uiController.rerunNow()
    }
}
```

Direct manual-selection buttons clear preparation before editing. Text edits and combo
activations call `setExperimentalRecommendationConfirmed(false)`. Changing candidate,
dataset, or mode also resets confirmation.

Extend the manual surface before deleting the shortcut:

- repeated-measures ANOVA and Friedman share a clearly labelled measures-list field;
- mediation has distinct X, mediator, Y, and optional covariate fields;
- moderated mediation has a required Model 7/14 selector plus distinct X, mediator,
  moderator, Y, and optional covariate fields;
- preparing any of these candidates pre-fills only the named fields carried by the
  immutable preparation DTO;
- no positional unpacking of mediation roles is permitted in QML or Python.

Run a focused behavioral test for every candidate kind: select, prepare, verify no
pipeline mutation, verify the intended form and prefill, invalidate confirmation on a
field change, then commit through the mapped manual configurator. Configuration-
required logistic and factorial cases stop before execution until their unresolved
choices are supplied.

After the QML caller is replaced, delete `applySelectedRecommendation`,
`runPreparedRecommendation`, and `runPreparedRecommendationNow` from the controller.

- [ ] **Step 5: Run focused UI and end-to-end tests and verify GREEN**

Run the Step 2 command plus:

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/ui/test_human_operated_qml_flow.py tests/ui/test_end_to_end_ui_flow.py tests/ui/test_qml_visual_contract.py
```

- [ ] **Step 6: Commit the explicit experimental UI**

```powershell
git add src/modori/ui/controller.py src/modori/ui/strings.py src/modori/ui/qml tests/ui
git commit -m "feat: isolate recommendations in experimental guidance"
```

---

### Task 5: Record Selection Origin and Disclose It in Reports

**Files:**
- Modify: `src/modori/ui/contracts.py`
- Modify: `src/modori/ui/controller.py`
- Modify: `src/modori/ui/pipeline_ops.py`
- Modify: `src/modori/steps/reporting.py`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `tests/ui/test_controller.py`
- Modify: `tests/ui/test_pipeline_ops.py`
- Modify: `tests/test_report_step.py`
- Modify: `tests/ui/test_experimental_recommendation_flow.py`

**Interfaces:**
- Produces: `SelectionOrigin = Literal["manual", "experimental_candidate_assisted"]`.
- Extends: `ReportExportOptions.selection_origin` with default `manual`.
- Consumes: QML call `markCurrentSelectionExperimental(bool)` from Task 4.

- [ ] **Step 1: Write RED report-disclosure and parity tests**

```python
def test_assisted_report_discloses_selection_origin(tmp_path) -> None:
    result = run_report(
        tmp_path,
        selection_origin="experimental_candidate_assisted",
        language="ko",
    )
    assert result.prose[0] == (
        "분석 방법 선택에 실험적 후보 안내가 사용되었습니다. "
        "계산 모듈의 수치 검증 범위와 추천 타당성은 별개입니다."
    )


def test_selection_origin_does_not_change_numeric_result(manual, assisted) -> None:
    assert manual.analysis_params == assisted.analysis_params
    assert manual.analysis_result == assisted.analysis_result
```

Add an unknown-origin test expecting `ValueError("Unsupported selection origin")`.

- [ ] **Step 2: Run report/controller tests and verify RED**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_report_step.py tests/ui/test_pipeline_ops.py tests/ui/test_controller.py tests/ui/test_experimental_recommendation_flow.py
```

- [ ] **Step 3: Implement local selection-origin lifecycle**

Initialize `_analysis_selection_origin = "manual"`. Every direct manual configuration
sets it to `manual`; successful candidate-assisted configuration sets it to
`experimental_candidate_assisted`. New dataset load resets it to `manual`.

```python
@Slot(bool, result=bool)
def markCurrentSelectionExperimental(self, assisted: bool) -> bool:
    self._analysis_selection_origin = (
        "experimental_candidate_assisted" if assisted else "manual"
    )
    self.stateChanged.emit()
    return True
```

In `GuideRail.qml`, after a successful candidate-assisted manual commit and before
`rerunNow()`, call:

```qml
uiController.markCurrentSelectionExperimental(root.experimentalPreparation)
```

Before report export, create options with:

```python
options = replace(options, selection_origin=self._analysis_selection_origin)
```

- [ ] **Step 4: Add fixed bilingual ReportStep disclosure**

`PipelineOperations._report_params_for_options()` writes the fixed enum value to the
report step. `ReportStep.compute()` validates it and prepends exactly one of these
fixed disclosures when assisted:

```python
SELECTION_DISCLOSURE = {
    "ko": (
        "분석 방법 선택에 실험적 후보 안내가 사용되었습니다. "
        "계산 모듈의 수치 검증 범위와 추천 타당성은 별개입니다."
    ),
    "en": (
        "An experimental analysis-candidate aid was used to select this method. "
        "Numerical validation of the calculation module and validity of the "
        "recommendation are separate."
    ),
}
```

Unknown values fail report export closed; they do not affect calculation.

- [ ] **Step 5: Run report drift and product flow tests and verify GREEN**

Run the Step 2 command plus all reporting/prose contract tests:

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests -k "report or reporting"
```

- [ ] **Step 6: Commit provenance disclosure**

```powershell
git add src/modori/ui/contracts.py src/modori/ui/controller.py src/modori/ui/pipeline_ops.py src/modori/steps/reporting.py tests
git commit -m "feat: disclose experimental selection provenance"
```

---

### Task 6: Lock Product Wording and Prepare VM Acceptance Assets

**Files:**
- Modify: production wording under `src/modori/`
- Modify: production help entries under `library/`
- Create: `scripts/check_product_wording.py`
- Create: `tests/test_product_recommendation_wording.py`
- Create: `.visual-qa/clean-win-vm-payload/experimental-candidate.csv`
- Create: `.visual-qa/clean-win-vm-payload/experimental-configuration.csv`
- Create: `.visual-qa/clean-win-vm-payload/experimental-no-candidate.csv`
- Modify: `scripts/attach_modori_payload_disk.ps1`
- Modify: `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd`
- Create: `docs/qa/experimental-recommendation-vm-runbook.md`

**Interfaces:**
- Produces: repository-wide production-text classification gate.
- Produces: three payload fixtures for candidate, configuration-required, and
  no-candidate visual paths.

- [ ] **Step 1: Write a RED production-wording scanner**

```python
from scripts.check_product_wording import product_wording_violations


def test_scanner_rejects_unvalidated_claim_in_product_path(tmp_path) -> None:
    source = tmp_path / "src" / "modori" / "ui" / "copy.py"
    source.parent.mkdir(parents=True)
    source.write_text('LABEL = "강한 추천"', encoding="utf-8")
    assert product_wording_violations(tmp_path) == (
        f"{source.relative_to(tmp_path).as_posix()}:강한 추천",
    )


def test_repository_product_text_has_no_unvalidated_claims() -> None:
    assert product_wording_violations(Path.cwd()) == ()


def test_scanner_rejects_recommendation_accuracy_percentage(tmp_path) -> None:
    source = tmp_path / "library" / "help.md"
    source.parent.mkdir(parents=True)
    source.write_text("추천 정확도 92%", encoding="utf-8")
    assert product_wording_violations(tmp_path) == (
        "library/help.md:recommendation-accuracy-percentage",
    )
```

The scanner owns this exact configuration:

```python
import re
from pathlib import Path


PRODUCT_ROOTS = (Path("src/modori"), Path("library"))
HISTORICAL_ALLOWLIST = {
    Path("src/modori/recommendation_baseline.py"),
    Path("src/modori/recommendation_benchmark.py"),
    Path("src/modori/recommendation_benchmark_io.py"),
}
BANNED = (
    "강한 추천",
    "기본 추천",
    "추천 분석 실행",
    "strong recommendation",
    "expert-level recommendation",
    "전문가 수준 추천",
)
BANNED_PATTERNS = (
    (
        "recommendation-accuracy-percentage",
        re.compile(
            r"(?:추천|recommendation)[^\n]{0,40}\d+(?:\.\d+)?\s*%",
            re.IGNORECASE,
        ),
    ),
    (
        "expert-equivalence-claim",
        re.compile(
            r"(?:전문가[^\n]{0,20}(?:동등|같은 수준)|"
            r"(?:equal|equivalent|matches)[^\n]{0,20}expert)",
            re.IGNORECASE,
        ),
    ),
)
```

Implement the scanner with deterministic ordering:

```python
TEXT_SUFFIXES = {".py", ".qml", ".json", ".yaml", ".yml", ".md"}


def product_wording_violations(repository_root: Path) -> tuple[str, ...]:
    violations: list[str] = []
    for relative_root in PRODUCT_ROOTS:
        root = repository_root / relative_root
        if not root.exists():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(repository_root)
            if relative in HISTORICAL_ALLOWLIST or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8")
            folded = text.casefold()
            for phrase in BANNED:
                if phrase.casefold() in folded:
                    violations.append(f"{relative.as_posix()}:{phrase}")
            for label, pattern in BANNED_PATTERNS:
                if pattern.search(text):
                    violations.append(f"{relative.as_posix()}:{label}")
    optional_roots = (repository_root / "README.md", repository_root / "docs" / "product")
    for optional in optional_roots:
        paths = [optional] if optional.is_file() else (
            sorted(item for item in optional.rglob("*") if item.is_file())
            if optional.is_dir()
            else []
        )
        for path in paths:
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8").casefold()
            for phrase in BANNED:
                if phrase.casefold() in text:
                    relative = path.relative_to(repository_root)
                    violations.append(f"{relative.as_posix()}:{phrase}")
            for label, pattern in BANNED_PATTERNS:
                if pattern.search(text):
                    relative = path.relative_to(repository_root)
                    violations.append(f"{relative.as_posix()}:{label}")
    return tuple(sorted(violations))
```

Also scan optional `README.md` and every file under `docs/product/` when those paths
exist. Do not scan benchmark fixtures, scorer diagnostics, migration tests, or evidence
ledgers as product copy.

- [ ] **Step 2: Run the scanner and verify RED on current claims**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_product_recommendation_wording.py
```

Expected: collection fails because `scripts.check_product_wording` does not exist.

- [ ] **Step 3: Remove remaining production claims and verify GREEN**

Implement the scanner, then change only remaining product copy. Historical benchmark
and evidence terms remain in their allowlisted files. Run the Step 2 command until the
sentinel rejection and repository-zero-violation tests both pass.

- [ ] **Step 4: Add deterministic VM fixtures and payload validation**

Create synthetic, non-PII CSVs that deterministically produce:

- at least one ordinary experimental candidate;
- one factorial or logistic candidate with `requires_configuration=True`;
- no candidate other than unusable ID/constant fields.

Use these exact fixture contents:

`experimental-candidate.csv`:

```csv
age,satisfaction
21,2
24,3
29,4
33,3
38,5
44,4
```

`experimental-configuration.csv`:

```csv
condition,site,score
A,X,11
A,X,12
A,X,13
A,Y,14
A,Y,15
A,Y,16
B,X,17
B,X,18
B,X,19
B,Y,20
B,Y,21
B,Y,22
```

`experimental-no-candidate.csv`:

```csv
id,constant
1,1
2,1
3,1
4,1
5,1
6,1
```

Update `Assert-PayloadDriveContents` and payload copy logic so all three files are
required under `Samples\experimental_recommendation\`. Add tests that verify the
script paths and fixture hashes. Change `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd` to pass its
own `%~dp0` as `-WorkspaceRoot`; otherwise a wrapper executed from this worktree would
silently copy `dist` from the main release worktree.

```bat
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -WorkspaceRoot "%~dp0." -RebuildPayload
```

- [ ] **Step 5: Write the Korean nondeveloper VM runbook**

The runbook must state that the walkthrough tests interaction, not recommendation
accuracy, and give exact clicks for:

1. direct open in standard mode;
2. explicit experimental entry;
3. no preselection and ordering disclaimer;
4. candidate selection and preparation without execution;
5. configuration-required behavior;
6. confirmation and explicit calculation;
7. direct manual parity;
8. assisted report disclosure;
9. no-candidate manual recovery;
10. normal Windows shutdown.

- [ ] **Step 6: Run fixture, payload-script, wording, and QML tests**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_product_recommendation_wording.py tests/test_clean_vm_payload_script.py tests/ui/test_experimental_recommendation_flow.py tests/ui/test_qml_runtime_load.py
```

- [ ] **Step 7: Commit wording and VM assets**

```powershell
git add src library scripts/check_product_wording.py tests .visual-qa/clean-win-vm-payload scripts/attach_modori_payload_disk.ps1 RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd docs/qa/experimental-recommendation-vm-runbook.md
git commit -m "test: lock experimental recommendation product boundary"
```

---

### Task 7: Full Verification, Package, Payload, and Evidence

**Files:**
- Modify: `docs/qa/statistics-accuracy-closure-matrix.md` only if status facts change
- Create: `docs/qa/experimental-recommendation-release-evidence.md`

**Interfaces:**
- Consumes every prior task.
- Produces fresh full-suite, slow-suite, package, artifact-hash, payload, and owner-VM
  handoff evidence.

- [ ] **Step 1: Run benchmark identity gates**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts\build_recommendation_pilot.py --check
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts\recommendation_benchmark.py validate-pack --pack-root tests\fixtures\recommendation_benchmark --output .tmp\experimental-boundary-pack.json --force
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts\recommendation_benchmark.py predict-a --pack-root tests\fixtures\recommendation_benchmark --output .tmp\experimental-boundary-baseline.jsonl --force
Get-FileHash -Algorithm SHA256 .tmp\experimental-boundary-baseline.jsonl
```

Expected: 20 cases, 19 unique data files, pinned scorer identities, and canonical
prediction hash.

- [ ] **Step 2: Run focused recommendation/UI/report gates**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -rs -p no:cacheprovider tests/test_experimental_recommendation_boundary.py tests/test_product_recommendation_wording.py tests/test_recommendation_baseline.py tests/test_recommendation_benchmark.py tests/test_recommendation_benchmark_io.py tests/ui/test_recommendations.py tests/ui/test_experimental_recommendation_flow.py tests/ui/test_qml_runtime_load.py tests/test_report_step.py tests/ui/test_pipeline_ops.py tests/test_v1_statistics_smoke.py tests/test_package_engine_smoke_script.py
```

Expected: zero failures and no required reference skip.

- [ ] **Step 3: Run the full static, statistical, package-build, and package-launch gate**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch --with-slow-stats
```

Expected: compile, ruff, bandit, launch, pip, full pytest, slow statistics, fresh
package, and packaged launch all pass. Any new skip is investigated rather than counted
as a pass.

- [ ] **Step 4: Run packaged engine and public-data smokes and hash the artifact**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts\package_engine_smoke.py
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts\package_public_data_smoke.py
Get-FileHash -Algorithm SHA256 dist\Modori\Modori.exe
```

Expected: both smokes pass; engine JSON contains all 22 V1 checks and no analysis key
drift.

- [ ] **Step 5: Record evidence and self-review the entire diff**

Write exact commands, counts, skips, hashes, and residual limitations. Search the
implementation-range diff from the pinned `aa04d43` baseline for numerical-code
changes; none are allowed. The older release comparison is informational because it
also contains the already-reviewed accuracy and factorial-ANOVA work. Run:

```powershell
git diff --check
git status --short
git diff --stat aa04d4347e065f44ef3431ffc59e31c53ca844b9...HEAD
git diff --name-only aa04d4347e065f44ef3431ffc59e31c53ca844b9...HEAD -- src/modori/steps
git diff --stat release/readiness-1-9...HEAD
```

- [ ] **Step 6: Commit release evidence**

```powershell
git add docs/qa/experimental-recommendation-release-evidence.md docs/qa/statistics-accuracy-closure-matrix.md
git commit -m "docs: record experimental recommendation release evidence"
```

- [ ] **Step 7: Rebuild and attach Payload V2 on the host**

With the VM off, run `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd` as Administrator. Require log
evidence for VM Off, payload rebuild, content validation, SCSI attachment, and `Done`.
Do not modify the guest VHD offline beyond the approved payload-disk rebuild.

- [ ] **Step 8: Hand off the exact VM walkthrough to the owner**

The owner runs the engine smoke, public-data smoke, and bounded visual walkthrough from
Task 6, returns outputs/screenshots, and shuts down Windows normally. Do not mark the
feature promoted until those results are reviewed.
