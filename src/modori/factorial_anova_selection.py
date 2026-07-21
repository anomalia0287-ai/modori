from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
import math
from numbers import Real

import numpy as np
import pandas as pd

from modori.value_tokens import (
    complete_case_level_identities,
    decode_value_token,
    is_declared_missing,
    normalized_value_key,
    ordered_observed_value_options,
)


_FACTOR_MEASURES = {"nominal", "ordinal"}
_ROLES = {"outcome", "factor"}


def factorial_variable_options(
    dataset: object,
    role: str,
) -> list[dict[str, str]]:
    requested_role = str(role).strip()
    if requested_role not in _ROLES:
        raise ValueError("Factorial variable role must be outcome or factor")
    frame = getattr(dataset, "df", None)
    variables = getattr(dataset, "variables", None)
    if not isinstance(frame, pd.DataFrame) or not isinstance(variables, Mapping):
        return []

    rows: list[dict[str, str]] = []
    for raw_column in frame.columns:
        key = str(raw_column)
        variable = variables.get(key)
        if variable is None:
            continue
        measure = _measure(variable)
        if requested_role == "outcome":
            if measure != "scale" or not _is_finite_numeric_outcome(
                frame[key],
                getattr(variable, "missing_values", ()),
            ):
                continue
        else:
            if measure not in _FACTOR_MEASURES:
                continue
            try:
                levels = factorial_level_options(dataset, key)
            except ValueError:
                continue
            if not levels:
                continue
        rows.append({"key": key, "label": _variable_label(variable, key)})
    return rows


def factorial_level_options(
    dataset: object,
    variable_key: str,
    *,
    complete_case_keys: Sequence[str] | None = None,
) -> list[dict[str, str]]:
    key = str(variable_key).strip()
    variables = getattr(dataset, "variables", None)
    if not key or not isinstance(variables, Mapping):
        return []
    variable = variables.get(key)
    if variable is None or _measure(variable) not in _FACTOR_MEASURES:
        return []

    options = ordered_observed_value_options(dataset, key)
    if complete_case_keys is not None:
        identities = complete_case_level_identities(
            dataset,
            required_keys=complete_case_keys,
            factor_keys=(key,),
        )[key]
        options = [
            option
            for option in options
            if normalized_value_key(decode_value_token(option["token"])) in identities
        ]
    return options if 2 <= len(options) <= 6 else []


def _is_finite_numeric_outcome(
    series: pd.Series,
    missing_values: object,
) -> bool:
    if not isinstance(missing_values, Sequence) or isinstance(missing_values, str):
        return False
    observed = False
    for value in series.tolist():
        if is_declared_missing(value, missing_values):
            continue
        if isinstance(value, bool | np.bool_):
            return False
        if isinstance(value, Decimal):
            if not value.is_finite():
                return False
        elif isinstance(value, Real):
            if not math.isfinite(float(value)):
                return False
        else:
            return False
        observed = True
    return observed


def _measure(variable: object) -> str:
    measure = getattr(variable, "measure", "")
    return str(getattr(measure, "value", measure))


def _variable_label(variable: object, key: str) -> str:
    raw_label = getattr(variable, "label", None)
    label = "" if raw_label is None else str(raw_label).strip()
    if not label or label == key:
        return key
    return f"{label} ({key})"
