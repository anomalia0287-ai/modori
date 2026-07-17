from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
from enum import Enum

import numpy as np
import pandas as pd
import pytest

from modori.core.model import Dataset, Measure, Variable
from modori.research_flow import (
    FINGERPRINT_CANCELLATION_INTERVAL_CELLS,
    FINGERPRINT_DEFAULT_MAX_CELLS,
    FINGERPRINT_WORKER_DEADLINE_SECONDS,
    FingerprintCancelled,
    FingerprintContractError,
    FingerprintLimitError,
    SourceSchemaDescriptor,
    fingerprint_dataset,
)


def _variable(
    name: str,
    *,
    label: str | None = None,
    measure: Measure = Measure.SCALE,
    value_labels: dict[float, str] | None = None,
    missing_values: list[float] | None = None,
    dtype: str = "object",
    origin_step_id: str | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=label,
        measure=measure,
        value_labels={} if value_labels is None else value_labels,
        missing_values=[] if missing_values is None else missing_values,
        dtype=dtype,
        origin_step_id=origin_step_id,
    )


def _source_schema(**overrides: object) -> SourceSchemaDescriptor:
    values: dict[str, object] = {
        "source_type": "xlsx",
        "sheet_name": "응답",
        "header_row_index": 0,
        "header_row_count": 1,
        "data_start_row_index": 1,
        "source_columns": (
            "flag",
            "integer",
            "float",
            "text",
            "naive_date",
            "utc_date",
            "duration",
            "category",
        ),
        "included_columns": (
            "flag",
            "integer",
            "float",
            "text",
            "naive_date",
            "utc_date",
            "duration",
            "category",
        ),
    }
    values.update(overrides)
    return SourceSchemaDescriptor(**values)  # type: ignore[arg-type]


def _typed_dataset() -> Dataset:
    frame = pd.DataFrame(
        {
            "flag": pd.Series([True, False, pd.NA], dtype="boolean"),
            "integer": pd.Series([1, -2, pd.NA], dtype="Int64"),
            "float": pd.Series([1.25, -0.0, np.nan], dtype="float64"),
            "text": pd.Series(["é", "plain", None], dtype="object"),
            "naive_date": pd.Series(
                [
                    pd.Timestamp("2025-01-02 03:04:05.123456789"),
                    pd.Timestamp("2025-02-03"),
                    pd.NaT,
                ]
            ),
            "utc_date": pd.Series(
                pd.to_datetime(
                    ["2025-01-02T03:04:05Z", "2025-02-03T04:05:06Z", None],
                    utc=True,
                )
            ),
            "duration": pd.Series(
                [pd.Timedelta("1 days 2 ns"), timedelta(seconds=-2), pd.NaT]
            ),
            "category": pd.Series(pd.Categorical(["control", "treatment", None])),
        }
    )
    variables = {
        "flag": _variable(
            "flag",
            label="동의",
            measure=Measure.NOMINAL,
            value_labels={0.0: "아니요", 1.0: "예"},
            dtype="boolean",
        ),
        "integer": _variable(
            "integer",
            label="횟수",
            value_labels={1.0: "한 번", -2.0: "음수"},
            missing_values=[99.0, -99.0],
            dtype="Int64",
        ),
        "float": _variable("float", label="점수", dtype="float64"),
        "text": _variable("text", label="설명", measure=Measure.NOMINAL),
        "naive_date": _variable("naive_date", dtype="datetime64[ns]"),
        "utc_date": _variable("utc_date", dtype="datetime64[ns, UTC]"),
        "duration": _variable("duration", dtype="timedelta64[ns]"),
        "category": _variable(
            "category",
            label="조건",
            measure=Measure.NOMINAL,
            value_labels={0.0: "통제", 1.0: "처치"},
            dtype="category",
        ),
    }
    return Dataset(df=frame, variables=variables)


def _fingerprint(
    dataset: Dataset,
    source_schema: SourceSchemaDescriptor | None = None,
    *,
    pipeline_version: int = 7,
):
    return fingerprint_dataset(
        dataset,
        _source_schema() if source_schema is None else source_schema,
        pipeline_version=pipeline_version,
        cancel_requested=lambda: False,
    )


def _one_cell(value: object, *, dtype: str = "object") -> Dataset:
    return Dataset(
        df=pd.DataFrame({"value": pd.Series([value], dtype="object")}),
        variables={"value": _variable("value", dtype=dtype)},
    )


def test_typed_dataset_fingerprint_is_deterministic_and_preserves_column_order() -> (
    None
):
    dataset = _typed_dataset()

    first = _fingerprint(dataset)
    second = _fingerprint(dataset)

    assert first == second
    assert first.variable_ids == tuple(str(column) for column in dataset.df.columns)
    assert first.pipeline_version == 7
    assert len(first.dataset_fingerprint) == 64
    assert len(first.source_schema_fingerprint) == 64


def test_v1_golden_vector_prevents_silent_fingerprint_reinterpretation() -> None:
    source = SourceSchemaDescriptor(
        source_type="synthetic",
        sheet_name=None,
        header_row_index=None,
        header_row_count=None,
        data_start_row_index=None,
        source_columns=("value",),
        included_columns=("value",),
    )
    identity = fingerprint_dataset(
        _one_cell(1),
        source,
        pipeline_version=3,
        cancel_requested=lambda: False,
    )

    assert (
        identity.dataset_fingerprint
        == "fb87e634eba20664cfaf3cc8ba8023fc7aaf32ea6b47dea1436288a97459556b"
    )
    assert (
        identity.source_schema_fingerprint
        == "d61edebf400b0421c299e5e6aeb14691fa0952787668717fe956827d297e2686"
    )


def test_row_and_column_order_are_part_of_current_dataset_identity() -> None:
    dataset = _typed_dataset()
    first = _fingerprint(dataset)
    row_reordered = Dataset(
        df=dataset.df.iloc[[1, 0, 2]].reset_index(drop=True),
        variables=dataset.variables,
    )
    reversed_columns = list(reversed(dataset.df.columns))
    column_reordered = Dataset(
        df=dataset.df.loc[:, reversed_columns],
        variables=dataset.variables,
    )

    assert _fingerprint(row_reordered).dataset_fingerprint != first.dataset_fingerprint
    assert (
        _fingerprint(column_reordered).dataset_fingerprint != first.dataset_fingerprint
    )


def test_nfc_equivalent_text_and_positive_zero_are_semantically_identical() -> None:
    dataset = _typed_dataset()
    equivalent_frame = dataset.df.copy(deep=True)
    equivalent_frame.loc[0, "text"] = "e\u0301"
    equivalent_frame.loc[1, "float"] = 0.0
    original_frame = dataset.df.copy(deep=True)
    original_frame.loc[1, "float"] = -0.0

    assert (
        _fingerprint(
            Dataset(df=equivalent_frame, variables=dataset.variables)
        ).dataset_fingerprint
        == _fingerprint(
            Dataset(df=original_frame, variables=dataset.variables)
        ).dataset_fingerprint
    )


def test_metadata_changes_identity_but_origin_step_bookkeeping_does_not() -> None:
    dataset = _typed_dataset()
    label_variables = dict(dataset.variables)
    label_variables["float"] = replace(label_variables["float"], label="다른 점수")
    origin_variables = dict(dataset.variables)
    origin_variables["float"] = replace(
        origin_variables["float"],
        origin_step_id="step-that-must-not-bind",
    )

    baseline = _fingerprint(dataset).dataset_fingerprint
    assert (
        _fingerprint(
            Dataset(df=dataset.df, variables=label_variables)
        ).dataset_fingerprint
        != baseline
    )
    assert (
        _fingerprint(
            Dataset(df=dataset.df, variables=origin_variables)
        ).dataset_fingerprint
        == baseline
    )


def test_descriptive_labels_allow_empty_text_and_normalize_nfc() -> None:
    dataset = _typed_dataset()
    nfd_variables = dict(dataset.variables)
    nfd_variables["integer"] = replace(
        nfd_variables["integer"],
        label="e\u0301",
        value_labels={1.0: "e\u0301", -2.0: ""},
    )
    nfc_variables = dict(dataset.variables)
    nfc_variables["integer"] = replace(
        nfc_variables["integer"],
        label="é",
        value_labels={1.0: "é", -2.0: ""},
    )

    assert (
        _fingerprint(
            Dataset(df=dataset.df, variables=nfd_variables)
        ).dataset_fingerprint
        == _fingerprint(
            Dataset(df=dataset.df, variables=nfc_variables)
        ).dataset_fingerprint
    )


def test_value_label_map_order_is_canonical_but_missing_code_order_is_bound() -> None:
    dataset = _typed_dataset()
    canonical_variables = dict(dataset.variables)
    canonical_variables["integer"] = replace(
        canonical_variables["integer"],
        value_labels={-2.0: "음수", 1.0: "한 번"},
    )
    reordered_missing = dict(dataset.variables)
    reordered_missing["integer"] = replace(
        reordered_missing["integer"],
        missing_values=[-99.0, 99.0],
    )

    baseline = _fingerprint(dataset).dataset_fingerprint
    assert (
        _fingerprint(
            Dataset(df=dataset.df, variables=canonical_variables)
        ).dataset_fingerprint
        == baseline
    )
    assert (
        _fingerprint(
            Dataset(df=dataset.df, variables=reordered_missing)
        ).dataset_fingerprint
        != baseline
    )


@pytest.mark.parametrize(
    ("left", "right"),
    (
        (True, 1),
        (1, 1.0),
        (float("inf"), float("-inf")),
        (date(2025, 1, 2), "2025-01-02"),
        (datetime(2025, 1, 2), date(2025, 1, 2)),
        (timedelta(seconds=1), 1_000_000_000),
    ),
)
def test_typed_values_do_not_alias(left: object, right: object) -> None:
    source = SourceSchemaDescriptor(
        source_type="synthetic",
        sheet_name=None,
        header_row_index=None,
        header_row_count=None,
        data_start_row_index=None,
        source_columns=("value",),
        included_columns=("value",),
    )

    assert (
        _fingerprint(_one_cell(left), source).dataset_fingerprint
        != _fingerprint(_one_cell(right), source).dataset_fingerprint
    )


@pytest.mark.parametrize("missing", (None, np.nan, pd.NA, pd.NaT))
def test_all_missing_representations_share_one_marker(missing: object) -> None:
    source = SourceSchemaDescriptor(
        source_type="synthetic",
        sheet_name=None,
        header_row_index=None,
        header_row_count=None,
        data_start_row_index=None,
        source_columns=("value",),
        included_columns=("value",),
    )

    assert (
        _fingerprint(_one_cell(missing), source).dataset_fingerprint
        == _fingerprint(_one_cell(None), source).dataset_fingerprint
    )


def test_declared_missing_code_uses_the_same_normalized_missing_mask() -> None:
    source = SourceSchemaDescriptor(
        source_type="synthetic",
        sheet_name=None,
        header_row_index=None,
        header_row_count=None,
        data_start_row_index=None,
        source_columns=("value",),
        included_columns=("value",),
    )
    variable = _variable(
        "value",
        missing_values=[99.0],
        dtype="object",
    )
    coded = Dataset(
        df=pd.DataFrame({"value": pd.Series([99], dtype="object")}),
        variables={"value": variable},
    )
    native = Dataset(
        df=pd.DataFrame({"value": pd.Series([np.nan], dtype="object")}),
        variables={"value": variable},
    )

    assert (
        _fingerprint(coded, source).dataset_fingerprint
        == _fingerprint(native, source).dataset_fingerprint
    )


def test_aware_datetimes_are_canonicalized_to_the_same_utc_instant() -> None:
    utc = datetime(2025, 1, 2, 3, tzinfo=timezone.utc)
    same_instant = datetime(
        2025,
        1,
        2,
        12,
        tzinfo=timezone(timedelta(hours=9)),
    )
    source = SourceSchemaDescriptor(
        source_type="synthetic",
        sheet_name=None,
        header_row_index=None,
        header_row_count=None,
        data_start_row_index=None,
        source_columns=("value",),
        included_columns=("value",),
    )

    assert (
        _fingerprint(_one_cell(utc), source).dataset_fingerprint
        == _fingerprint(_one_cell(same_instant), source).dataset_fingerprint
    )


@pytest.mark.parametrize(
    "changed_source",
    (
        _source_schema(source_type="csv"),
        _source_schema(sheet_name="다른 시트"),
        _source_schema(header_row_index=2),
        _source_schema(
            source_columns=(
                "integer",
                "flag",
                "float",
                "text",
                "naive_date",
                "utc_date",
                "duration",
                "category",
            )
        ),
        _source_schema(included_columns=("integer", "flag", "float")),
    ),
)
def test_source_descriptor_changes_only_source_schema_identity(
    changed_source: SourceSchemaDescriptor,
) -> None:
    dataset = _typed_dataset()
    baseline = _fingerprint(dataset, _source_schema())
    changed = _fingerprint(dataset, changed_source)

    assert changed.dataset_fingerprint == baseline.dataset_fingerprint
    assert changed.source_schema_fingerprint != baseline.source_schema_fingerprint


def test_source_schema_descriptor_has_no_path_and_is_frozen() -> None:
    descriptor = _source_schema()

    assert tuple(descriptor.__dataclass_fields__) == (
        "source_type",
        "sheet_name",
        "header_row_index",
        "header_row_count",
        "data_start_row_index",
        "source_columns",
        "included_columns",
    )
    assert "path" not in descriptor.__dataclass_fields__
    assert "filename" not in descriptor.__dataclass_fields__
    with pytest.raises(FrozenInstanceError):
        descriptor.source_type = "csv"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"source_type": ""}, "source_type"),
        ({"source_type": "e\u0301"}, "NFC"),
        ({"sheet_name": ""}, "sheet_name"),
        ({"header_row_index": True}, "header_row_index"),
        ({"header_row_count": -1}, "header_row_count"),
        ({"data_start_row_index": 1.0}, "data_start_row_index"),
        ({"source_columns": ["flag"]}, "source_columns"),
        ({"source_columns": ("flag", "flag")}, "source_columns"),
        ({"included_columns": ("missing",)}, "included_columns"),
        ({"included_columns": ("flag", "flag")}, "included_columns"),
    ),
)
def test_source_schema_descriptor_rejects_malformed_values(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(FingerprintContractError, match=message):
        _source_schema(**overrides)


def test_fingerprint_cancels_before_work_and_before_final_publication() -> None:
    dataset = _typed_dataset()
    with pytest.raises(FingerprintCancelled):
        fingerprint_dataset(
            dataset,
            _source_schema(),
            pipeline_version=2,
            cancel_requested=lambda: True,
        )

    calls = 0

    def cancel_before_publication() -> bool:
        nonlocal calls
        calls += 1
        return calls == 2

    with pytest.raises(FingerprintCancelled):
        fingerprint_dataset(
            dataset,
            _source_schema(),
            pipeline_version=2,
            cancel_requested=cancel_before_publication,
        )

    assert calls == 2


def test_cancellation_is_checked_at_least_once_per_8192_cells() -> None:
    row_count = FINGERPRINT_CANCELLATION_INTERVAL_CELLS * 2 + 1
    dataset = Dataset(
        df=pd.DataFrame({"value": np.arange(row_count, dtype=np.int64)}),
        variables={"value": _variable("value", dtype="int64")},
    )
    source = SourceSchemaDescriptor(
        source_type="synthetic",
        sheet_name=None,
        header_row_index=None,
        header_row_count=None,
        data_start_row_index=None,
        source_columns=("value",),
        included_columns=("value",),
    )
    calls = 0

    def never_cancel() -> bool:
        nonlocal calls
        calls += 1
        return False

    fingerprint_dataset(
        dataset,
        source,
        pipeline_version=2,
        cancel_requested=never_cancel,
    )

    assert calls >= 4


def test_resource_limit_blocks_before_encoding() -> None:
    dataset = Dataset(
        df=pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}),
        variables={
            "a": _variable("a", dtype="int64"),
            "b": _variable("b", dtype="int64"),
        },
    )
    source = SourceSchemaDescriptor(
        source_type="synthetic",
        sheet_name=None,
        header_row_index=None,
        header_row_count=None,
        data_start_row_index=None,
        source_columns=("a", "b"),
        included_columns=("a", "b"),
    )

    with pytest.raises(FingerprintLimitError, match="5"):
        fingerprint_dataset(
            dataset,
            source,
            pipeline_version=2,
            cancel_requested=lambda: False,
            max_cells=5,
        )


def test_public_limits_remain_frozen() -> None:
    assert FINGERPRINT_DEFAULT_MAX_CELLS == 5_000_000
    assert FINGERPRINT_CANCELLATION_INTERVAL_CELLS == 8_192
    assert FINGERPRINT_WORKER_DEADLINE_SECONDS == 10


@pytest.mark.parametrize(
    ("pipeline_version", "max_cells", "callback", "message"),
    (
        (True, 5_000_000, lambda: False, "pipeline_version"),
        (-1, 5_000_000, lambda: False, "pipeline_version"),
        (1, True, lambda: False, "max_cells"),
        (1, -1, lambda: False, "max_cells"),
        (1, 5_000_000, None, "cancel_requested"),
    ),
)
def test_fingerprint_rejects_invalid_control_arguments(
    pipeline_version: object,
    max_cells: object,
    callback: object,
    message: str,
) -> None:
    with pytest.raises(FingerprintContractError, match=message):
        fingerprint_dataset(
            _typed_dataset(),
            _source_schema(),
            pipeline_version=pipeline_version,  # type: ignore[arg-type]
            cancel_requested=callback,  # type: ignore[arg-type]
            max_cells=max_cells,  # type: ignore[arg-type]
        )


def test_unsupported_cell_type_fails_instead_of_stringifying() -> None:
    with pytest.raises(FingerprintContractError, match="unsupported"):
        _fingerprint(_one_cell(b"not text"))


def test_foreign_enum_cannot_impersonate_a_measure() -> None:
    class ForeignMeasure(str, Enum):
        SCALE = "scale"

    dataset = _typed_dataset()
    variables = dict(dataset.variables)
    variables["float"] = replace(
        variables["float"],
        measure=ForeignMeasure.SCALE,  # type: ignore[arg-type]
    )

    with pytest.raises(FingerprintContractError, match="measure"):
        _fingerprint(Dataset(df=dataset.df, variables=variables))
