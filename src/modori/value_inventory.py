from __future__ import annotations

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


def value_recode_inventory(dataset: Any, *, suffix: str = _RECODE_SUFFIX) -> list[dict[str, Any]]:
    if dataset is None:
        return []
    inventory: list[dict[str, Any]] = []
    for column, variable in dataset.variables.items():
        reason = value_recode_ineligibility_reason(dataset, str(column))
        values = _value_counts(dataset.df[column]) if reason is None else []
        inventory.append(
            {
                "column": str(column),
                "label": str(variable.label or column),
                "eligible": reason is None,
                "reason": "" if reason is None else reason,
                "output": f"{column}{suffix}",
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


def _value_counts(series: pd.Series) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    for position, raw in enumerate(series.dropna()):
        value = str(raw)
        if not value.strip():
            continue
        counts[value] = counts.get(value, 0) + 1
        first_seen.setdefault(value, position)
    return [
        {"value": value, "count": counts[value]}
        for value in sorted(counts, key=lambda item: (-counts[item], first_seen[item]))
    ]
