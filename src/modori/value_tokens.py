from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
import json
import math
from typing import TypeAlias
import unicodedata

import numpy as np
import pandas as pd


ScalarValue: TypeAlias = bool | int | float | str


def display_label_key(label: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(label))
    visible = "".join(
        character
        for character in normalized
        if not unicodedata.category(character).startswith("C")
    )
    return " ".join(visible.split()).casefold()


def normalized_value_key(value: object) -> tuple[str, object]:
    scalar = _python_scalar(value)
    if isinstance(scalar, bool):
        return "boolean", scalar
    if isinstance(scalar, int | float):
        return "numeric", scalar
    return "string", scalar


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
    seen_labels: set[str] = set()
    for raw_value in frame[key].tolist():
        if is_declared_missing(raw_value, missing_values):
            continue
        token = canonical_value_token(raw_value)
        if token in seen:
            continue
        scalar = decode_value_token(token)
        label = display_value_label(variable, scalar)
        label_key = display_label_key(label)
        if not label_key:
            raise ValueError("Observed values have blank display labels")
        if label_key in seen_labels:
            raise ValueError("Observed values have ambiguous display labels")
        options.append(
            {
                "token": token,
                "label": label,
            }
        )
        seen.add(token)
        seen_labels.add(label_key)
    return options


def ordered_observed_value_options(
    dataset: object,
    variable_key: str,
) -> list[dict[str, str]]:
    """Return typed observed values in a row-order-independent factor order."""
    options = observed_value_options(dataset, variable_key)
    variables = getattr(dataset, "variables", None)
    if not options or not isinstance(variables, Mapping):
        return options
    variable = variables.get(str(variable_key).strip())
    if variable is None:
        return options
    return sorted(options, key=lambda row: _deterministic_option_key(variable, row))


def _deterministic_option_key(
    variable: object,
    option: Mapping[str, str],
) -> tuple[object, ...]:
    token = option["token"]
    value = decode_value_token(token)
    metadata_rank = _numeric_metadata_rank(variable, value)
    if metadata_rank is not None:
        return (0, metadata_rank, token)
    if isinstance(value, bool):
        return (1, int(value), token)
    if isinstance(value, int | float):
        type_rank = 0 if isinstance(value, int) else 1
        return (2, float(value), type_rank, token)
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return (3, normalized, token)


def _numeric_metadata_rank(variable: object, value: ScalarValue) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    value_labels = getattr(variable, "value_labels", {})
    if not isinstance(value_labels, Mapping):
        return None
    for index, (raw_key, raw_label) in enumerate(value_labels.items()):
        if not str(raw_label).strip() or isinstance(raw_key, bool):
            continue
        try:
            metadata_value = float(raw_key)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(metadata_value) and metadata_value == float(value):
            return index
    return None


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


def is_declared_missing(value: object, declared: Sequence[object]) -> bool:
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        missing = False
    if isinstance(missing, bool | np.bool_) and bool(missing):
        return True
    try:
        value_identity = _declared_missing_identity(value)
    except ValueError:
        return False
    for marker in declared:
        try:
            marker_identity = _declared_missing_identity(marker)
        except ValueError:
            continue
        if value_identity == marker_identity:
            return True
    return False


def _declared_missing_identity(value: object) -> tuple[str, object]:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bool):
        return "boolean", value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Missing-value identities require finite decimals")
        return "numeric", value
    if isinstance(value, int):
        return "numeric", Decimal(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Missing-value identities require finite floats")
        return "numeric", Decimal(str(value))
    if isinstance(value, str):
        return "string", value
    raise ValueError("Unsupported missing-value identity")


def complete_case_level_identities(
    dataset: object,
    *,
    required_keys: Sequence[str],
    factor_keys: Sequence[str],
) -> dict[str, set[tuple[str, object]]]:
    required = tuple(str(key).strip() for key in required_keys)
    factors = tuple(str(key).strip() for key in factor_keys)
    if (
        not required
        or not factors
        or any(not key for key in (*required, *factors))
        or len(set(required)) != len(required)
        or len(set(factors)) != len(factors)
        or not set(factors) <= set(required)
    ):
        raise ValueError("Complete-case keys must be distinct, non-empty, and nested")

    frame = getattr(dataset, "df", None)
    variables = getattr(dataset, "variables", None)
    if not isinstance(frame, pd.DataFrame) or not isinstance(variables, Mapping):
        raise ValueError("Complete-case identities require a dataset")
    if any(key not in frame.columns or key not in variables for key in required):
        raise ValueError("Complete-case identity keys must exist in the dataset")

    missing_values: dict[str, Sequence[object]] = {}
    for key in required:
        markers = getattr(variables[key], "missing_values", ())
        if not isinstance(markers, Sequence) or isinstance(markers, str):
            raise ValueError("Variable missing values must be a sequence")
        missing_values[key] = markers

    positions = {key: index for index, key in enumerate(required)}
    identities = {key: set() for key in factors}
    for row in frame.loc[:, list(required)].itertuples(index=False, name=None):
        if any(
            is_declared_missing(row[positions[key]], missing_values[key])
            for key in required
        ):
            continue
        for key in factors:
            identities[key].add(normalized_value_key(row[positions[key]]))
    return identities


def display_value_label(variable: object, value: ScalarValue) -> str:
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
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
