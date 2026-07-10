from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import math
from typing import TypeAlias

import numpy as np
import pandas as pd


ScalarValue: TypeAlias = bool | int | float | str


def _python_scalar(value: object) -> ScalarValue:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Value tokens require finite floats")
        return value
    if isinstance(value, str):
        return value
    raise ValueError("Value tokens support only bool, int, finite float, and str")


def _type_name(value: ScalarValue) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def canonical_value_token(value: object) -> str:
    scalar = _python_scalar(value)
    return json.dumps(
        {"type": _type_name(scalar), "value": scalar},
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def decode_value_token(token: str) -> ScalarValue:
    if not isinstance(token, str):
        raise ValueError("Value token must be a string")
    try:
        payload = json.loads(token)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError("Value token is not valid canonical JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"type", "value"}:
        raise ValueError("Value token must contain exactly type and value")

    kind = payload["type"]
    value = payload["value"]
    if kind == "bool" and type(value) is bool:
        scalar: ScalarValue = value
    elif kind == "int" and type(value) is int:
        scalar = value
    elif kind == "float" and type(value) is float and math.isfinite(value):
        scalar = value
    elif kind == "str" and type(value) is str:
        scalar = value
    else:
        raise ValueError("Value token type does not match its value")
    if canonical_value_token(scalar) != token:
        raise ValueError("Value token is not in canonical form")
    return scalar


def observed_value_options(dataset: object, variable_key: str) -> list[dict[str, str]]:
    key = str(variable_key).strip()
    frame = getattr(dataset, "df", None)
    variables = getattr(dataset, "variables", None)
    if not key or not isinstance(frame, pd.DataFrame) or key not in frame.columns:
        return []
    if not isinstance(variables, Mapping) or key not in variables:
        return []

    variable = variables[key]
    missing_values = getattr(variable, "missing_values", [])
    if not isinstance(missing_values, Sequence) or isinstance(missing_values, str):
        raise ValueError("Variable missing values must be a sequence")

    options: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_value in frame[key].tolist():
        if _is_missing(raw_value, missing_values):
            continue
        token = canonical_value_token(raw_value)
        if token in seen:
            continue
        scalar = decode_value_token(token)
        options.append(
            {
                "token": token,
                "label": _display_label(variable, scalar),
            }
        )
        seen.add(token)
    return options


def categorical_reference_options(
    dataset: object,
    predictor_keys: Sequence[str],
) -> list[dict[str, object]]:
    variables = getattr(dataset, "variables", None)
    if not isinstance(variables, Mapping):
        return []
    rows: list[dict[str, object]] = []
    for raw_key in predictor_keys:
        key = str(raw_key).strip()
        variable = variables.get(key)
        if variable is None:
            continue
        measure = getattr(variable, "measure", "")
        measure_value = str(getattr(measure, "value", measure))
        if measure_value not in {"nominal", "ordinal"}:
            continue
        try:
            levels = observed_value_options(dataset, key)
        except ValueError:
            levels = []
        rows.append({"variable": key, "levels": levels})
    return rows


def _is_missing(value: object, declared: Sequence[object]) -> bool:
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        missing = False
    if isinstance(missing, bool) and missing:
        return True
    for marker in declared:
        try:
            if bool(value == marker):
                return True
        except (TypeError, ValueError):
            continue
    return False


def _display_label(variable: object, value: ScalarValue) -> str:
    raw_label = _display_scalar(value)
    value_labels = getattr(variable, "value_labels", {})
    if (
        isinstance(value_labels, Mapping)
        and not isinstance(value, bool)
        and isinstance(value, int | float)
    ):
        metadata_label = value_labels.get(float(value))
        if metadata_label is not None and str(metadata_label).strip():
            return f"{metadata_label} ({raw_label})"
    return raw_label


def _display_scalar(value: ScalarValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
