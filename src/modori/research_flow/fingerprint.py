"""Streaming, typed fingerprints for the full current local dataset."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import math
import struct
import unicodedata

import numpy as np
import pandas as pd

from modori.core.model import Dataset, Measure, Variable
from modori.research_flow.contracts import (
    FINGERPRINT_CONTRACT_ID,
    DatasetIdentity,
    ResearchFlowContractError,
)


FINGERPRINT_DEFAULT_MAX_CELLS = 5_000_000
FINGERPRINT_CANCELLATION_INTERVAL_CELLS = 8_192
FINGERPRINT_WORKER_DEADLINE_SECONDS = 10

_UINT64 = struct.Struct(">Q")
_FLOAT64 = struct.Struct(">d")
_DATASET_DOMAIN = b"full-current-dataset"
_SOURCE_SCHEMA_DOMAIN = b"source-schema"


class FingerprintContractError(ResearchFlowContractError):
    """Raised when an input has no valid typed fingerprint representation."""


class FingerprintLimitError(FingerprintContractError):
    """Raised before hashing a dataset that exceeds its fixed cell budget."""


class FingerprintCancelled(RuntimeError):
    """Raised without returning an identity when cancellation is requested."""


class FingerprintDeadlineExceeded(FingerprintCancelled):
    """Raised when the worker exceeds its fixed fingerprint time budget."""


def _canonical_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FingerprintContractError(f"{field_name} must be a non-empty string")
    if value != unicodedata.normalize("NFC", value):
        raise FingerprintContractError(f"{field_name} must use canonical NFC Unicode")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise FingerprintContractError(
            f"{field_name} must be valid UTF-8 text"
        ) from exc
    return value


def _normalized_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise FingerprintContractError(f"{field_name} must be a string")
    normalized = unicodedata.normalize("NFC", value)
    try:
        normalized.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise FingerprintContractError(
            f"{field_name} must be valid UTF-8 text"
        ) from exc
    return normalized


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _canonical_text(value, field_name)


def _optional_nonnegative_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FingerprintContractError(
            f"{field_name} must be a nonnegative integer or null"
        )
    return value


def _ordered_texts(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise FingerprintContractError(f"{field_name} must be a tuple")
    normalized = tuple(_canonical_text(item, f"{field_name} item") for item in value)
    if len(set(normalized)) != len(normalized):
        raise FingerprintContractError(f"{field_name} cannot contain duplicates")
    return normalized


@dataclass(frozen=True)
class SourceSchemaDescriptor:
    source_type: str
    sheet_name: str | None
    header_row_index: int | None
    header_row_count: int | None
    data_start_row_index: int | None
    source_columns: tuple[str, ...]
    included_columns: tuple[str, ...]

    def __post_init__(self) -> None:
        _canonical_text(self.source_type, "source_type")
        _optional_text(self.sheet_name, "sheet_name")
        _optional_nonnegative_int(self.header_row_index, "header_row_index")
        _optional_nonnegative_int(self.header_row_count, "header_row_count")
        _optional_nonnegative_int(
            self.data_start_row_index,
            "data_start_row_index",
        )
        source_columns = _ordered_texts(self.source_columns, "source_columns")
        included_columns = _ordered_texts(
            self.included_columns,
            "included_columns",
        )
        if not set(included_columns).issubset(source_columns):
            raise FingerprintContractError(
                "included_columns must be drawn from source_columns"
            )


def _frame(tag: bytes, payload: bytes) -> bytes:
    if len(tag) != 1:
        raise AssertionError("fingerprint type tags must be exactly one byte")
    if len(payload) > 0xFFFF_FFFF_FFFF_FFFF:
        raise FingerprintContractError("fingerprint payload exceeds uint64 length")
    return tag + _UINT64.pack(len(payload)) + payload


def _update_frame(hasher: object, tag: bytes, payload: bytes) -> None:
    hasher.update(_frame(tag, payload))  # type: ignore[attr-defined]


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return isinstance(missing, (bool, np.bool_)) and bool(missing)


def _is_declared_missing(value: object, missing_values: list[float]) -> bool:
    if _is_missing(value):
        return True
    for missing_value in missing_values:
        try:
            matches = value == missing_value
        except (TypeError, ValueError):
            continue
        if isinstance(matches, (bool, np.bool_)) and bool(matches):
            return True
    return False


def _timestamp_payload(value: pd.Timestamp | datetime) -> tuple[bytes, bytes]:
    timestamp = value if isinstance(value, pd.Timestamp) else pd.Timestamp(value)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return b"D", timestamp.isoformat().encode("ascii")
    normalized = timestamp.tz_convert(timezone.utc)
    return b"Z", normalized.isoformat().encode("ascii")


def _timedelta_nanoseconds(value: object) -> int:
    if isinstance(value, pd.Timedelta):
        return int(value.value)
    if isinstance(value, np.timedelta64):
        try:
            return int(value.astype("timedelta64[ns]").astype(np.int64))
        except (OverflowError, TypeError, ValueError) as exc:
            raise FingerprintContractError(
                "timedelta value cannot be represented as signed nanoseconds"
            ) from exc
    if isinstance(value, timedelta):
        return (
            value.days * 86_400_000_000_000
            + value.seconds * 1_000_000_000
            + value.microseconds * 1_000
        )
    raise AssertionError("unsupported timedelta type")


def _scalar_frame(value: object) -> bytes:
    if _is_missing(value):
        return _frame(b"M", b"")
    if isinstance(value, (bool, np.bool_)):
        return _frame(b"B", b"\x01" if bool(value) else b"\x00")
    if isinstance(value, (int, np.integer)):
        return _frame(b"I", str(int(value)).encode("ascii"))
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if math.isnan(number):
            return _frame(b"M", b"")
        if math.isinf(number):
            return _frame(b"P" if number > 0 else b"N", b"")
        if number == 0.0:
            number = 0.0
        return _frame(b"F", _FLOAT64.pack(number))
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFC", value)
        try:
            payload = normalized.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise FingerprintContractError(
                "text cell must be valid UTF-8 text"
            ) from exc
        return _frame(b"T", payload)
    if isinstance(value, np.datetime64):
        if np.isnat(value):
            return _frame(b"M", b"")
        tag, payload = _timestamp_payload(pd.Timestamp(value))
        return _frame(tag, payload)
    if isinstance(value, (pd.Timestamp, datetime)):
        tag, payload = _timestamp_payload(value)
        return _frame(tag, payload)
    if isinstance(value, date):
        return _frame(b"A", value.isoformat().encode("ascii"))
    if isinstance(value, (pd.Timedelta, np.timedelta64, timedelta)):
        nanoseconds = _timedelta_nanoseconds(value)
        return _frame(b"L", str(nanoseconds).encode("ascii"))
    raise FingerprintContractError(
        f"unsupported dataset cell type: {type(value).__name__}"
    )


def _new_hasher(domain: bytes):
    hasher = hashlib.sha256()
    hasher.update(FINGERPRINT_CONTRACT_ID.encode("ascii"))
    _update_frame(hasher, b"!", domain)
    return hasher


def _write_text(hasher: object, tag: bytes, value: object, field_name: str) -> None:
    text = _canonical_text(value, field_name)
    _update_frame(hasher, tag, text.encode("utf-8"))


def _write_optional_text(
    hasher: object,
    tag: bytes,
    value: object,
    field_name: str,
) -> None:
    if value is None:
        _update_frame(hasher, tag, _scalar_frame(None))
        return
    text = _normalized_text(value, field_name)
    _update_frame(hasher, tag, _scalar_frame(text))


def _write_optional_int(hasher: object, tag: bytes, value: int | None) -> None:
    _update_frame(hasher, tag, _scalar_frame(value))


def _write_text_sequence(
    hasher: object,
    tag: bytes,
    values: tuple[str, ...],
) -> None:
    _update_frame(hasher, tag, _UINT64.pack(len(values)))
    for value in values:
        _update_frame(hasher, b"e", _scalar_frame(value))


def _variable_metadata(
    hasher: object,
    variable_id: str,
    variable: Variable,
) -> None:
    if not isinstance(variable, Variable):
        raise FingerprintContractError(
            f"variable metadata for {variable_id!r} must be a Variable"
        )
    _write_text(hasher, b"n", variable_id, "variable ID")
    _write_text(hasher, b"v", variable.name, "variable name")
    _write_optional_text(hasher, b"l", variable.label, "variable label")
    if not isinstance(variable.measure, Measure):
        raise FingerprintContractError("variable measure must be a Measure value")
    _write_text(hasher, b"m", variable.measure.value, "variable measure")
    if not isinstance(variable.value_labels, Mapping):
        raise FingerprintContractError("variable value_labels must be a mapping")
    encoded_value_labels = sorted(
        (
            _scalar_frame(key),
            _scalar_frame(_normalized_text(label, "value label")),
        )
        for key, label in variable.value_labels.items()
    )
    _update_frame(hasher, b"k", _UINT64.pack(len(encoded_value_labels)))
    for encoded_key, encoded_label in encoded_value_labels:
        _update_frame(hasher, b"q", encoded_key)
        _update_frame(hasher, b"w", encoded_label)
    if not isinstance(variable.missing_values, list):
        raise FingerprintContractError("variable missing_values must be a list")
    _update_frame(hasher, b"x", _UINT64.pack(len(variable.missing_values)))
    for missing_value in variable.missing_values:
        _update_frame(hasher, b"y", _scalar_frame(missing_value))
    _write_text(hasher, b"t", variable.dtype, "variable dtype")


def _dataset_digest(
    dataset: Dataset,
    *,
    cancel_requested: Callable[[], bool],
) -> tuple[str, tuple[str, ...]]:
    hasher = _new_hasher(_DATASET_DOMAIN)
    row_count, column_count = dataset.df.shape
    if row_count > 0xFFFF_FFFF_FFFF_FFFF:
        raise FingerprintContractError("dataset row count exceeds uint64")
    if column_count > 0xFFFF_FFFF_FFFF_FFFF:
        raise FingerprintContractError("dataset column count exceeds uint64")
    _update_frame(hasher, b"r", _UINT64.pack(row_count))
    _update_frame(hasher, b"c", _UINT64.pack(column_count))

    variable_ids = tuple(str(column) for column in dataset.df.columns)
    validated_ids = _ordered_texts(variable_ids, "variable_ids")
    ordered_variables: list[Variable] = []
    for column, variable_id in zip(dataset.df.columns, validated_ids, strict=True):
        try:
            variable = dataset.variables[column]
        except KeyError as exc:
            raise FingerprintContractError(
                f"dataset is missing metadata for variable {variable_id!r}"
            ) from exc
        _variable_metadata(hasher, variable_id, variable)
        ordered_variables.append(variable)

    cell_index = 0
    for row in dataset.df.itertuples(index=False, name=None):
        for value, variable in zip(row, ordered_variables, strict=True):
            if (
                cell_index > 0
                and cell_index % FINGERPRINT_CANCELLATION_INTERVAL_CELLS == 0
            ):
                _raise_if_cancelled(cancel_requested)
            normalized_value = (
                None
                if variable.missing_values
                and _is_declared_missing(value, variable.missing_values)
                else value
            )
            hasher.update(_scalar_frame(normalized_value))
            cell_index += 1
    return hasher.hexdigest(), validated_ids


def _source_schema_digest(source_schema: SourceSchemaDescriptor) -> str:
    hasher = _new_hasher(_SOURCE_SCHEMA_DOMAIN)
    _write_text(hasher, b"s", source_schema.source_type, "source_type")
    _write_optional_text(hasher, b"h", source_schema.sheet_name, "sheet_name")
    _write_optional_int(hasher, b"i", source_schema.header_row_index)
    _write_optional_int(hasher, b"j", source_schema.header_row_count)
    _write_optional_int(hasher, b"d", source_schema.data_start_row_index)
    _write_text_sequence(hasher, b"o", source_schema.source_columns)
    _write_text_sequence(hasher, b"u", source_schema.included_columns)
    return hasher.hexdigest()


def _raise_if_cancelled(cancel_requested: Callable[[], bool]) -> None:
    if cancel_requested():
        raise FingerprintCancelled("dataset fingerprinting was cancelled")


def fingerprint_dataset(
    dataset: Dataset,
    source_schema: SourceSchemaDescriptor,
    *,
    pipeline_version: int,
    cancel_requested: Callable[[], bool],
    max_cells: int = FINGERPRINT_DEFAULT_MAX_CELLS,
) -> DatasetIdentity:
    """Return a full typed identity or raise without publishing a partial digest."""

    if not isinstance(dataset, Dataset):
        raise FingerprintContractError("dataset must be a Dataset")
    if not isinstance(source_schema, SourceSchemaDescriptor):
        raise FingerprintContractError("source_schema must be a SourceSchemaDescriptor")
    if (
        isinstance(pipeline_version, bool)
        or not isinstance(pipeline_version, int)
        or pipeline_version < 0
    ):
        raise FingerprintContractError("pipeline_version must be a nonnegative integer")
    if isinstance(max_cells, bool) or not isinstance(max_cells, int) or max_cells < 0:
        raise FingerprintContractError("max_cells must be a nonnegative integer")
    if not callable(cancel_requested):
        raise FingerprintContractError("cancel_requested must be callable")

    row_count, column_count = dataset.df.shape
    cell_count = row_count * column_count
    if cell_count > max_cells:
        raise FingerprintLimitError(
            f"dataset has {cell_count} cells, exceeding max_cells={max_cells}"
        )

    _raise_if_cancelled(cancel_requested)
    dataset_fingerprint, variable_ids = _dataset_digest(
        dataset,
        cancel_requested=cancel_requested,
    )
    source_schema_fingerprint = _source_schema_digest(source_schema)
    _raise_if_cancelled(cancel_requested)
    return DatasetIdentity(
        fingerprint_contract_id=FINGERPRINT_CONTRACT_ID,
        dataset_fingerprint=dataset_fingerprint,
        source_schema_fingerprint=source_schema_fingerprint,
        variable_ids=variable_ids,
        pipeline_version=pipeline_version,
    )
