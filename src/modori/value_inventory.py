from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from modori.core import Measure

_MAX_RECODE_UNIQUE_VALUES = 200
_RECODE_SUFFIX = "_수정"

LABELLED_REASON = "값 라벨이 있는 변수는 아직 값 수정을 지원하지 않습니다."
MISSING_CODE_REASON = "결측 코드가 있는 변수는 아직 값 수정을 지원하지 않습니다."
MEASURE_REASON = "명목/순서 변수만 값 수정을 지원합니다."
NUMERIC_REASON = "숫자 변수는 아직 값 수정을 지원하지 않습니다."
TOO_MANY_VALUES_REASON = "고유값이 200개를 넘는 변수는 아직 값 수정을 지원하지 않습니다."


def value_recode_inventory(
    dataset: Any,
    *,
    suffix: str = _RECODE_SUFFIX,
    existing_steps: list[object] | None = None,
) -> list[dict[str, Any]]:
    if dataset is None:
        return []
    existing_params = _existing_map_values_params(existing_steps or [])
    inventory: list[dict[str, Any]] = []
    for column, variable in dataset.variables.items():
        column_key = str(column)
        reason = value_recode_ineligibility_reason(dataset, str(column))
        params = existing_params.get(column_key, {})
        mapping = _string_mapping(params.get("mapping", {}))
        to_missing = _string_set(params.get("to_missing", []))
        active_suffix = str(params.get("suffix", suffix) or suffix)
        values = (
            _value_counts(dataset.df[column], mapping=mapping, to_missing=to_missing)
            if reason is None
            else []
        )
        inventory.append(
            {
                "column": column_key,
                "label": str(variable.label or column),
                "eligible": reason is None,
                "reason": "" if reason is None else reason,
                "output": f"{column}{active_suffix}",
                "suffix": active_suffix,
                "values": values,
            }
        )
    return inventory


def value_recode_ineligibility_reason(dataset: Any, column: str) -> str | None:
    variable = dataset.variables[column]
    if variable.value_labels:
        return LABELLED_REASON
    if variable.missing_values:
        return MISSING_CODE_REASON
    series = dataset.df[column]
    if not (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
    ):
        return NUMERIC_REASON
    if variable.measure not in (Measure.NOMINAL, Measure.ORDINAL):
        return MEASURE_REASON
    if len(_value_counts(series)) > _MAX_RECODE_UNIQUE_VALUES:
        return TOO_MANY_VALUES_REASON
    return None


def _value_counts(
    series: pd.Series,
    *,
    mapping: Mapping[str, str] | None = None,
    to_missing: set[str] | None = None,
) -> list[dict[str, Any]]:
    mapping = mapping or {}
    to_missing = to_missing or set()
    counts: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    for position, raw in enumerate(series.dropna()):
        value = str(raw)
        if not value.strip():
            continue
        counts[value] = counts.get(value, 0) + 1
        first_seen.setdefault(value, position)
    return [
        {
            "value": value,
            "count": counts[value],
            "new_value": mapping.get(value, ""),
            "to_missing": value in to_missing,
        }
        for value in sorted(counts, key=lambda item: (-counts[item], first_seen[item]))
    ]


def _existing_map_values_params(steps: list[object]) -> dict[str, dict[str, Any]]:
    params_by_column: dict[str, dict[str, Any]] = {}
    for step in steps:
        if _step_type(step) != "recode.map_values":
            continue
        params = _step_params(step)
        column = str(params.get("column", "")).strip()
        if column:
            params_by_column[column] = params
    return params_by_column


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(mapped) for key, mapped in value.items()}


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value}


def _step_type(step: object) -> str:
    if isinstance(step, Mapping):
        return str(step.get("step_type", ""))
    return str(getattr(step, "step_type", ""))


def _step_params(step: object) -> dict[str, Any]:
    if isinstance(step, Mapping):
        params = step.get("params", {})
    else:
        params = getattr(step, "params", {})
    if isinstance(params, Mapping):
        return dict(params)
    return {}
