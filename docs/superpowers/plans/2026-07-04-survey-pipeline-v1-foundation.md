# Survey Pipeline V1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first safe implementation slice for Survey Pipeline V1: explicit executable/deferred analysis catalog, case-count reporting contracts, Welch-first independent comparisons, two-time paired comparisons, and deterministic report wording gates.

**Architecture:** Keep the existing `Step`/`Pipeline` architecture. Add narrow engine-owned result fields and new deterministic steps; the UI remains a thin shell and receives only Step parameters and result DTOs. Analyses not supported by V1 are represented in a capability catalog as deferred, not exposed as partial executable features.

**Tech Stack:** Python 3.11+, pandas, scipy, pingouin, statsmodels where already used, pytest.

---

## Scope Check

The approved design in `docs/superpowers/specs/2026-07-04-survey-pipeline-v1-design.md` covers multiple subsystems:

- data management and replayable preparation
- descriptives/Table 1
- reliability and item diagnostics
- factor/PCA
- independent and paired comparisons
- ANOVA/ANCOVA
- OLS regression safety
- report generation and export

Implementing all of V1 as one plan would invite scope creep. This plan covers the foundation and first comparison slice only. Follow-on plans should cover:

1. `survey-pipeline-v1-descriptives-table1`
2. `survey-pipeline-v1-factor-pca`
3. `survey-pipeline-v1-anova-ancova`
4. `survey-pipeline-v1-regression-interactions`
5. `survey-pipeline-v1-report-export-qa`

This plan must leave unsupported analyses fail-closed through the catalog and must not add mediation, repeated-measures ANOVA, Friedman, mixed models, MANOVA, or AI/SLM runtime paths.

## File Structure

- Create `src/modori/analysis_catalog.py`: deterministic capability registry for executable and deferred analyses.
- Create `tests/test_analysis_catalog.py`: verifies V1 does not expose deferred advanced analyses as executable.
- Modify `src/modori/results.py`: extend `ComparisonResult` with total/excluded N and optional related-samples metadata.
- Modify `src/modori/steps/statistics.py`: make independent comparisons Welch-first and add `PairedComparisonStep`.
- Modify `src/modori/steps/__init__.py`: export and register `PairedComparisonStep`.
- Modify `src/modori/steps/reporting.py`: include N/excluded N and paired/Wilcoxon wording in deterministic prose/tables.
- Modify `tests/test_compare_groups_step.py`: update Welch-first expectations and N reporting assertions.
- Create `tests/test_paired_comparison_step.py`: paired t/Wilcoxon routing, exclusions, validation, pipeline writes.
- Modify `tests/test_reporting_prose_contracts.py`: lock deterministic Korean/English prose for Welch, paired t, Wilcoxon, and excluded N.

---

### Task 1: Add Deterministic Analysis Capability Catalog

**Files:**
- Create: `src/modori/analysis_catalog.py`
- Create: `tests/test_analysis_catalog.py`

- [ ] **Step 1: Write failing catalog tests**

Create `tests/test_analysis_catalog.py`:

```python
import pytest

from modori.analysis_catalog import (
    AnalysisStatus,
    get_capability,
    require_executable,
    survey_v1_executable_keys,
)


def test_survey_v1_exposes_only_supported_executable_comparisons() -> None:
    keys = survey_v1_executable_keys()

    assert "independent_groups" in keys
    assert "paired_two_time" in keys
    assert "mediation" not in keys
    assert "moderated_mediation" not in keys
    assert "repeated_measures_anova" not in keys
    assert "friedman" not in keys


def test_deferred_advanced_analyses_fail_closed() -> None:
    capability = get_capability("repeated_measures_anova")

    assert capability.status is AnalysisStatus.DEFERRED
    assert "sphericity" in capability.reason
    assert "Greenhouse-Geisser" in capability.reason
    assert "Friedman" in capability.reason
    with pytest.raises(ValueError, match="not executable in Survey Pipeline V1"):
        require_executable("repeated_measures_anova")


def test_mediation_is_deferred_with_external_verification_paths() -> None:
    capability = get_capability("mediation")

    assert capability.status is AnalysisStatus.DEFERRED
    assert "Bootstrap CI" in capability.reason
    assert "PROCESS" in capability.external_paths
    assert "R/lavaan" in capability.external_paths
    assert "jamovi/jAMM" in capability.external_paths


def test_unknown_capability_key_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown analysis capability"):
        get_capability("unknown")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests\test_analysis_catalog.py -q -p no:cacheprovider
```

Expected: FAIL with `ModuleNotFoundError: No module named 'modori.analysis_catalog'`.

- [ ] **Step 3: Implement the catalog**

Create `src/modori/analysis_catalog.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AnalysisStatus(Enum):
    EXECUTABLE = "executable"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class AnalysisCapability:
    key: str
    label: str
    status: AnalysisStatus
    reason: str
    external_paths: tuple[str, ...] = ()


_CAPABILITIES: dict[str, AnalysisCapability] = {
    "independent_groups": AnalysisCapability(
        key="independent_groups",
        label="Independent two-group comparison",
        status=AnalysisStatus.EXECUTABLE,
        reason="Supported by CompareGroupsStep with Welch-first routing and Mann-Whitney fallback.",
    ),
    "paired_two_time": AnalysisCapability(
        key="paired_two_time",
        label="Two-time paired comparison",
        status=AnalysisStatus.EXECUTABLE,
        reason="Supported by PairedComparisonStep for paired t-test and Wilcoxon fallback.",
    ),
    "repeated_measures_anova": AnalysisCapability(
        key="repeated_measures_anova",
        label="Repeated-measures ANOVA",
        status=AnalysisStatus.DEFERRED,
        reason=(
            "Repeated-measures ANOVA is not executable in Survey Pipeline V1 because "
            "it requires sphericity evaluation, Greenhouse-Geisser correction when "
            "sphericity is violated, and Friedman routing for nonparametric cases."
        ),
        external_paths=("SPSS", "R", "jamovi"),
    ),
    "friedman": AnalysisCapability(
        key="friedman",
        label="Friedman test",
        status=AnalysisStatus.DEFERRED,
        reason="Friedman is paired with repeated-measures coverage and is V1.x with RM-ANOVA gates.",
        external_paths=("SPSS", "R", "jamovi"),
    ),
    "mediation": AnalysisCapability(
        key="mediation",
        label="Mediation analysis",
        status=AnalysisStatus.DEFERRED,
        reason=(
            "Mediation is V1.x because publishable output requires Bootstrap CI, "
            "indirect-effect reporting, and cross-checks against PROCESS/R/lavaan."
        ),
        external_paths=("PROCESS", "R/lavaan", "jamovi/jAMM"),
    ),
    "moderated_mediation": AnalysisCapability(
        key="moderated_mediation",
        label="Moderated mediation",
        status=AnalysisStatus.DEFERRED,
        reason="Moderated mediation requires the advanced process module and is not executable in V1.",
        external_paths=("PROCESS", "R/lavaan", "jamovi/jAMM"),
    ),
}


def get_capability(key: str) -> AnalysisCapability:
    try:
        return _CAPABILITIES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown analysis capability: {key}") from exc


def require_executable(key: str) -> AnalysisCapability:
    capability = get_capability(key)
    if capability.status is not AnalysisStatus.EXECUTABLE:
        raise ValueError(f"{capability.label} is not executable in Survey Pipeline V1: {capability.reason}")
    return capability


def survey_v1_executable_keys() -> set[str]:
    return {
        key
        for key, capability in _CAPABILITIES.items()
        if capability.status is AnalysisStatus.EXECUTABLE
    }
```

- [ ] **Step 4: Run catalog tests**

Run:

```powershell
python -m pytest tests\test_analysis_catalog.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/modori/analysis_catalog.py tests/test_analysis_catalog.py
git commit -m "feat: add survey v1 analysis catalog"
```

---

### Task 2: Add Case-Count Fields To Comparison Results

**Files:**
- Modify: `src/modori/results.py`
- Modify: `src/modori/steps/statistics.py`
- Modify: `tests/test_compare_groups_step.py`
- Modify: `tests/test_reporting_prose_contracts.py`

- [ ] **Step 1: Write failing case-count assertions**

In `tests/test_compare_groups_step.py`, update `test_compare_groups_routes_to_welch_when_variance_is_unequal` to assert total and dropped cases:

```python
def test_compare_groups_reports_used_and_excluded_n() -> None:
    dataset = comparison_dataset(
        [9, 10, 11, float("nan"), 9],
        [0, 5, 10, 15, 20],
    )
    result = compare_step().compute_context_free(dataset).analysis

    assert result.n_total == 10
    assert result.n_obs == 9
    assert result.n_dropped == 1
```

In `tests/test_reporting_prose_contracts.py`, update `_comparison_result` to include:

```python
        n_obs=20,
        n_total=22,
        n_dropped=2,
```

Then add:

```python
def test_comparison_prose_mentions_excluded_n() -> None:
    prose = prose_for(_comparison_result("welch_t"), "ko")

    assert "분석에는 20명이 사용되었고 2명은 결측으로 제외되었다" in prose
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests\test_compare_groups_step.py::test_compare_groups_reports_used_and_excluded_n tests\test_reporting_prose_contracts.py::test_comparison_prose_mentions_excluded_n -q -p no:cacheprovider
```

Expected: FAIL with `AttributeError` or dataclass constructor error for missing `n_obs`, `n_total`, or `n_dropped`.

- [ ] **Step 3: Extend `ComparisonResult`**

Modify `src/modori/results.py`:

```python
@dataclass(frozen=True)
class ComparisonResult:
    dv: str
    group_var: str
    test_name: str
    route_reason: str
    groups: dict[str, GroupDesc]
    statistic: float
    df: float | None
    p_value: float
    effect_name: str
    effect_value: float
    mean_diff_ci: tuple[float, float] | None
    assumptions: dict[str, float]
    apa_template_id: str
    chart_spec: ChartSpec
    n_obs: int
    n_total: int
    n_dropped: int
    dv_label: str | None = None
    group_label: str | None = None
```

- [ ] **Step 4: Populate counts in `CompareGroupsStep`**

In `src/modori/steps/statistics.py`, change the start of `CompareGroupsStep.compute`:

```python
        source_frame = ctx.dataset.frame_for_compute([dv, group_var])
        n_total = int(len(source_frame))
        frame = source_frame.dropna(axis=0, how="any")
        n_obs = int(len(frame))
        n_dropped = int(n_total - n_obs)
```

Pass `n_obs`, `n_total`, and `n_dropped` through `_t_result` and `_mann_whitney_result`, then set those fields when constructing `ComparisonResult`:

```python
            n_obs=n_obs,
            n_total=n_total,
            n_dropped=n_dropped,
```

- [ ] **Step 5: Add deterministic N wording**

In `src/modori/steps/reporting.py`, add:

```python
def _comparison_n_sentence(result: ComparisonResult, language: str) -> str:
    if result.n_dropped <= 0:
        return ""
    if language == "en":
        return f" The analysis used {result.n_obs} cases; {result.n_dropped} cases were excluded for missing values."
    return f" 분석에는 {result.n_obs}명이 사용되었고 {result.n_dropped}명은 결측으로 제외되었다."
```

Append `_comparison_n_sentence(result, language)` to every returned comparison prose string.

- [ ] **Step 6: Run affected tests**

Run:

```powershell
python -m pytest tests\test_compare_groups_step.py tests\test_reporting_prose_contracts.py -q -p no:cacheprovider
```

Expected: PASS after updating all `ComparisonResult` test fixtures with `n_obs`, `n_total`, and `n_dropped`.

- [ ] **Step 7: Commit**

Run:

```powershell
git add src/modori/results.py src/modori/steps/statistics.py src/modori/steps/reporting.py tests/test_compare_groups_step.py tests/test_reporting_prose_contracts.py
git commit -m "feat: report comparison case counts"
```

---

### Task 3: Make Independent Comparisons Welch-First

**Files:**
- Modify: `src/modori/steps/statistics.py`
- Modify: `tests/test_compare_groups_step.py`
- Modify: `tests/test_reporting_prose_contracts.py`

- [ ] **Step 1: Update failing Welch-first tests**

Rename `test_compare_groups_routes_to_student_t_when_assumptions_hold` to:

```python
def test_compare_groups_uses_welch_by_default_when_assumptions_hold() -> None:
    result = compare_step().compute_context_free(
        comparison_dataset(
            [10, 11, 9, 10, 12, 11, 10, 9, 11, 10],
            [12, 13, 11, 12, 14, 13, 12, 11, 13, 12],
        )
    ).analysis

    assert result.test_name == "welch_t"
    assert result.route_reason == "Welch-first policy"
    assert result.statistic == pytest.approx(-4.714, abs=0.001)
    assert result.effect_name == "cohen_d"
    assert sign(result.effect_value) == sign(result.statistic)
```

Update the public dataset reference test to expect `pg.ttest(correction=True)`:

```python
    reference = pg.ttest(
        frame.loc[frame["Group"] == "Control", "Scores"],
        frame.loc[frame["Group"] == "Meditation", "Scores"],
        correction=True,
    ).iloc[0]

    assert result.test_name == "welch_t"
    assert result.statistic == pytest.approx(float(reference["T"]), abs=1e-12)
    assert result.df == pytest.approx(float(reference["dof"]), abs=1e-12)
    assert result.p_value == pytest.approx(float(reference["p_val"]), abs=1e-12)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests\test_compare_groups_step.py::test_compare_groups_uses_welch_by_default_when_assumptions_hold -q -p no:cacheprovider
```

Expected: FAIL because `_route` currently returns `student_t` when assumptions hold.

- [ ] **Step 3: Change routing**

In `src/modori/steps/statistics.py`, replace the final routing branch in `_route` with:

```python
        if allow_nonparametric and normality_violated and min(len(first), len(second)) < nonparametric_cutoff:
            return "mann_whitney", "normality violated + small sample"
        if preset == "classic":
            if variance_unequal:
                return "welch_t", "unequal variance -> Welch correction"
            return "student_t", "classic policy"
        if preset == "custom" and policy.get("default_test") == "student_t":
            if variance_unequal:
                return "welch_t", "unequal variance -> Welch correction"
            return "student_t", "custom policy requested Student t"
        return "welch_t", "Welch-first policy"
```

- [ ] **Step 4: Update exact expectations affected by Welch-first routing**

Apply these exact expectation changes in `tests/test_compare_groups_step.py`:

```python
def test_modern_routing_uses_nonparametric_cutoff_boundary() -> None:
    step = compare_step()
    violated = {"shapiro_g1_p": 0.049, "shapiro_g2_p": 0.500, "levene_p": 0.500}

    route_29, reason_29 = step._route(
        pd.Series(range(29)),
        pd.Series(range(29)),
        violated,
    )
    route_30, reason_30 = step._route(
        pd.Series(range(30)),
        pd.Series(range(30)),
        violated,
    )

    assert (route_29, reason_29) == (
        "mann_whitney",
        "normality violated + small sample",
    )
    assert (route_30, reason_30) == ("welch_t", "Welch-first policy")
```

Update `test_compare_groups_writes_analysis_object_for_pipeline`:

```python
    assert pipeline.step_results["compare"].notes == [
        "Selected Welch's t-test because Welch-first policy."
    ]
```

Keep the classic-policy test as the only test that expects `"student_t"` for a modern-numeric case.

- [ ] **Step 5: Run comparison tests**

Run:

```powershell
python -m pytest tests\test_compare_groups_step.py tests\test_reporting_prose_contracts.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/modori/steps/statistics.py tests/test_compare_groups_step.py tests/test_reporting_prose_contracts.py
git commit -m "feat: make independent comparisons welch first"
```

---

### Task 4: Add Two-Time Paired Comparison Step

**Files:**
- Modify: `src/modori/results.py`
- Modify: `src/modori/steps/statistics.py`
- Modify: `src/modori/steps/__init__.py`
- Create: `tests/test_paired_comparison_step.py`

- [ ] **Step 1: Write paired comparison tests**

Create `tests/test_paired_comparison_step.py`:

```python
import pandas as pd
import pytest

from modori.core import Dataset, Measure, Pipeline, Variable
from modori.steps import PairedComparisonStep


def paired_dataset(pre: list[float], post: list[float]) -> Dataset:
    frame = pd.DataFrame({"pre": pre, "post": post})
    variables = {
        "pre": Variable("pre", "Pre score", Measure.SCALE, {}, [], "float", None),
        "post": Variable("post", "Post score", Measure.SCALE, {}, [], "float", None),
    }
    return Dataset(df=frame, variables=variables)


def paired_step(policy: dict | None = None) -> PairedComparisonStep:
    return PairedComparisonStep(
        id="paired",
        title="Compare paired scores",
        params={
            "before": "pre",
            "after": "post",
            "routing_policy": policy or {"preset": "modern"},
        },
    )


def test_paired_comparison_uses_paired_t_for_approximately_normal_differences() -> None:
    result = paired_step().compute_context_free(
        paired_dataset(
            [10, 11, 12, 13, 14, 15, 16, 17],
            [11, 13, 13, 15, 15, 17, 17, 19],
        )
    ).analysis

    assert result.test_name == "paired_t"
    assert result.route_reason == "paired differences compatible with t-test"
    assert result.n_obs == 8
    assert result.n_total == 8
    assert result.n_dropped == 0
    assert result.effect_name == "cohen_dz"
    assert result.mean_diff_ci is not None


def test_paired_comparison_routes_to_wilcoxon_for_small_nonnormal_differences() -> None:
    result = paired_step().compute_context_free(
        paired_dataset(
            [1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 10],
        )
    ).analysis

    assert result.test_name == "wilcoxon"
    assert result.route_reason == "non-normal paired differences + small sample"
    assert result.df is None
    assert result.effect_name == "rank_biserial"


def test_paired_comparison_reports_excluded_pairs() -> None:
    result = paired_step().compute_context_free(
        paired_dataset([1, 2, None, 4], [2, 3, 4, None])
    ).analysis

    assert result.n_total == 4
    assert result.n_obs == 2
    assert result.n_dropped == 2


def test_paired_comparison_rejects_same_column() -> None:
    step = PairedComparisonStep(
        id="paired",
        title="Bad paired",
        params={"before": "pre", "after": "pre"},
    )

    with pytest.raises(ValueError, match="before and after variables must differ"):
        step.compute_context_free(paired_dataset([1, 2, 3], [2, 3, 4]))


def test_paired_comparison_writes_analysis_object_for_pipeline() -> None:
    pipeline = Pipeline(paired_dataset([1, 2, 3, 4], [2, 3, 4, 5]))
    pipeline.add(paired_step())

    pipeline.recompute(dirty_from=None)

    assert "comparison:pre:post:paired" in pipeline.analysis_objects
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests\test_paired_comparison_step.py -q -p no:cacheprovider
```

Expected: FAIL with `ImportError: cannot import name 'PairedComparisonStep'`.

- [ ] **Step 3: Add related-samples metadata to `ComparisonResult`**

Modify `src/modori/results.py`:

```python
    paired: bool = False
    before_label: str | None = None
    after_label: str | None = None
```

Place these fields after `group_label` so existing independent-comparison calls can keep using defaults.

- [ ] **Step 4: Implement `PairedComparisonStep`**

Add this class to `src/modori/steps/statistics.py` after `CompareGroupsStep`:

```python
@dataclass
class PairedComparisonStep(Step):
    step_type = "stats.paired_comparison"
    produces_analysis = True

    def compute(self, ctx: PipelineContext) -> StepResult:
        before = str(self.params["before"])
        after = str(self.params["after"])
        if before == after:
            raise ValueError("PairedComparisonStep before and after variables must differ.")
        frame = ctx.dataset.frame_for_compute([before, after])
        n_total = int(len(frame))
        frame = frame.dropna(axis=0, how="any")
        n_obs = int(len(frame))
        n_dropped = int(n_total - n_obs)
        if n_obs < 3:
            raise ValueError("PairedComparisonStep requires at least three complete pairs.")
        for column in [before, after]:
            if ctx.dataset.variables[column].measure is not Measure.SCALE:
                raise ValueError(f"PairedComparisonStep requires SCALE variables: {column}")
            if not pd.api.types.is_numeric_dtype(frame[column]):
                raise ValueError(f"PairedComparisonStep requires numeric variables: {column}")
        diff = frame[after].astype(float) - frame[before].astype(float)
        if diff.nunique(dropna=True) < 2:
            raise ValueError("PairedComparisonStep requires non-zero variance in paired differences.")

        policy = dict(self.params.get("routing_policy", {"preset": "modern"}))
        route, reason = self._route(diff, policy)
        before_label = ctx.dataset.variables[before].label or before
        after_label = ctx.dataset.variables[after].label or after

        if route == "wilcoxon":
            analysis = self._wilcoxon_result(before, after, before_label, after_label, frame, diff, reason, n_total, n_obs, n_dropped)
            note = "Wilcoxon signed-rank test"
        else:
            analysis = self._paired_t_result(before, after, before_label, after_label, frame, diff, reason, n_total, n_obs, n_dropped)
            note = "paired-samples t-test"
        return StepResult(analysis=analysis, notes=[f"Selected {note} because {analysis.route_reason}."])

    @staticmethod
    def _route(diff: pd.Series, policy: dict[str, object]) -> tuple[str, str]:
        preset = str(policy.get("preset", "modern"))
        if preset == "always_wilcoxon":
            return "wilcoxon", "always_wilcoxon policy"
        if preset == "classic":
            return "paired_t", "classic policy"
        alpha = float(policy.get("normality_p", 0.05))
        cutoff = int(policy.get("nonparametric_n_cutoff", 30))
        shapiro_p = float(stats.shapiro(diff).pvalue)
        if shapiro_p < alpha and len(diff) < cutoff:
            return "wilcoxon", "non-normal paired differences + small sample"
        return "paired_t", "paired differences compatible with t-test"

    @staticmethod
    def _paired_t_result(
        before: str,
        after: str,
        before_label: str,
        after_label: str,
        frame: pd.DataFrame,
        diff: pd.Series,
        route_reason: str,
        n_total: int,
        n_obs: int,
        n_dropped: int,
    ) -> ComparisonResult:
        test = pg.ttest(frame[after], frame[before], paired=True).iloc[0]
        ci = tuple(float(value) for value in test["CI95"])
        dz = float(test["T"]) / float(np.sqrt(n_obs))
        return ComparisonResult(
            dv=after,
            group_var=before,
            test_name="paired_t",
            route_reason=route_reason,
            groups={
                before_label: GroupDesc(n=n_obs, mean=float(frame[before].mean()), sd=float(frame[before].std(ddof=1)), median=float(frame[before].median())),
                after_label: GroupDesc(n=n_obs, mean=float(frame[after].mean()), sd=float(frame[after].std(ddof=1)), median=float(frame[after].median())),
            },
            statistic=float(test["T"]),
            df=float(test["dof"]),
            p_value=float(test["p_val"]),
            effect_name="cohen_dz",
            effect_value=dz,
            mean_diff_ci=(ci[0], ci[1]),
            assumptions={"shapiro_diff_p": float(stats.shapiro(diff).pvalue)},
            apa_template_id="paired_t.v1",
            chart_spec=ChartSpec(
                type="paired_line",
                title="Paired score change",
                data={"before": frame[before].tolist(), "after": frame[after].tolist()},
                x_label="Time",
                y_label=after,
            ),
            n_obs=n_obs,
            n_total=n_total,
            n_dropped=n_dropped,
            dv_label=after_label,
            group_label=before_label,
            paired=True,
            before_label=before_label,
            after_label=after_label,
        )

    @staticmethod
    def _wilcoxon_result(
        before: str,
        after: str,
        before_label: str,
        after_label: str,
        frame: pd.DataFrame,
        diff: pd.Series,
        route_reason: str,
        n_total: int,
        n_obs: int,
        n_dropped: int,
    ) -> ComparisonResult:
        test = pg.wilcoxon(frame[after], frame[before]).iloc[0]
        return ComparisonResult(
            dv=after,
            group_var=before,
            test_name="wilcoxon",
            route_reason=route_reason,
            groups={
                before_label: GroupDesc(n=n_obs, mean=float(frame[before].mean()), sd=float(frame[before].std(ddof=1)), median=float(frame[before].median())),
                after_label: GroupDesc(n=n_obs, mean=float(frame[after].mean()), sd=float(frame[after].std(ddof=1)), median=float(frame[after].median())),
            },
            statistic=float(test["W-val"]),
            df=None,
            p_value=float(test["p-val"]),
            effect_name="rank_biserial",
            effect_value=float(test.get("RBC", 0.0)),
            mean_diff_ci=None,
            assumptions={"shapiro_diff_p": float(stats.shapiro(diff).pvalue)},
            apa_template_id="wilcoxon.v1",
            chart_spec=ChartSpec(
                type="paired_line",
                title="Paired score change",
                data={"before": frame[before].tolist(), "after": frame[after].tolist()},
                x_label="Time",
                y_label=after,
            ),
            n_obs=n_obs,
            n_total=n_total,
            n_dropped=n_dropped,
            dv_label=after_label,
            group_label=before_label,
            paired=True,
            before_label=before_label,
            after_label=after_label,
        )

    def reads(self) -> set[str]:
        return {str(self.params["before"]), str(self.params["after"])}

    def writes(self) -> set[str]:
        return {f"comparison:{self.params['before']}:{self.params['after']}:paired"}

    def provenance(self) -> str:
        return f"paired comparison {self.params['before']} to {self.params['after']}"


Step.register_type(PairedComparisonStep.step_type, PairedComparisonStep)
```

Also change the imports in `statistics.py` so the new code has its dependencies:

```python
from modori.core import Measure, PipelineContext, Step, StepResult
from modori.results import ChartSpec, ComparisonResult, GroupDesc, ReliabilityResult
```

- [ ] **Step 5: Export the new step**

Modify `src/modori/steps/__init__.py`:

```python
from modori.steps.statistics import CompareGroupsStep, PairedComparisonStep, ReliabilityStep
```

Add `"PairedComparisonStep"` to `__all__`.

- [ ] **Step 6: Run paired tests**

Run:

```powershell
python -m pytest tests\test_paired_comparison_step.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add src/modori/results.py src/modori/steps/statistics.py src/modori/steps/__init__.py tests/test_paired_comparison_step.py
git commit -m "feat: add paired comparison step"
```

---

### Task 5: Add Deterministic Paired/Wilcoxon Report Wording

**Files:**
- Modify: `src/modori/steps/reporting.py`
- Modify: `tests/test_reporting_prose_contracts.py`

- [ ] **Step 1: Add exact prose tests**

Add fixtures to `tests/test_reporting_prose_contracts.py`:

```python
def _paired_result(test_name: str = "paired_t") -> ComparisonResult:
    return ComparisonResult(
        dv="post",
        group_var="pre",
        test_name=test_name,
        route_reason="paired differences compatible with t-test" if test_name == "paired_t" else "non-normal paired differences + small sample",
        groups={
            "Pre score": GroupDesc(n=8, mean=12.25, sd=2.49, median=12.5),
            "Post score": GroupDesc(n=8, mean=13.75, sd=2.71, median=14.0),
        },
        statistic=-4.20 if test_name == "paired_t" else 0.0,
        df=7.0 if test_name == "paired_t" else None,
        p_value=0.004 if test_name == "paired_t" else 0.031,
        effect_name="cohen_dz" if test_name == "paired_t" else "rank_biserial",
        effect_value=-1.48 if test_name == "paired_t" else -0.75,
        mean_diff_ci=(-2.35, -0.65) if test_name == "paired_t" else None,
        assumptions={"shapiro_diff_p": 0.42},
        apa_template_id="paired_t.v1" if test_name == "paired_t" else "wilcoxon.v1",
        chart_spec=_dummy_chart("paired_line"),
        n_obs=8,
        n_total=9,
        n_dropped=1,
        dv_label="Post score",
        group_label="Pre score",
        paired=True,
        before_label="Pre score",
        after_label="Post score",
    )
```

Add:

```python
def test_paired_t_prose_is_exactly_locked() -> None:
    assert prose_for(_paired_result("paired_t"), "ko") == (
        "대응표본 t검정 결과, Pre score와 Post score의 평균 차이는 통계적으로 유의하였다, "
        "t(7.00) = -4.20, p = .004, 95% CI [-2.35, -.65], Cohen's dz = -1.48. "
        "분석에는 8명이 사용되었고 1명은 결측으로 제외되었다."
    )


def test_wilcoxon_prose_is_exactly_locked() -> None:
    assert prose_for(_paired_result("wilcoxon"), "ko") == (
        "Wilcoxon 부호순위검정 결과, Pre score와 Post score의 차이는 통계적으로 유의하였다, "
        "W = 0.00, p = .031, rank_biserial = -.75. "
        "분석에는 8명이 사용되었고 1명은 결측으로 제외되었다."
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests\test_reporting_prose_contracts.py::test_paired_t_prose_is_exactly_locked tests\test_reporting_prose_contracts.py::test_wilcoxon_prose_is_exactly_locked -q -p no:cacheprovider
```

Expected: FAIL with `ValueError: Unsupported comparison test`.

- [ ] **Step 3: Add effect label and test labels**

Modify `src/modori/steps/reporting.py`:

```python
def _comparison_effect_label(result: ComparisonResult) -> str:
    if result.effect_name == "cohen_d":
        return "Cohen's d"
    if result.effect_name == "cohen_dz":
        return "Cohen's dz"
    if result.effect_name == "hedges_g":
        return "Hedges' g"
    if result.effect_name == "eta_squared":
        return "eta squared"
    return result.effect_name
```

Add labels:

```python
    if result.test_name == "wilcoxon":
        return "Wilcoxon 부호순위검정"
```

and:

```python
    if result.test_name == "wilcoxon":
        return "Wilcoxon signed-rank test"
```

- [ ] **Step 4: Add paired prose branch**

In `_comparison_prose`, before the independent t-test branch, add:

```python
    n_sentence = _comparison_n_sentence(result, language)
    if result.test_name in {"paired_t", "wilcoxon"}:
        before_label = result.before_label or first_label
        after_label = result.after_label or second_label
        significance_ko = "통계적으로 유의하였다" if result.p_value < 0.05 else "통계적으로 유의하지 않았다"
        significance_en = "a statistically significant" if result.p_value < 0.05 else "no statistically significant"
        if result.test_name == "paired_t":
            df_text = _apa_number(result.df, 2) if result.df is not None else ""
            ci_text = ""
            if result.mean_diff_ci is not None:
                ci_text = f", 95% CI [{_apa_number(result.mean_diff_ci[0])}, {_apa_number(result.mean_diff_ci[1])}]"
            if language == "en":
                return (
                    f"A paired-samples t test showed {significance_en} mean difference between "
                    f"{before_label} and {after_label}, t({df_text}) = {_apa_number(result.statistic)}, "
                    f"{p_text}{ci_text}, {_comparison_effect_label(result)} = {_apa_number(result.effect_value, omit_leading_zero=True)}."
                    f"{n_sentence}"
                )
            return (
                f"대응표본 t검정 결과, {before_label}와 {after_label}의 평균 차이는 {significance_ko}, "
                f"t({df_text}) = {_apa_number(result.statistic)}, {p_text}{ci_text}, "
                f"{_comparison_effect_label(result)} = {_apa_number(result.effect_value, omit_leading_zero=True)}."
                f"{n_sentence}"
            )
        if language == "en":
            return (
                f"A Wilcoxon signed-rank test showed {significance_en} difference between "
                f"{before_label} and {after_label}, W = {_apa_number(result.statistic)}, "
                f"{p_text}, {result.effect_name} = {_apa_number(result.effect_value, omit_leading_zero=True)}."
                f"{n_sentence}"
            )
        return (
            f"Wilcoxon 부호순위검정 결과, {before_label}와 {after_label}의 차이는 {significance_ko}, "
            f"W = {_apa_number(result.statistic)}, {p_text}, "
            f"{result.effect_name} = {_apa_number(result.effect_value, omit_leading_zero=True)}."
            f"{n_sentence}"
        )
```

- [ ] **Step 5: Run reporting tests**

Run:

```powershell
python -m pytest tests\test_reporting_prose_contracts.py tests\test_report_step.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/modori/steps/reporting.py tests/test_reporting_prose_contracts.py
git commit -m "feat: report paired comparison results"
```

---

### Task 6: Full Verification For This Slice

**Files:**
- No code changes expected.

- [ ] **Step 1: Run focused engine suite**

Run:

```powershell
python -m pytest tests\test_analysis_catalog.py tests\test_data_prep_steps.py tests\test_compare_groups_step.py tests\test_paired_comparison_step.py tests\test_reliability_step.py tests\test_regression_step.py tests\test_report_step.py tests\test_reporting_prose_contracts.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 2: Run UI thin-shell guard**

Run:

```powershell
python -m pytest tests\ui\test_thin_shell_guards.py tests\ui\test_architecture_guards.py -q -p no:cacheprovider
```

Expected: PASS. This confirms the UI did not gain statistical computation imports.

- [ ] **Step 3: Run packaged smoke baseline if packaging files changed**

Run only if the implementation touched packaging, app entry, import flow, or QML:

```powershell
python -m pytest tests\test_package_engine_smoke_script.py tests\test_package_launch_smoke_script.py -q -p no:cacheprovider
```

Expected: PASS. If this plan only changes engine/reporting files, record this command as not required in the final implementation report.

- [ ] **Step 4: Confirm no QA note is needed for engine-only changes**

If implementation touched only engine/reporting files listed in this plan, run this command and leave docs unchanged:

```powershell
git status --short
```

Expected: only implementation files are modified before the final implementation commit. If packaging, app entry, import flow, or QML changed during execution, stop and write a separate QA note plan before committing those changes.

## Plan Self-Review

Spec coverage in this first implementation slice:

- Deterministic capability boundary: Task 1.
- RM-ANOVA/Friedman/mediation fail-closed: Task 1.
- Welch-first gate: Task 3.
- Paired two-time comparison without RM-ANOVA scope creep: Task 4.
- N/excluded N visible in result/report: Tasks 2 and 5.
- Deterministic report wording: Task 5.
- UI thin-shell boundary preserved: Task 6.

Known spec areas intentionally left for separate plans:

- Descriptives/Table 1.
- Kruskal-Wallis and one-way ANOVA/post-hoc expansion.
- ANCOVA.
- Factor/PCA with KMO, Bartlett, and parallel analysis.
- Regression interaction safety and simple slopes.
- Full report export QA across the expanded result set.

No V1 task in this plan adds AI/SLM, mediation execution, repeated-measures ANOVA, Friedman, mixed models, or MANOVA.
