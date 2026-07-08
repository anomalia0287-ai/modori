# Descriptives Table 1 Module Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Keep the checklist updated in this file as each task finishes.

**Goal:** Ship the first Analysis Module Contract v1 pilot, `descriptives_table1`, with mechanical contract validation, replayable versioned params, module-owned recommendation eligibility, module-local result/reporting logic, and no broad refactor of existing executable analyses.

**Architecture:** Preserve the current pipeline shape: QML remains a thin shell; Python owns analysis selection, Step construction, computation, results, reporting, and recommendations. Add a new-style module spec registry beside the existing lightweight catalog, then make `descriptives_table1` the first executable module that passes the new contract harness.

**Tech Stack:** Python dataclasses, existing `modori.core.model.Step`, pandas-backed dataset frames, pytest, existing QML/Python bridge, existing `ReportStep`, existing recommendation panel.

## Global Constraints

- Preserve `C:\Users\V\Desktop\TongTong\prototypes\crystal-aurora-proof\index.html` as a design asset. Do not clean, rename, or rewrite it during this implementation.
- Do not disturb staged release evidence files unless the task explicitly edits that exact file.
- Do not replace the existing `AnalysisCapability` registry wholesale during the pilot.
- New `descriptives_table1` result DTOs must live in a module-specific file. `src/modori/results.py` may only re-export if an existing import path needs it.
- New reporting logic must live in a module-specific helper. `src/modori/steps/reporting.py` may only receive a small dispatch hook.
- New recommendation statistics logic must live in a module-owned provider. `src/modori/recommendations.py` may orchestrate providers but must not accumulate descriptives-specific heuristics.
- Parameter schemas are replay contracts. Unknown params are errors after version migration, not before it.
- Deterministic ordering is defined by `params["variables"]` for variables, metadata value-label order or normalized lexical order for observed group values, and metadata value-label order or normalized lexical order for categories.
- Chart tests validate `ChartSpec` data payloads, not pixels.
- Engineering identifiers are English. UI, report prose, recommendation titles, and user-facing validation messages are Korean-first.
- Every implementation step ends with focused tests. Full quality gate runs only after all focused tests pass.

## Task 1: Add New-Style Module Spec Registry Without Breaking Existing Catalog

- [x] Edit `src/modori/analysis_catalog.py`.

Add new enum values and dataclasses beside the existing `AnalysisCapability`. Keep current public functions working.

```python
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class RecommendationPolicy(str, Enum):
    STRONG = "strong"
    CANDIDATE = "candidate"
    CAUTION_ONLY = "caution_only"
    MANUAL_ONLY = "manual_only"
    NEVER = "never"


@dataclass(frozen=True)
class AnalysisModuleSpec:
    key: str
    label: str
    status: AnalysisStatus
    reason: str
    step_type: str | None
    result_type: str | None
    variable_roles: tuple[str, ...] = ()
    supported_measures: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    required_preprocessing: tuple[str, ...] = ()
    unsupported_cases: tuple[str, ...] = ()
    reference_sources: tuple[str, ...] = ()
    recommendation_policy: RecommendationPolicy = RecommendationPolicy.NEVER
    release_evidence_required: bool = False
    contract_tests: tuple[str, ...] = ()
    help_keys: tuple[str, ...] = ()
    external_paths: tuple[str, ...] = ()
```

Extend `AnalysisStatus` with `EXPERIMENTAL = "experimental"` if it currently only has executable/deferred states. Existing executable/deferred keys must keep their current behavior.

Add a new module spec store. Existing six lightweight items remain in `_CAPABILITIES`.

```python
_MODULE_SPECS: dict[str, AnalysisModuleSpec] = {}


def module_specs() -> tuple[AnalysisModuleSpec, ...]:
    return tuple(_MODULE_SPECS.values())


def get_module_spec(key: str) -> AnalysisModuleSpec | None:
    return _MODULE_SPECS.get(key)
```

Update `get_capability(key)` to return the existing `_CAPABILITIES` value first. If the key only exists in `_MODULE_SPECS`, derive a lightweight `AnalysisCapability` from the spec so older UI/catalog callers do not need to know the new type.

```python
spec = _MODULE_SPECS.get(key)
if spec is not None:
    return AnalysisCapability(
        key=spec.key,
        label=spec.label,
        status=spec.status,
        reason=spec.reason,
        external_paths=spec.external_paths,
    )
```

- [x] Add `tests/test_analysis_catalog_module_specs.py`.

Required tests:

```python
from modori.analysis_catalog import (
    AnalysisCapability,
    AnalysisModuleSpec,
    AnalysisStatus,
    RecommendationPolicy,
    get_capability,
    module_specs,
)


def test_existing_capabilities_still_return_lightweight_rows():
    capability = get_capability("independent_groups")
    assert isinstance(capability, AnalysisCapability)
    assert capability.key == "independent_groups"


def test_module_specs_iterable_is_available_before_pilot_registration():
    assert isinstance(module_specs(), tuple)


def test_experimental_status_and_recommendation_policy_are_stable_strings():
    assert AnalysisStatus.EXPERIMENTAL.value == "experimental"
    assert RecommendationPolicy.STRONG.value == "strong"
```

- [x] Run focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_analysis_catalog_module_specs.py -p no:cacheprovider
```

- [ ] Commit message for this task:

```text
Add new-style analysis module spec registry
```

## Task 2: Add Mechanical Contract Harness Before Registering the Pilot Module

- [x] Add `tests/test_analysis_module_contract.py`.

The harness must iterate only new-style specs from `module_specs()`. It must not fail existing lightweight catalog rows.

Use the existing Step registry. If the registry is private, expose a read-only helper in `src/modori/core/model.py` instead of inspecting private state in tests.

- [x] If needed, edit `src/modori/core/model.py` to add these module-level helpers after the `Step` class definition:

```python
def registered_step_types() -> tuple[str, ...]:
    return tuple(Step._registry.keys())


def step_class_for_type(step_type: str) -> type[Step]:
    return Step._registry[step_type]
```

Use the actual registry attribute name from `Step.register_type`.

- [x] Add harness assertions:

```python
import importlib

import pytest

from modori.analysis_catalog import AnalysisStatus, RecommendationPolicy, module_specs
from modori.core.model import registered_step_types, step_class_for_type


@pytest.mark.parametrize("spec", module_specs(), ids=lambda spec: spec.key)
def test_executable_module_specs_have_required_contract_fields(spec):
    if spec.status is not AnalysisStatus.EXECUTABLE:
        pytest.skip(f"{spec.key} is not executable")

    assert spec.step_type
    assert spec.result_type
    assert spec.variable_roles
    assert spec.supported_measures
    assert spec.unsupported_cases
    assert spec.reference_sources
    assert spec.contract_tests
    assert spec.help_keys
    assert spec.step_type in registered_step_types()


@pytest.mark.parametrize("spec", module_specs(), ids=lambda spec: spec.key)
def test_result_type_module_is_importable(spec):
    if spec.status is not AnalysisStatus.EXECUTABLE:
        pytest.skip(f"{spec.key} is not executable")

    module_name, class_name = spec.result_type.rsplit(".", 1)
    module = importlib.import_module(module_name)
    assert getattr(module, class_name)


@pytest.mark.parametrize("spec", module_specs(), ids=lambda spec: spec.key)
def test_recommended_modules_have_eligibility_provider(spec):
    if spec.recommendation_policy in {RecommendationPolicy.NEVER, RecommendationPolicy.MANUAL_ONLY}:
        pytest.skip(f"{spec.key} does not require recommendation eligibility")

    provider_module = importlib.import_module(f"modori.{spec.key}_recommendation")
    provider = getattr(provider_module, "eligibility_provider")()
    assert provider.module_key == spec.key
    assert callable(provider.candidates)
```

If the final provider path is `modori.recommendation_providers.descriptives_table1`, encode that exact package in a spec field named `recommendation_provider`. Prefer an explicit field over deriving a fragile import path.

- [x] Add schema contract tests in the same file:

```python
@pytest.mark.parametrize("spec", module_specs(), ids=lambda spec: spec.key)
def test_executable_steps_expose_schema_migration_contract(spec):
    if spec.status is not AnalysisStatus.EXECUTABLE:
        pytest.skip(f"{spec.key} is not executable")

    step_cls = step_class_for_type(spec.step_type)
    assert isinstance(step_cls.CURRENT_SCHEMA_VERSION, int)
    assert step_cls.CURRENT_SCHEMA_VERSION >= 1
    assert callable(step_cls.migrate_params)
    assert callable(step_cls.validate_params)
```

If `step_class_for_type` does not exist, add it beside `registered_step_types()` using the existing registry.

- [x] Run focused tests. At this point they may pass with zero specs. That is acceptable because Task 3 registers the first spec.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_analysis_module_contract.py -p no:cacheprovider
```

- [ ] Commit message for this task:

```text
Add analysis module contract harness
```

## Task 3: Implement `descriptives_table1` Result DTO and Step

- [x] Add `src/modori/descriptives_table1_results.py`.

Define frozen dataclasses with JSON-friendly primitive fields. Use `None` for unavailable statistics. Do not store pandas objects.

```python
from __future__ import annotations

from dataclasses import dataclass, field

from modori.results import ChartSpec


@dataclass(frozen=True)
class DescriptiveCategoryRow:
    value: str
    label: str
    count: int
    percent: float


@dataclass(frozen=True)
class DescriptiveVariableSummary:
    key: str
    label: str
    measure: str
    n_obs: int
    n_missing: int
    mean: float | None = None
    sd: float | None = None
    median: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    categories: tuple[DescriptiveCategoryRow, ...] = ()


@dataclass(frozen=True)
class DescriptiveGroupSummary:
    group_value: str
    group_label: str
    n_total: int
    variables: tuple[DescriptiveVariableSummary, ...]


@dataclass(frozen=True)
class DescriptivesTableResult:
    analysis_key: str
    title_ko: str
    variables: tuple[str, ...]
    group: str | None
    n_total: int
    summaries: tuple[DescriptiveVariableSummary, ...]
    grouped_summaries: tuple[DescriptiveGroupSummary, ...] = ()
    warnings_ko: tuple[str, ...] = ()
    notes_ko: tuple[str, ...] = ()
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
```

Use the current `ChartSpec` import path: `modori.results.ChartSpec`.

- [x] Add `src/modori/steps/descriptives_table1.py`.

Define the step and register it with the repository's current registry API:

```python
@dataclass(frozen=True)
class DescriptivesTableStep(Step):
    step_type = "stats.descriptives_table1"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx, params)
        return StepResult(analysis=result)

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        keys = set(params["variables"])
        if params["group"] is not None:
            keys.add(params["group"])
        return keys

    def writes(self) -> set[str]:
        return {self.id}


Step.register_type(DescriptivesTableStep.step_type, DescriptivesTableStep)
```

Use `ctx`, not `context`, inside `compute()`. The `_compute_result()` helper accepts `PipelineContext` and validated params.

Implement these class methods:

```python
@classmethod
def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
    version = params.get("schema_version")
    if version is None:
        raise ValueError("descriptives_table1 params require schema_version")
    if not isinstance(version, int):
        raise ValueError("schema_version must be an integer")
    if version > cls.CURRENT_SCHEMA_VERSION:
        raise ValueError("descriptives_table1 params use a newer schema_version")
    if version == 1:
        return params
    raise ValueError(f"unsupported descriptives_table1 schema_version: {version}")


@classmethod
def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
    allowed = {"schema_version", "variables", "group", "include_missing_counts", "language"}
    unknown = set(params) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"unknown descriptives_table1 params: {names}")
    if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
        raise ValueError("descriptives_table1 params were not migrated to the current schema")
    variables = params.get("variables")
    if not isinstance(variables, list) or not variables or not all(isinstance(v, str) for v in variables):
        raise ValueError("variables must be a non-empty list of variable keys")
    group = params.get("group")
    if group is not None and not isinstance(group, str):
        raise ValueError("group must be null or a variable key")
    include_missing_counts = params.get("include_missing_counts", True)
    if not isinstance(include_missing_counts, bool):
        raise ValueError("include_missing_counts must be boolean")
    language = params.get("language", "ko")
    if language not in {"ko", "en"}:
        raise ValueError("language must be ko or en")
    return {
        "schema_version": cls.CURRENT_SCHEMA_VERSION,
        "variables": variables,
        "group": group,
        "include_missing_counts": include_missing_counts,
        "language": language,
    }
```

Computation rules:

- `n_total` is the number of rows in the dataset frame before variable-level missing filtering.
- Numeric summaries are emitted for scale variables. Calculate `mean`, `median`, `minimum`, `maximum` over non-missing numeric values. Calculate sample standard deviation with `ddof=1`; emit `None` when `n_obs < 2`.
- Nominal and ordinal summaries emit category rows over non-missing values. `percent` denominator is non-missing `n_obs`. Missing count remains separate.
- Variables appear exactly in `params["variables"]` order.
- Grouped output includes one `DescriptiveGroupSummary` per observed non-missing group value. Group values use metadata value-label order when labels exist, otherwise normalized lexical order.
- Category labels use metadata value labels when available, otherwise `str(value)`.
- Unsupported variable keys, unsupported group keys, duplicate variable keys, and empty datasets raise Korean-first validation errors.
- Warnings contain Korean messages for skipped unsupported variables only if the module chooses skip behavior. Prefer hard validation for the pilot to keep replay deterministic.

- [x] Register the module spec in `src/modori/analysis_catalog.py` only after `DescriptivesTableStep` and result DTO import cleanly.

```python
_MODULE_SPECS["descriptives_table1"] = AnalysisModuleSpec(
    key="descriptives_table1",
    label="기술통계 표 1",
    status=AnalysisStatus.EXECUTABLE,
    reason="척도형 변수의 요약 통계와 범주형 변수의 빈도표를 재현 가능한 표로 생성합니다.",
    step_type="stats.descriptives_table1",
    result_type="modori.descriptives_table1_results.DescriptivesTableResult",
    variable_roles=("variables", "group"),
    supported_measures={
        "variables": ("scale", "ordinal", "nominal"),
        "group": ("ordinal", "nominal"),
    },
    required_preprocessing=(),
    unsupported_cases=(
        "weights",
        "complex_samples",
        "multiple_imputation",
        "standardized_mean_difference",
        "baseline_imbalance_claims",
        "causal_or_treatment_language",
    ),
    reference_sources=("pandas describe/crosstab parity tests",),
    recommendation_policy=RecommendationPolicy.STRONG,
    release_evidence_required=True,
    contract_tests=(
        "tests/test_analysis_module_contract.py",
        "tests/test_descriptives_table1_step.py",
    ),
    help_keys=("analysis.descriptives_table1",),
)
```

If importing `DescriptivesTableStep` in `analysis_catalog.py` creates a cycle, put registration in a module that is imported by the application startup and by the contract harness. The harness must import that registration module before iterating specs.

- [x] Add `tests/test_descriptives_table1_step.py`.

Required test cases:

```python
def test_current_schema_rejects_unknown_params_after_migration():
    params = {
        "schema_version": 1,
        "variables": ["age"],
        "group": None,
        "include_missing_counts": True,
        "language": "ko",
        "extra": "bad",
    }
    with pytest.raises(ValueError, match="unknown descriptives_table1 params"):
        DescriptivesTableStep.validate_params(params)


def test_newer_schema_version_is_rejected_explicitly():
    with pytest.raises(ValueError, match="newer schema_version"):
        DescriptivesTableStep.migrate_params({"schema_version": 999, "variables": ["age"]})
```

Add numeric parity test against pandas:

```python
def test_scale_summary_matches_pandas_sample_sd(dataset_factory):
    dataset = dataset_factory(
        rows=[{"age": 20}, {"age": 24}, {"age": None}, {"age": 28}],
        measures={"age": "scale"},
        labels={"age": "Age"},
    )
    result = run_step(dataset, {"schema_version": 1, "variables": ["age"], "group": None, "include_missing_counts": True, "language": "ko"})

    summary = result.summaries[0]
    assert summary.n_obs == 3
    assert summary.n_missing == 1
    assert summary.mean == pytest.approx(24.0)
    assert summary.sd == pytest.approx(pd.Series([20, 24, 28]).std(ddof=1))
    assert summary.median == pytest.approx(24.0)
    assert summary.minimum == pytest.approx(20.0)
    assert summary.maximum == pytest.approx(28.0)
```

Add categorical percentage and deterministic order tests:

```python
def test_nominal_summary_uses_non_missing_denominator_and_label_order(dataset_factory):
    dataset = dataset_factory(
        rows=[{"gender": "F"}, {"gender": "M"}, {"gender": "F"}, {"gender": None}],
        measures={"gender": "nominal"},
        labels={"gender": "Gender"},
        value_labels={"gender": {"F": "여성", "M": "남성"}},
    )
    result = run_step(dataset, {"schema_version": 1, "variables": ["gender"], "group": None, "include_missing_counts": True, "language": "ko"})

    summary = result.summaries[0]
    assert summary.n_obs == 3
    assert summary.n_missing == 1
    assert [(row.value, row.label, row.count, row.percent) for row in summary.categories] == [
        ("F", "여성", 2, pytest.approx(66.6666667)),
        ("M", "남성", 1, pytest.approx(33.3333333)),
    ]
```

Add grouped output test:

```python
def test_grouped_output_preserves_variable_order_and_group_order(dataset_factory):
    dataset = dataset_factory(
        rows=[
            {"group": "B", "age": 20, "gender": "F"},
            {"group": "A", "age": 30, "gender": "M"},
            {"group": "B", "age": 40, "gender": "F"},
        ],
        measures={"group": "nominal", "age": "scale", "gender": "nominal"},
        value_labels={"group": {"A": "A집단", "B": "B집단"}},
    )
    result = run_step(dataset, {"schema_version": 1, "variables": ["gender", "age"], "group": "group", "include_missing_counts": True, "language": "ko"})

    assert [group.group_value for group in result.grouped_summaries] == ["A", "B"]
    assert [[summary.key for summary in group.variables] for group in result.grouped_summaries] == [["gender", "age"], ["gender", "age"]]
```

Use existing dataset/step test helpers if the repository already has them. If there is no helper, create local helpers inside the test file rather than adding shared test infrastructure.

- [x] Run focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_descriptives_table1_step.py tests\test_analysis_module_contract.py -p no:cacheprovider
```

- [ ] Commit message for this task:

```text
Implement descriptives table step contract
```

## Task 4: Add Module-Local Reporting and Minimal Central Dispatch

- [x] Add `src/modori/descriptives_table1_reporting.py`.

Functions:

```python
from modori.descriptives_table1_results import DescriptivesTableResult


def table_for_descriptives_table1(result: DescriptivesTableResult) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for summary in result.summaries:
        rows.extend(_summary_rows(summary, group_label=None))
    return rows


def prose_for_descriptives_table1(result: DescriptivesTableResult, language: str = "ko") -> str:
    variable_count = len(result.variables)
    if language == "en":
        return f"Descriptives Table 1 summarizes {variable_count} variables across {result.n_total} cases."
    return f"기술통계 표 1은 총 {result.n_total}개 사례와 {variable_count}개 변수의 요약을 제공합니다."
```

Each row dict must use these keys: `variable`, `n`, `missing`, `mean`, `sd`, `median`, `min`, `max`, `category`, `count`, `percent`. For grouped output, prepend `group` to each row dict.

Reporting rules:

- First header row for ungrouped result:

```text
변수 | N | 결측 | 평균 | 표준편차 | 중앙값 | 최솟값 | 최댓값 | 범주 | 빈도 | %
```

- Scale variables fill numeric columns and leave category columns blank.
- Nominal/ordinal variables fill category rows and leave numeric statistic columns blank.
- Grouped result includes a leading `집단` column and one block per group.
- Percentages are formatted with one decimal place.
- Missing numeric values display as an empty string, not `"None"` or `"nan"`.
- Prose is Korean-first and descriptive only. It must not contain causal wording, treatment/control wording, or balance claims.

- [x] Edit `src/modori/steps/reporting.py`.

Add a small dispatch branch only:

```python
from modori.descriptives_table1_reporting import (
    prose_for_descriptives_table1,
    table_for_descriptives_table1,
)
from modori.descriptives_table1_results import DescriptivesTableResult


def table_for(result):
    if isinstance(result, DescriptivesTableResult):
        return table_for_descriptives_table1(result)
    return _existing_table_for(result)


def prose_for(result, language: str = "ko"):
    if isinstance(result, DescriptivesTableResult):
        return prose_for_descriptives_table1(result, language=language)
    return _existing_prose_for(result)
```

Keep the existing `prose_for(result, language="ko")` signature and the existing `table_for(result) -> list[dict[str, str]]` return type. Use the current fallback code in `reporting.py`; do not introduce `_existing_table_for` or `_existing_prose_for` unless the existing function body is first extracted without behavior changes. If `reporting.py` already has a registry pattern, register the two functions there and avoid adding `isinstance` branches.

- [x] Add `tests/test_descriptives_table1_reporting.py`.

Required tests:

```python
def test_table_formats_scale_and_nominal_rows_without_none_or_nan():
    result = DescriptivesTableResult(
        analysis_key="descriptives_table1",
        title_ko="기술통계 표 1",
        variables=("age", "gender"),
        group=None,
        n_total=4,
        summaries=(
            DescriptiveVariableSummary(
                key="age",
                label="나이",
                measure="scale",
                n_obs=3,
                n_missing=1,
                mean=24.0,
                sd=4.0,
                median=24.0,
                minimum=20.0,
                maximum=28.0,
            ),
            DescriptiveVariableSummary(
                key="gender",
                label="성별",
                measure="nominal",
                n_obs=3,
                n_missing=1,
                categories=(
                    DescriptiveCategoryRow(value="F", label="여성", count=2, percent=66.6666667),
                    DescriptiveCategoryRow(value="M", label="남성", count=1, percent=33.3333333),
                ),
            ),
        ),
    )
    table = table_for_descriptives_table1(result)
    flat = "\n".join("\t".join(row.values()) for row in table)
    assert "None" not in flat
    assert "nan" not in flat.lower()
    assert "66.7" in flat


def test_prose_is_korean_first_and_does_not_make_causal_claims():
    result = DescriptivesTableResult(
        analysis_key="descriptives_table1",
        title_ko="기술통계 표 1",
        variables=("age",),
        group=None,
        n_total=2,
        summaries=(
            DescriptiveVariableSummary(
                key="age",
                label="나이",
                measure="scale",
                n_obs=2,
                n_missing=0,
                mean=25.0,
                sd=7.0710678118654755,
                median=25.0,
                minimum=20.0,
                maximum=30.0,
            ),
        ),
    )
    prose = prose_for_descriptives_table1(result)
    assert "기술통계" in prose
    forbidden = ("원인", "효과", "처치", "통제집단", "실험집단", "baseline", "balance")
    assert not any(term in prose for term in forbidden)
```

- [x] Extend existing reporting dispatch tests if they exist:

```python
from modori.steps.reporting import prose_for, table_for


def test_reporting_dispatch_accepts_descriptives_result():
    result = DescriptivesTableResult(
        analysis_key="descriptives_table1",
        title_ko="기술통계 표 1",
        variables=("age",),
        group=None,
        n_total=1,
        summaries=(
            DescriptiveVariableSummary(
                key="age",
                label="나이",
                measure="scale",
                n_obs=1,
                n_missing=0,
                mean=20.0,
                sd=None,
                median=20.0,
                minimum=20.0,
                maximum=20.0,
            ),
        ),
    )
    assert table_for(result)
    assert prose_for(result)
```

- [x] Run focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_descriptives_table1_reporting.py tests\test_descriptives_table1_step.py tests\test_analysis_module_contract.py -p no:cacheprovider
```

- [ ] Commit message for this task:

```text
Add descriptives table reporting
```

## Task 5: Add Module-Owned Recommendation Eligibility and Orchestration Hook

- [x] Add `src/modori/descriptives_table1_recommendation.py`.

Provider contract:

```python
from dataclasses import dataclass

from modori.recommendations import RecommendationCandidate


@dataclass(frozen=True)
class DescriptivesTable1EligibilityProvider:
    module_key: str = "descriptives_table1"

    def candidates(self, dataset, *, active_analysis: bool = False) -> list[RecommendationCandidate]:
        if active_analysis:
            return []
        frame_for_compute = getattr(dataset, "frame_for_compute", None)
        frame = frame_for_compute() if callable(frame_for_compute) else getattr(dataset, "df", None)
        if frame is None:
            return []
        variable_keys = self._usable_variable_keys(dataset)
        if frame.empty or not variable_keys:
            return []
        group_key = self._first_plausible_group_key(dataset, variable_keys) or ""
        level = "강한 추천"
        reason = "가져온 데이터셋에 요약 가능한 변수가 있어 기술통계 표를 먼저 생성할 수 있습니다."
        return [
            RecommendationCandidate(
                candidate_id="descriptives_table1.default",
                kind="descriptives",
                title_ko="기술통계 표 1",
                level=level,
                reason_ko=reason,
                variable_keys=variable_keys,
                group_key=group_key,
            )
        ]


def eligibility_provider() -> DescriptivesTable1EligibilityProvider:
    return DescriptivesTable1EligibilityProvider()
```

Adjust `dataset.frame()` to the actual current dataset API. Keep dataset-specific inspection in this provider.

Eligibility rules:

- Strong recommendation when a dataset is imported, there is at least one usable scale/ordinal/nominal variable, and no active analysis is being edited.
- Candidate recommendation may include a plausible grouping variable when a nominal/ordinal variable has between 2 and 12 observed non-missing values. Store no grouping variable as an empty string to match the existing `RecommendationCandidate.group_key` field.
- Never infer treatment/control roles.
- Exclude group variable from `variable_keys`.
- Limit default variable list to the first 20 usable variables in dataset order to avoid accidental huge reports. The user can manually add more variables in later UI work.

- [x] Edit `src/modori/recommendations.py`.

Keep existing recommendation behavior. Add:

```python
RecommendationKind = Literal["descriptives", "reliability", "comparison", "regression"]
```

Add a neutral field to `RecommendationCandidate`:

```python
variable_keys: list[str] = field(default_factory=list)
```

Existing candidates may leave it empty.

Add provider orchestration:

```python
from modori.descriptives_table1_recommendation import eligibility_provider as descriptives_provider


class RecommendationService:
    def __init__(self, providers=None):
        self._providers = tuple(providers or (descriptives_provider(),))

    def recommend(self, dataset, *, active_analysis: bool = False):
        frame = self._frame_for_recommendation(dataset)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return self._empty_state()
        variables = self._variables_for_recommendation(dataset)

        candidates: list[RecommendationCandidate] = []
        for provider in self._providers:
            candidates.extend(provider.candidates(dataset, active_analysis=active_analysis))

        usable = [
            str(column)
            for column in frame.columns
            if self._is_usable_column(frame[column], str(column))
        ]
        numeric = [
            column for column in usable if pd.api.types.is_numeric_dtype(frame[column])
        ]
        item_groups = self._item_groups(frame, numeric)
        candidates.extend(self._reliability_candidates(item_groups))
        candidates.extend(self._comparison_candidates(frame, numeric, usable))
        candidates.extend(self._caution_candidates(frame, numeric, variables))
        candidates = self._rank(candidates)

        default = self._default_candidate(candidates)
        return RecommendationState(
            candidates=candidates,
            default_candidate=default,
            selected_candidate=default,
            message_ko=self._message(candidates, default),
        )
```

Preserve the existing empty-state handling, legacy candidate creation, ranking, default selection, and message behavior. Extracting legacy code into a private helper is allowed only if tests prove output ordering and messages are unchanged.

Update `_rank()` to include the new kind:

```python
kind_rank = {"descriptives": 0, "reliability": 1, "comparison": 2, "regression": 3}
```

- [ ] Register provider path in the module spec if Task 2 used an explicit field:

```python
recommendation_provider="modori.descriptives_table1_recommendation.eligibility_provider"
```

- [x] Add `tests/test_descriptives_table1_recommendation.py`.

Required tests:

```python
def test_provider_recommends_descriptives_for_imported_dataset_with_usable_variable(dataset_factory):
    dataset = dataset_factory(rows=[{"age": 20}, {"age": 30}], measures={"age": "scale"})
    candidate = eligibility_provider().candidates(dataset)[0]
    assert candidate.kind == "descriptives"
    assert candidate.variable_keys == ["age"]
    assert candidate.level == "강한 추천"


def test_provider_returns_no_candidate_when_active_analysis_is_present(dataset_factory):
    dataset = dataset_factory(rows=[{"age": 20}], measures={"age": "scale"})
    assert eligibility_provider().candidates(dataset, active_analysis=True) == []


def test_provider_uses_plausible_group_without_treatment_language(dataset_factory):
    dataset = dataset_factory(
        rows=[{"group": "A", "age": 20}, {"group": "B", "age": 30}],
        measures={"group": "nominal", "age": "scale"},
    )
    candidate = eligibility_provider().candidates(dataset)[0]
    assert candidate.group_key == "group"
    assert "처치" not in candidate.reason_ko
    assert "통제" not in candidate.reason_ko
```

Add orchestration regression test:

```python
def test_recommendation_service_includes_descriptives_without_removing_legacy_candidates(dataset_factory):
    dataset = dataset_factory(
        rows=[
            {"stress_1": 1, "stress_2": 2, "stress_3": 3, "age": 20},
            {"stress_1": 2, "stress_2": 3, "stress_3": 4, "age": 30},
        ],
        measures={"stress_1": "scale", "stress_2": "scale", "stress_3": "scale", "age": "scale"},
    )
    result = RecommendationService().recommend(dataset)
    kinds = [candidate.kind for candidate in result.candidates]
    assert "descriptives" in kinds
```

Use the actual return type of `RecommendationService.recommend()`.

- [x] Run focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_descriptives_table1_recommendation.py tests\test_analysis_module_contract.py -p no:cacheprovider
```

- [ ] Commit message for this task:

```text
Add descriptives recommendation provider
```

## Task 6: Wire Recommendation Execution Into Existing Python UI Bridge

- [x] Inspect these files before editing:

```text
src/modori/ui/recommendation_controller.py
src/modori/ui/controller.py
src/modori/ui/analysis_editor.py
src/modori/ui/commands.py
src/modori/ui/pipeline_ops.py
```

- [x] Edit `src/modori/ui/commands.py`.

Add a builder method that constructs canonical params:

```python
def descriptives_table1(
    self,
    variables: list[str],
    group: str,
    *,
    include_missing_counts: bool = True,
    language: str = "ko",
) -> PipelineStepCommand:
    if not variables:
        raise PatchValidationError(
            "기술통계 표에는 하나 이상의 변수가 필요합니다.",
            error_code="invalid_selection",
        )
    variable_keys = [str(variable).strip() for variable in variables if str(variable).strip()]
    if len(variable_keys) != len(variables):
        raise PatchValidationError(
            "기술통계 변수 이름은 비어 있을 수 없습니다.",
            error_code="invalid_selection",
        )
    if len(set(variable_keys)) != len(variable_keys):
        raise PatchValidationError(
            "기술통계 변수는 중복될 수 없습니다.",
            error_code="invalid_selection",
        )
    group_key = str(group).strip()
    known_keys = variable_keys + ([group_key] if group_key else [])
    self._require_known_variables(known_keys)
    step_type = "stats.descriptives_table1"
    step = self._step_by_type(step_type)
    return PipelineStepCommand(
        step_id="descriptives_table1" if step is None else str(step.id),
        step_type=step_type,
        params={
            "schema_version": 1,
            "variables": variable_keys,
            "group": group_key or None,
            "include_missing_counts": include_missing_counts,
            "language": language,
        },
        message_ko="기술통계 표 변수가 변경되었습니다.",
    )
```

Use the existing `PipelineStepCommand` dataclass and field names.

- [x] Edit `src/modori/ui/analysis_editor.py`.

Add a method that delegates to the command builder:

```python
def descriptives(
    self,
    variables: list[str],
    group_key: str,
    *,
    pipeline_version: int,
) -> CommandResult:
    return self._apply(
        lambda builder: builder.descriptives_table1(variables, group_key),
        pipeline_version=pipeline_version,
    )
```

Use the existing `_apply()` path so stale-pipeline handling and rollback behavior remain unchanged.

- [x] Edit `src/modori/ui/pipeline_ops.py`.

Import and create `DescriptivesTableStep` when `step_type` is `"stats.descriptives_table1"`.

```python
if step_type == "stats.descriptives_table1":
    return DescriptivesTableStep(
        id=step_id,
        title="Descriptives Table 1",
        params=dict(params),
    )
```

Update `_managed_step_types()` to include `"stats.descriptives_table1"`. Update `_analysis_result_key()` so the report step includes `"descriptives_table1"` when it reports this step:

```python
if step_type == "stats.descriptives_table1":
    return self._step_id(analysis_step)
```

The existing `replace_managed_analysis_steps()` path then appends the analysis step and `ReportStep`.

- [x] Edit `src/modori/ui/controller.py`.

Add a slot used by recommendation execution:

```python
def configureDescriptivesSelection(self, variables: list[str], group_key: str = "") -> CommandResult:
    variable_keys = [str(value) for value in variables]
    result = self._services.analysis_editor.descriptives(
        variable_keys,
        str(group_key or ""),
        pipeline_version=self._pipeline_state.pipeline_version,
    )
    return self._apply_step_edit_result(result)


@Slot("QVariantList", str, result=bool)
def configureDescriptivesFromList(self, variables, group_key: str = "") -> bool:
    return self.configureDescriptivesSelection(list(variables), group_key).ok
```

Use the current Qt binding import and return convention in this file.

- [x] Edit `src/modori/ui/recommendation_controller.py`.

Add branch:

```python
if candidate.kind == "descriptives":
    return self.configureDescriptivesSelection(candidate.variable_keys, candidate.group_key)
```

Leave legacy branches unchanged.

- [x] Add UI-focused tests in the existing UI test file that already covers recommendation execution. If no such file exists, add `tests/ui/test_descriptives_recommendation_execution.py`.

Required assertions:

```python
def test_apply_descriptives_recommendation_builds_versioned_params(controller_factory, dataset_factory):
    dataset = dataset_factory(rows=[{"age": 20}, {"age": 30}], measures={"age": "scale"})
    controller = controller_factory(dataset)
    recommendation = RecommendationCandidate(
        candidate_id="descriptives_table1.default",
        kind="descriptives",
        title_ko="기술통계 표 1",
        level="강한 추천",
        reason_ko="가져온 데이터셋에 요약 가능한 변수가 있어 기술통계 표를 먼저 생성할 수 있습니다.",
        variable_keys=["age"],
        group_key="",
    )

    controller._recommendation_state = RecommendationState(
        candidates=[recommendation],
        default_candidate=recommendation,
        selected_candidate=recommendation,
    )
    assert controller.applySelectedRecommendation().ok
    step = next(step for step in controller.pipeline.steps if step.step_type == "stats.descriptives_table1")
    assert step.step_type == "stats.descriptives_table1"
    assert step.params == {
        "schema_version": 1,
        "variables": ["age"],
        "group": None,
        "include_missing_counts": True,
        "language": "ko",
    }
```

Use actual controller and pipeline accessors. If direct controller construction is expensive, test `AnalysisSelectionCommandBuilder` and `PipelineOperations` separately.

- [x] Run focused UI tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui -k "recommendation or descriptives" -p no:cacheprovider
```

- [ ] Commit message for this task:

```text
Wire descriptives recommendation execution
```

## Task 7: Add Help-Key Coverage and Release Evidence

- [x] Find the existing help/knowledge source file by searching for current analysis help keys:

```powershell
rg "analysis\." src tests docs
```

- [x] Add `analysis.descriptives_table1` to the existing help source.

Content requirements:

- Korean title: `기술통계 표 1`
- Define when to use it.
- State that it reports summaries only and does not test differences or causal effects.
- State missing value denominator rules.
- State unsupported cases: weights, complex samples, multiple imputation, SMD, baseline imbalance claims.

- [x] Extend the contract harness help-key assertion to resolve help keys through the real help lookup function. If no help lookup function exists, add a small public lookup that returns `None` for unknown keys and the entry for known keys.

- [x] Add release evidence doc `docs/qa/descriptives-table1-contract.md`.

Include:

```markdown
# Descriptives Table 1 Contract Evidence

Date: 2026-07-07

## Scope

- Scale summaries: N, missing N, mean, sample SD, median, min, max.
- Nominal/ordinal summaries: N, missing N, category count, category percent.
- Optional nominal/ordinal grouping variable.

## Explicitly Unsupported

- Weights
- Complex samples
- Multiple imputation
- Standardized mean differences
- Baseline imbalance claims
- Causal, treatment, or control-group interpretation

## Verification

- `tests/test_analysis_module_contract.py`
- `tests/test_descriptives_table1_step.py`
- `tests/test_descriptives_table1_reporting.py`
- `tests/test_descriptives_table1_recommendation.py`
- UI recommendation execution test

## Determinism

- Variable order follows `params["variables"]`.
- Group order follows metadata value labels, then normalized lexical order.
- Category order follows metadata value labels, then normalized lexical order.

## Replay

- Params require `schema_version: 1`.
- Newer schema versions are rejected.
- Unknown params are rejected after migration.
```

- [x] Add tests for help-key resolution:

```python
def test_descriptives_help_key_resolves():
    assert help_for("analysis.descriptives_table1") is not None
```

Use the real helper name.

- [x] Run focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_analysis_module_contract.py -p no:cacheprovider
```

- [ ] Commit message for this task:

```text
Document descriptives contract evidence
```

## Task 8: Final Verification and Cleanliness Audit

- [x] Run the focused suite first:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_analysis_catalog_module_specs.py tests\test_analysis_module_contract.py tests\test_descriptives_table1_step.py tests\test_descriptives_table1_reporting.py tests\test_descriptives_table1_recommendation.py -p no:cacheprovider
```

- [x] Run the full quality gate:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py
```

Expected result:

```text
[quality-gate] all checks passed
```

- [x] After tests finish, run status checks last and read-only:

```powershell
git status --short
```

```powershell
Get-ChildItem -Force
```

- [x] If tests created cache directories such as `matplotlib-cache`, inspect the path and remove only that generated cache after confirming it is under `C:\Users\V\Desktop\TongTong`.

- [x] Confirm no generated cache or build directory remains unclassified. Do not remove `.visual-qa`, `.worktrees`, `.tools`, `.venv`, `dist`, `.stress-matrix`, `.tmp`, `.test-tmp`, or admin logs during this feature implementation.

- [ ] Final implementation summary must include:

- Files changed.
- Focused tests run.
- Full quality gate result.
- Any files left unstaged because they are existing release evidence/design assets.

- [ ] Commit message for final verification-only changes, if documentation changed during verification:

```text
Record descriptives verification evidence
```

## Parallel Session Boundaries

The following work can be delegated only after Task 1 and Task 2 land because the contract harness defines the gate:

- Step/result implementation: `src/modori/steps/descriptives_table1.py`, `src/modori/descriptives_table1_results.py`, `tests/test_descriptives_table1_step.py`
- Reporting: `src/modori/descriptives_table1_reporting.py`, small dispatch edit in `src/modori/steps/reporting.py`, `tests/test_descriptives_table1_reporting.py`
- Recommendation: `src/modori/descriptives_table1_recommendation.py`, provider orchestration in `src/modori/recommendations.py`, `tests/test_descriptives_table1_recommendation.py`
- UI bridge: `src/modori/ui/*.py` listed in Task 6 and UI tests

Do not run parallel sessions that edit the same shared files at the same time:

- `src/modori/analysis_catalog.py`
- `src/modori/recommendations.py`
- `src/modori/steps/reporting.py`
- `src/modori/ui/controller.py`
- `src/modori/ui/pipeline_ops.py`

## Acceptance Criteria

- `descriptives_table1` is registered as the first executable new-style `AnalysisModuleSpec`.
- Contract harness fails if an executable new-style module lacks schema migration, result DTO importability, help-key resolution, test markers, or recommendation eligibility provider.
- `DescriptivesTableStep` rejects missing/newer schema versions and unknown params after migration.
- Numeric and categorical summaries match pinned pandas/reference expectations.
- Reporting produces Korean-first descriptive output without causal/treatment/control claims.
- Recommendation eligibility is module-owned and can recommend the module for an imported dataset with at least one usable variable.
- Recommendation execution creates a replayable `stats.descriptives_table1` step with schema-versioned params.
- Full quality gate passes.
