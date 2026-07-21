"""Shared, non-inferential structural input validation for statistical steps."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import unicodedata

import numpy as np
import pandas as pd

from modori.core import Dataset, Measure, Variable


STEP_INPUT_ISSUE_CODES = frozenset(
    {
        "boolean_not_allowed",
        "dataset_empty",
        "duplicate_display_label",
        "duplicate_variable",
        "group_too_small",
        "insufficient_categories",
        "invalid_params",
        "missing_variable",
        "no_nonmissing_value",
        "non_finite",
        "non_numeric",
        "p1_group_requires_categorical",
        "p1_requires_scale",
        "pearson_requires_scale",
        "pipeline_changed",
        "preflight_failure",
        "role_collision",
        "too_few_complete_pairs",
        "unsupported_measure",
        "unsupported_step_type",
        "wrong_group_cardinality",
        "zero_paired_difference_variance",
        "zero_variance",
    }
)

_SUPPORTED_STEP_TYPES = frozenset(
    {
        "stats.descriptives_table1",
        "stats.frequency_crosstab",
        "stats.correlation",
        "stats.compare_groups",
        "stats.paired_comparison",
    }
)


@dataclass(frozen=True)
class StepInputIssue:
    code: str
    role: str | None = None
    variable_id: str | None = None

    def __post_init__(self) -> None:
        if self.code not in STEP_INPUT_ISSUE_CODES:
            raise ValueError("StepInputIssue code is outside the closed catalog")
        if self.role is not None and (
            not isinstance(self.role, str)
            or not self.role.strip()
            or self.role != unicodedata.normalize("NFC", self.role)
        ):
            raise ValueError("StepInputIssue role must be a non-empty NFC string")
        if self.variable_id is not None and not isinstance(self.variable_id, str):
            raise ValueError("StepInputIssue variable_id must be a string or null")


class StepInputValidationError(ValueError):
    """Existing ValueError surface carrying the shared typed issues."""

    def __init__(self, message: str, issues: tuple[StepInputIssue, ...]) -> None:
        self.issues = issues
        super().__init__(message)


class StepInputValidationKeyError(KeyError):
    """Existing unknown-column KeyError surface carrying shared typed issues."""

    def __init__(self, message: str, issues: tuple[StepInputIssue, ...]) -> None:
        self.issues = issues
        super().__init__(message)


def _invalid_params() -> tuple[StepInputIssue, ...]:
    return (StepInputIssue(code="invalid_params"),)


def _missing_issues(
    dataset: Dataset,
    requested: list[tuple[str, str]],
) -> tuple[StepInputIssue, ...]:
    return tuple(
        StepInputIssue(code="missing_variable", role=role, variable_id=key)
        for key, role in requested
        if key not in dataset.variables
    )


def _numeric_values(
    series: pd.Series,
    *,
    role: str,
    variable_id: str,
    reject_boolean: bool = False,
) -> tuple[pd.Series | None, StepInputIssue | None]:
    nonmissing = series.dropna()
    if reject_boolean and any(
        isinstance(value, (bool, np.bool_)) for value in nonmissing
    ):
        return None, StepInputIssue(
            code="boolean_not_allowed",
            role=role,
            variable_id=variable_id,
        )
    if (
        pd.api.types.is_datetime64_any_dtype(nonmissing.dtype)
        or pd.api.types.is_timedelta64_dtype(nonmissing.dtype)
        or pd.api.types.is_complex_dtype(nonmissing.dtype)
    ):
        return None, StepInputIssue(
            code="non_numeric",
            role=role,
            variable_id=variable_id,
        )
    try:
        values = pd.to_numeric(nonmissing, errors="raise").astype(float)
    except (TypeError, ValueError, OverflowError):
        return None, StepInputIssue(
            code="non_numeric",
            role=role,
            variable_id=variable_id,
        )
    if len(values) and not np.all(np.isfinite(values.to_numpy(dtype=float))):
        return None, StepInputIssue(
            code="non_finite",
            role=role,
            variable_id=variable_id,
        )
    return values, None


def _validate_descriptives(
    dataset: Dataset,
    params: Mapping[str, object],
) -> tuple[StepInputIssue, ...]:
    variables = params.get("variables")
    group = params.get("group")
    if (
        not isinstance(variables, list)
        or not variables
        or not all(isinstance(item, str) for item in variables)
        or (group is not None and not isinstance(group, str))
    ):
        return _invalid_params()
    if dataset.df.empty:
        return (StepInputIssue(code="dataset_empty"),)
    if len(set(variables)) != len(variables):
        return (StepInputIssue(code="duplicate_variable"),)
    if group is not None and group in variables:
        return (
            StepInputIssue(
                code="role_collision",
                role="group",
                variable_id=group,
            ),
        )
    requested = [(key, "variable") for key in variables]
    if group is not None:
        requested.append((group, "group"))
    missing = _missing_issues(dataset, requested)
    if missing:
        return missing
    unsupported = tuple(
        StepInputIssue(
            code="unsupported_measure",
            role="variable",
            variable_id=key,
        )
        for key in variables
        if dataset.variables[key].measure
        not in {Measure.SCALE, Measure.NOMINAL, Measure.ORDINAL}
    )
    if unsupported:
        return unsupported
    if group is not None and dataset.variables[group].measure not in {
        Measure.NOMINAL,
        Measure.ORDINAL,
    }:
        return (
            StepInputIssue(
                code="unsupported_measure",
                role="group",
                variable_id=group,
            ),
        )
    frame = dataset.frame_for_compute(variables)
    for key in variables:
        if dataset.variables[key].measure is not Measure.SCALE:
            continue
        _values, issue = _numeric_values(
            frame[key],
            role="variable",
            variable_id=key,
            reject_boolean=True,
        )
        if issue is not None:
            return (issue,)
    return ()


def _validate_frequency(
    dataset: Dataset,
    params: Mapping[str, object],
) -> tuple[StepInputIssue, ...]:
    variables = params.get("variables")
    mode = params.get("mode")
    if (
        mode not in {"frequency", "crosstab"}
        or not isinstance(variables, list)
        or not variables
        or not all(isinstance(item, str) for item in variables)
    ):
        return _invalid_params()
    if dataset.df.empty:
        return (StepInputIssue(code="dataset_empty"),)
    if len(set(variables)) != len(variables):
        return (StepInputIssue(code="duplicate_variable"),)
    missing = _missing_issues(
        dataset,
        [(key, "variable") for key in variables],
    )
    if missing:
        return missing
    unsupported = tuple(
        StepInputIssue(
            code="unsupported_measure",
            role="variable",
            variable_id=key,
        )
        for key in variables
        if dataset.variables[key].measure not in {Measure.NOMINAL, Measure.ORDINAL}
    )
    if unsupported:
        return unsupported
    if mode == "crosstab":
        if len(variables) != 2:
            return _invalid_params()
        frame = dataset.frame_for_compute(variables).dropna(axis=0, how="any")
        if any(frame[key].nunique(dropna=True) < 2 for key in variables):
            return (StepInputIssue(code="insufficient_categories"),)
    return ()


def _validate_correlation(
    dataset: Dataset,
    params: Mapping[str, object],
) -> tuple[StepInputIssue, ...]:
    variables = params.get("variables")
    pairs = params.get("pairs")
    method = params.get("method")
    missing_policy = params.get("missing_policy")
    if (
        not isinstance(variables, list)
        or not variables
        or not all(isinstance(item, str) for item in variables)
        or not isinstance(pairs, list)
        or not pairs
        or method not in {"auto", "pearson", "spearman"}
        or missing_policy not in {"pairwise", "listwise"}
    ):
        return _invalid_params()
    normalized_pairs: list[tuple[str, str]] = []
    for pair in pairs:
        if (
            not isinstance(pair, list | tuple)
            or len(pair) != 2
            or not all(isinstance(item, str) for item in pair)
        ):
            return _invalid_params()
        normalized_pairs.append((pair[0], pair[1]))
    if dataset.df.empty:
        return (StepInputIssue(code="dataset_empty"),)
    missing = _missing_issues(
        dataset,
        [(key, "variable") for key in variables],
    )
    if missing:
        return missing
    unsupported = tuple(
        StepInputIssue(
            code="unsupported_measure",
            role="variable",
            variable_id=key,
        )
        for key in variables
        if dataset.variables[key].measure not in {Measure.SCALE, Measure.ORDINAL}
    )
    if unsupported:
        return unsupported
    frame = dataset.frame_for_compute(variables)
    listwise_frame = (
        frame.dropna(axis=0, how="any") if missing_policy == "listwise" else None
    )
    for x, y in normalized_pairs:
        pair_frame = (
            frame.loc[:, [x, y]].dropna(axis=0, how="any")
            if listwise_frame is None
            else listwise_frame.loc[:, [x, y]]
        )
        if len(pair_frame) < 3:
            return (StepInputIssue(code="too_few_complete_pairs"),)
        numeric: dict[str, pd.Series] = {}
        for key, role in ((x, "x"), (y, "y")):
            values, issue = _numeric_values(
                pair_frame[key],
                role=role,
                variable_id=key,
                reject_boolean=True,
            )
            if issue is not None:
                return (issue,)
            if values is None:
                raise RuntimeError(
                    "numeric validation returned neither values nor issue"
                )
            numeric[key] = values
        for key, role in ((x, "x"), (y, "y")):
            if numeric[key].nunique(dropna=True) < 2:
                return (
                    StepInputIssue(
                        code="zero_variance",
                        role=role,
                        variable_id=key,
                    ),
                )
        if method == "pearson" and any(
            dataset.variables[key].measure is not Measure.SCALE for key in (x, y)
        ):
            return (StepInputIssue(code="pearson_requires_scale"),)
    return ()


def group_sort_key(value: object) -> tuple[int, float | str]:
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, str(value))


def ordered_group_values(frame: pd.DataFrame, group_var: str) -> list[object]:
    return sorted(list(pd.unique(frame[group_var])), key=group_sort_key)


def _value_label(variable: Variable, value: object) -> str:
    missing = object()
    label = variable.value_labels.get(value, missing)
    if label is missing:
        try:
            label = variable.value_labels.get(float(value), missing)
        except (TypeError, ValueError):
            label = missing
    return str(value) if label is missing else str(label)


def group_labels(
    dataset: Dataset,
    group_var: str,
    group_values: list[object],
) -> tuple[str, ...]:
    variable = dataset.variables[group_var]
    return tuple(_value_label(variable, value) for value in group_values)


def _validate_compare_groups(
    dataset: Dataset,
    params: Mapping[str, object],
) -> tuple[StepInputIssue, ...]:
    dv = params.get("dv")
    group = params.get("group")
    if not isinstance(dv, str) or not isinstance(group, str):
        return _invalid_params()
    if dataset.df.empty:
        return (StepInputIssue(code="dataset_empty"),)
    if dv == group:
        return (
            StepInputIssue(
                code="role_collision",
                role="group",
                variable_id=group,
            ),
        )
    missing = _missing_issues(dataset, [(dv, "outcome"), (group, "group")])
    if missing:
        return missing
    frame = dataset.frame_for_compute([dv, group]).dropna(axis=0, how="any")
    if not pd.api.types.is_numeric_dtype(frame[dv]):
        return (
            StepInputIssue(
                code="non_numeric",
                role="outcome",
                variable_id=dv,
            ),
        )
    values, issue = _numeric_values(
        frame[dv],
        role="outcome",
        variable_id=dv,
        reject_boolean=True,
    )
    if issue is not None:
        return (issue,)
    if values is None:
        raise RuntimeError("numeric validation returned neither values nor issue")
    group_values = ordered_group_values(frame, group)
    if len(group_values) != 2:
        return (StepInputIssue(code="wrong_group_cardinality", role="group"),)
    first = frame.loc[frame[group] == group_values[0], dv]
    second = frame.loc[frame[group] == group_values[1], dv]
    if len(first) < 3 or len(second) < 3:
        return (StepInputIssue(code="group_too_small", role="group"),)
    if first.nunique(dropna=True) < 2 or second.nunique(dropna=True) < 2:
        return (
            StepInputIssue(
                code="zero_variance",
                role="outcome",
                variable_id=dv,
            ),
        )
    labels = group_labels(dataset, group, group_values)
    if labels[0] == labels[1]:
        return (
            StepInputIssue(
                code="duplicate_display_label",
                role="group",
                variable_id=group,
            ),
        )
    return ()


def _validate_paired(
    dataset: Dataset,
    params: Mapping[str, object],
) -> tuple[StepInputIssue, ...]:
    before = params.get("before")
    after = params.get("after")
    if not isinstance(before, str) or not isinstance(after, str):
        return _invalid_params()
    if dataset.df.empty:
        return (StepInputIssue(code="dataset_empty"),)
    if before == after:
        return (
            StepInputIssue(
                code="role_collision",
                role="after",
                variable_id=after,
            ),
        )
    missing = _missing_issues(dataset, [(before, "before"), (after, "after")])
    if missing:
        return missing
    if (
        dataset.variables[before].measure is not Measure.SCALE
        or dataset.variables[after].measure is not Measure.SCALE
    ):
        return (StepInputIssue(code="unsupported_measure"),)
    source_frame = dataset.frame_for_compute([before, after])
    if not (
        pd.api.types.is_numeric_dtype(source_frame[before])
        and pd.api.types.is_numeric_dtype(source_frame[after])
    ):
        return (StepInputIssue(code="non_numeric"),)
    frame = source_frame.dropna(axis=0, how="any")
    for key, role in ((before, "before"), (after, "after")):
        _values, issue = _numeric_values(
            frame[key],
            role=role,
            variable_id=key,
            reject_boolean=True,
        )
        if issue is not None:
            return (issue,)
    if len(frame) < 3:
        return (StepInputIssue(code="too_few_complete_pairs"),)
    differences = frame[after] - frame[before]
    if differences.nunique(dropna=True) < 2:
        return (StepInputIssue(code="zero_paired_difference_variance"),)
    before_label = dataset.variables[before].label or before
    after_label = dataset.variables[after].label or after
    if before_label == after_label:
        return (StepInputIssue(code="duplicate_display_label"),)
    return ()


def validate_step_input(
    dataset: Dataset,
    step_type: str,
    canonical_params: Mapping[str, object],
) -> tuple[StepInputIssue, ...]:
    """Return closed structural issues without inference or dataset mutation."""

    if not isinstance(dataset, Dataset) or not isinstance(canonical_params, Mapping):
        return _invalid_params()
    if step_type not in _SUPPORTED_STEP_TYPES:
        return (StepInputIssue(code="unsupported_step_type"),)
    validators = {
        "stats.descriptives_table1": _validate_descriptives,
        "stats.frequency_crosstab": _validate_frequency,
        "stats.correlation": _validate_correlation,
        "stats.compare_groups": _validate_compare_groups,
        "stats.paired_comparison": _validate_paired,
    }
    return validators[step_type](dataset, canonical_params)


def _missing_names(issues: tuple[StepInputIssue, ...]) -> list[str]:
    return [
        issue.variable_id
        for issue in issues
        if issue.code == "missing_variable" and issue.variable_id is not None
    ]


def _names_for_code(
    issues: tuple[StepInputIssue, ...],
    code: str,
) -> list[str]:
    return [
        issue.variable_id
        for issue in issues
        if issue.code == code and issue.variable_id is not None
    ]


def _first_variable(issues: tuple[StepInputIssue, ...]) -> str:
    return next(
        (issue.variable_id for issue in issues if issue.variable_id is not None),
        "unknown",
    )


def _message_for_issues(
    step_type: str,
    issues: tuple[StepInputIssue, ...],
) -> str:
    first = issues[0]
    code = first.code
    variable = _first_variable(issues)
    missing = _missing_names(issues)
    unsupported = _names_for_code(issues, "unsupported_measure")
    if step_type == "stats.descriptives_table1":
        if code == "dataset_empty":
            return "데이터셋이 비어 있어 기술통계 표를 생성할 수 없습니다."
        if code == "duplicate_variable":
            return "기술통계 변수는 중복될 수 없습니다."
        if code == "role_collision":
            return "기술통계 변수와 그룹 변수는 서로 달라야 합니다."
        if code == "missing_variable":
            return f"데이터셋에 없는 변수: {', '.join(missing)}"
        if code == "unsupported_measure" and first.role == "group":
            return "그룹 변수는 명목 또는 서열 척도여야 합니다."
        if code == "unsupported_measure":
            return f"지원하지 않는 기술통계 변수: {', '.join(unsupported)}"
        if code == "boolean_not_allowed":
            return f"척도형 변수는 boolean 값을 허용하지 않습니다: {variable}"
        if code == "non_numeric":
            return f"척도형 변수는 숫자여야 합니다: {variable}"
        if code == "non_finite":
            return f"척도형 변수는 유한한 숫자여야 합니다: {variable}"
    elif step_type == "stats.frequency_crosstab":
        if code == "dataset_empty":
            return "데이터셋이 비어 있어 빈도분석을 수행할 수 없습니다."
        if code == "duplicate_variable":
            return "빈도 및 교차분석 변수는 서로 다른 변수여야 합니다."
        if code == "missing_variable":
            return f"데이터셋에 없는 변수: {', '.join(missing)}"
        if code == "unsupported_measure":
            return f"명목 또는 서열 척도 변수만 지원합니다: {', '.join(unsupported)}"
        if code == "insufficient_categories":
            return "교차분석에는 각 변수에 최소 2개 이상의 관측 범주가 필요합니다."
    elif step_type == "stats.correlation":
        if code == "dataset_empty":
            return "데이터셋이 비어 있어 상관분석을 실행할 수 없습니다."
        if code == "missing_variable":
            return f"데이터셋에 없는 변수: {', '.join(missing)}"
        if code == "unsupported_measure":
            return (
                f"상관분석 변수는 척도 또는 서열이어야 합니다: {', '.join(unsupported)}"
            )
        if code == "too_few_complete_pairs":
            return "상관분석은 변수쌍마다 최소 3개의 완전한 관측치가 필요합니다."
        if code == "non_numeric":
            return f"상관분석 변수는 숫자여야 합니다: {variable}"
        if code == "boolean_not_allowed":
            return f"상관분석 변수는 숫자여야 합니다: {variable}"
        if code == "non_finite":
            return f"상관분석 변수는 유한한 숫자여야 합니다: {variable}"
        if code == "zero_variance":
            return f"상관분석 변수는 0이 아닌 분산이 필요합니다: {variable}"
        if code == "pearson_requires_scale":
            return "Pearson correlation requires two scale variables."
    elif step_type == "stats.compare_groups":
        if code == "dataset_empty":
            return "CompareGroupsStep requires a non-empty dataset."
        if code == "role_collision":
            return (
                "CompareGroupsStep dependent variable and group variable must differ."
            )
        if code == "missing_variable":
            return f"Unknown columns requested: {sorted(missing)}"
        if code == "non_numeric":
            return "CompareGroupsStep dependent variable must be numeric."
        if code == "boolean_not_allowed":
            return "CompareGroupsStep dependent variable must be numeric."
        if code == "non_finite":
            return "CompareGroupsStep dependent variable must contain finite values."
        if code == "wrong_group_cardinality":
            return "CompareGroupsStep requires exactly two groups."
        if code == "group_too_small":
            return "CompareGroupsStep requires at least three valid cases per group."
        if code == "zero_variance":
            return "CompareGroupsStep requires non-zero variance in each group."
        if code == "duplicate_display_label":
            return "CompareGroupsStep group labels must be unique."
    elif step_type == "stats.paired_comparison":
        if code == "dataset_empty":
            return "PairedComparisonStep requires a non-empty dataset."
        if code == "role_collision":
            return "PairedComparisonStep before and after variables must differ."
        if code == "missing_variable":
            return f"Unknown columns requested: {sorted(missing)}"
        if code == "unsupported_measure":
            return "PairedComparisonStep before and after variables must be SCALE."
        if code == "non_numeric":
            return "PairedComparisonStep before and after variables must be numeric."
        if code == "boolean_not_allowed":
            return "PairedComparisonStep before and after variables must be numeric."
        if code == "non_finite":
            return "PairedComparisonStep before and after variables must contain finite values."
        if code == "too_few_complete_pairs":
            return "PairedComparisonStep requires at least three complete pairs."
        if code == "zero_paired_difference_variance":
            return (
                "PairedComparisonStep requires non-zero variance in paired differences."
            )
        if code == "duplicate_display_label":
            return "PairedComparisonStep labels must be unique."
    return f"Step input validation failed: {code}"


def raise_for_step_input_issues(
    step_type: str,
    issues: tuple[StepInputIssue, ...],
) -> None:
    """Translate shared issues back to each step's existing public error surface."""

    if not issues:
        return
    message = _message_for_issues(step_type, issues)
    if issues[0].code == "missing_variable" and step_type in {
        "stats.compare_groups",
        "stats.paired_comparison",
    }:
        raise StepInputValidationKeyError(message, issues)
    raise StepInputValidationError(message, issues)
