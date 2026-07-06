import pandas as pd
import pyreadstat
import pytest

from modori.core import Dataset, Measure, Pipeline, Variable
from modori.steps import ComposeScaleStep, ImportStep, RecodeReverseStep


def scale_variable(
    name: str,
    *,
    value_labels: dict[float, str] | None = None,
    missing_values: list[float] | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=Measure.SCALE,
        value_labels=value_labels or {},
        missing_values=missing_values or [],
        dtype="float",
        origin_step_id=None,
    )


def likert_dataset() -> Dataset:
    return Dataset(
        df=pd.DataFrame(
            {
                "q1": [5.0, 4.0, 99.0],
                "q2": [4.0, 4.0, 4.0],
                "q3": [1.0, 2.0, 3.0],
                "q4": [5.0, 99.0, 5.0],
                "q5": [4.0, 4.0, 4.0],
            }
        ),
        variables={
            "q1": scale_variable("q1", missing_values=[99.0]),
            "q2": scale_variable("q2"),
            "q3": scale_variable(
                "q3",
                value_labels={
                    1.0: "strongly disagree",
                    2.0: "disagree",
                    3.0: "neutral",
                    4.0: "agree",
                    5.0: "strongly agree",
                },
            ),
            "q4": scale_variable("q4", missing_values=[99.0]),
            "q5": scale_variable("q5"),
        },
    )


def test_import_step_reads_csv_into_dataset_with_metadata_and_notes(tmp_path) -> None:
    path = tmp_path / "survey.csv"
    path.write_text("q1,q2,group\n1,2,1\n3,,2\n", encoding="utf-8")
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(path), "file_type": "csv"},
        )
    )

    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df.columns.tolist() == ["q1", "q2", "group"]
    assert pipeline.current_dataset.df.shape == (2, 3)
    assert pipeline.current_dataset.variables["q1"].measure is Measure.ORDINAL
    assert pipeline.current_dataset.variables["group"].origin_step_id == "import"
    assert pipeline.step_results["import"].notes == [
        "Imported 2 rows, 3 columns, and 1 missing cells."
    ]


def test_import_step_includes_public_data_loader_warnings_in_notes(tmp_path) -> None:
    path = tmp_path / "public-with-preamble.csv"
    path.write_text(
        "\n".join(
            [
                "서울시 인구 현황",
                "자료기준일: 2024-12-31",
                "단위: 명",
                "자치구,연도,인구",
                "종로구,2024,140000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(path), "file_type": "csv"},
        )
    )

    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df.columns.tolist() == ["자치구", "연도", "인구"]
    assert pipeline.step_results["import"].notes == [
        "Imported 1 rows, 3 columns, and 0 missing cells.",
        "표 헤더 앞의 안내 행 3개를 건너뛰었습니다.",
    ]


def test_import_step_applies_table_layout_override_params(tmp_path) -> None:
    path = tmp_path / "manual-layout.csv"
    path.write_text(
        "\n".join(
            [
                "다운로드 조건,2026-07-06",
                "이 행은 표가 아닙니다,확인용",
                "city,value",
                "Seoul,10",
                "Busan,20",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    import_step = ImportStep(
        id="import",
        title="Import CSV",
        params={
            "path": str(path),
            "file_type": "csv",
            "table_layout": {
                "header_row_index": 2,
                "header_row_count": 1,
            },
        },
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(import_step)

    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df.columns.tolist() == ["city", "value"]
    assert pipeline.current_dataset.df.to_dict(orient="records") == [
        {"city": "Seoul", "value": 10},
        {"city": "Busan", "value": 20},
    ]
    assert import_step.writes() == {"city", "value"}
    assert "사용자 지정 표 레이아웃을 적용했습니다." in pipeline.step_results["import"].notes


def test_import_step_drops_aggregate_rows_when_requested(tmp_path) -> None:
    path = tmp_path / "aggregate-row.csv"
    path.write_text(
        "\n".join(
            [
                "지역,인구",
                "합 계,300",
                "종로구,100",
                "중구,200",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={
                "path": str(path),
                "file_type": "csv",
                "drop_aggregate_rows": True,
            },
        )
    )

    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df.to_dict(orient="records") == [
        {"지역": "종로구", "인구": 100},
        {"지역": "중구", "인구": 200},
    ]
    assert pipeline.step_results["import"].notes == [
        "Imported 2 rows, 2 columns, and 0 missing cells.",
        "집계/합계 행 1개를 제외했습니다.",
    ]


def test_pipeline_rejects_duplicate_dynamic_import_writes_at_recompute(
    tmp_path,
) -> None:
    path = tmp_path / "survey.csv"
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import-a",
            title="Import CSV A",
            params={"path": str(path), "file_type": "csv"},
        )
    )
    pipeline.add(
        ImportStep(
            id="import-b",
            title="Import CSV B",
            params={"path": str(path), "file_type": "csv"},
        )
    )
    path.write_text("q1\n1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate Step write key: q1"):
        pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df.empty
    assert pipeline.step_results == {}


def test_import_step_writes_reads_only_csv_header(tmp_path, monkeypatch) -> None:
    path = tmp_path / "survey.csv"
    path.write_text("q1,q2\n1,2\n3,4\n", encoding="utf-8")
    calls = []

    def read_csv_spy(path_arg, *args, **kwargs):
        calls.append(kwargs)
        assert kwargs.get("nrows") == 0
        return pd.DataFrame(columns=["q1", "q2"])

    monkeypatch.setattr("modori.steps.data_prep.pd.read_csv", read_csv_spy)
    step = ImportStep(
        id="import",
        title="Import CSV",
        params={"path": str(path), "file_type": "csv"},
    )

    assert step.writes() == {"q1", "q2"}
    assert calls == [{"nrows": 0}]


def test_import_step_writes_reads_only_xlsx_header(tmp_path, monkeypatch) -> None:
    path = tmp_path / "survey.xlsx"
    path.write_bytes(b"not used by monkeypatched reader")
    calls = []

    def read_excel_spy(path_arg, *args, **kwargs):
        calls.append(kwargs)
        assert kwargs.get("nrows") == 0
        return pd.DataFrame(columns=["q1", "q2"])

    monkeypatch.setattr("modori.steps.data_prep.pd.read_excel", read_excel_spy)
    step = ImportStep(
        id="import",
        title="Import XLSX",
        params={"path": str(path), "file_type": "xlsx"},
    )

    assert step.writes() == {"q1", "q2"}
    assert calls == [{"nrows": 0, "header": 0}]


def test_import_step_writes_reads_only_sav_metadata(tmp_path, monkeypatch) -> None:
    path = tmp_path / "survey.sav"
    path.write_bytes(b"not used by monkeypatched reader")
    calls = []

    class Metadata:
        column_names = ["q1", "q2"]

    def read_sav_spy(path_arg, *args, **kwargs):
        calls.append(kwargs)
        assert kwargs.get("metadataonly") is True
        return pd.DataFrame(), Metadata()

    monkeypatch.setattr(pyreadstat, "read_sav", read_sav_spy)
    step = ImportStep(
        id="import",
        title="Import SAV",
        params={"path": str(path), "file_type": "sav"},
    )

    assert step.writes() == {"q1", "q2"}
    assert calls == [{"metadataonly": True, "user_missing": True}]


def test_import_step_reads_xlsx(tmp_path) -> None:
    path = tmp_path / "survey.xlsx"
    pd.DataFrame({"q1": [1, 2], "q2": [3, 4]}).to_excel(path, index=False)
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import XLSX",
            params={"path": str(path), "file_type": "xlsx"},
        )
    )

    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df.to_dict(orient="list") == {
        "q1": [1, 2],
        "q2": [3, 4],
    }


def test_import_step_reads_sav_metadata(tmp_path) -> None:
    path = tmp_path / "survey.sav"
    pyreadstat.write_sav(
        pd.DataFrame({"group": [1.0, 2.0, 99.0]}),
        path,
        column_labels={"group": "Treatment group"},
        variable_value_labels={"group": {1.0: "control", 2.0: "treatment"}},
        missing_ranges={"group": [99.0]},
        variable_measure={"group": "nominal"},
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import SAV",
            params={"path": str(path), "file_type": "sav"},
        )
    )

    pipeline.recompute(dirty_from=None)

    group = pipeline.current_dataset.variables["group"]
    assert group.label == "Treatment group"
    assert group.measure is Measure.NOMINAL
    assert group.value_labels == {1.0: "control", 2.0: "treatment"}
    assert group.missing_values == [99.0]


def test_import_step_treats_unknown_sav_measure_as_inferred_measure(
    tmp_path,
    monkeypatch,
) -> None:
    path = tmp_path / "survey.sav"
    path.write_bytes(b"not used by monkeypatched reader")

    class Metadata:
        column_labels = ["Score"]
        variable_value_labels = {}
        missing_ranges = {}
        variable_measure = {"score": "unknown"}

    def read_table_spy(path_arg, file_type):
        return pd.DataFrame({"score": [1.1, 2.2, 3.3]}), Metadata()

    monkeypatch.setattr("modori.steps.data_prep.read_table", read_table_spy)
    monkeypatch.setattr(
        "modori.steps.data_prep.read_columns",
        lambda path_arg, file_type: ["score"],
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import SAV",
            params={"path": str(path), "file_type": "sav"},
        )
    )

    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.variables["score"].measure is Measure.SCALE


def test_metadata_variables_treats_unknown_sav_measure_as_inferred_measure() -> None:
    from modori.steps.data_prep import metadata_variables

    class Metadata:
        column_labels = []
        variable_value_labels = {}
        missing_ranges = {}
        variable_measure = {"score": "unknown", "group": "unknown"}

    frame = pd.DataFrame({"score": [1, 2, 3], "group": ["a", "b", "a"]})

    variables = metadata_variables(frame, origin_step_id="preview", metadata=Metadata())

    assert variables["score"].measure is Measure.ORDINAL
    assert variables["group"].measure is Measure.NOMINAL


def test_import_step_rejects_sav_missing_ranges_that_are_not_point_codes(
    tmp_path,
    monkeypatch,
) -> None:
    path = tmp_path / "survey.sav"
    path.write_bytes(b"not used by monkeypatched reader")

    class Metadata:
        column_labels = ["Satisfaction"]
        variable_value_labels = {}
        missing_ranges = {"score": [{"lo": 90.0, "hi": 99.0}]}
        variable_measure = {"score": "scale"}

    def read_table_spy(path_arg, file_type):
        return pd.DataFrame({"score": [1.0, 95.0]}), Metadata()

    monkeypatch.setattr("modori.steps.data_prep.read_table", read_table_spy)
    monkeypatch.setattr(
        "modori.steps.data_prep.read_columns",
        lambda path_arg, file_type: ["score"],
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import SAV",
            params={"path": str(path), "file_type": "sav"},
        )
    )

    with pytest.raises(ValueError, match="SPSS missing value ranges are not supported"):
        pipeline.recompute(dirty_from=None)


def test_reverse_recode_preserves_original_and_reverses_value_labels() -> None:
    step = RecodeReverseStep(
        id="reverse",
        title="Reverse q3",
        params={"columns": ["q3"], "scale_min": 1, "scale_max": 5},
    )

    result = step.compute_context_free(likert_dataset())

    assert result.new_columns["q3_R"].tolist() == [5.0, 4.0, 3.0]
    assert likert_dataset().df["q3"].tolist() == [1.0, 2.0, 3.0]
    assert result.new_variables["q3_R"].value_labels == {
        5.0: "strongly disagree",
        4.0: "disagree",
        3.0: "neutral",
        2.0: "agree",
        1.0: "strongly agree",
    }
    assert step.reads() == {"q3"}
    assert step.writes() == {"q3_R"}


def test_reverse_recode_treats_declared_missing_codes_as_nan() -> None:
    dataset = Dataset(
        df=pd.DataFrame({"q3": [1.0, 99.0]}),
        variables={
            "q3": scale_variable(
                "q3",
                value_labels={1.0: "low", 5.0: "high"},
                missing_values=[99.0],
            )
        },
    )
    step = RecodeReverseStep(
        id="reverse",
        title="Reverse q3",
        params={"columns": ["q3"], "scale_min": 1, "scale_max": 5},
    )

    result = step.compute_context_free(dataset)

    assert result.new_columns["q3_R"].iloc[0] == 5.0
    assert pd.isna(result.new_columns["q3_R"].iloc[1])
    assert result.new_variables["q3_R"].missing_values == []


def test_reverse_recode_rejects_invalid_scale_range() -> None:
    step = RecodeReverseStep(
        id="reverse",
        title="Reverse q3",
        params={"columns": ["q3"], "scale_min": 5, "scale_max": 1},
    )

    with pytest.raises(ValueError, match="scale_min must be less than scale_max"):
        step.compute_context_free(likert_dataset())


def test_reverse_recode_rejects_duplicate_columns() -> None:
    step = RecodeReverseStep(
        id="reverse",
        title="Reverse q3",
        params={"columns": ["q3", "q3"], "scale_min": 1, "scale_max": 5},
    )

    with pytest.raises(ValueError, match="RecodeReverseStep columns must be unique"):
        step.compute_context_free(likert_dataset())


def test_compose_scale_survey_policy_uses_available_items_at_minimum_valid_ratio() -> None:
    step = ComposeScaleStep(
        id="compose",
        title="Compose satisfaction",
        params={
            "items": ["q1", "q2", "q3", "q4", "q5"],
            "method": "mean",
            "name": "job_sat",
            "missing_policy": {"preset": "survey", "min_valid": 0.8},
        },
    )

    result = step.compute_context_free(likert_dataset())

    assert result.new_columns["job_sat"].tolist() == [3.8, 3.5, 4.0]
    assert result.new_variables["job_sat"].measure is Measure.SCALE
    assert result.notes == [
        "Applied survey missing policy with min_valid=0.8.",
        "Composed 5 items into job_sat using mean.",
        "Dropped 0 cases for missingness.",
    ]


def test_compose_scale_conservative_policy_drops_any_case_with_missing_item() -> None:
    step = ComposeScaleStep(
        id="compose",
        title="Compose satisfaction",
        params={
            "items": ["q1", "q2", "q3", "q4", "q5"],
            "method": "mean",
            "name": "job_sat",
            "missing_policy": {"preset": "conservative"},
        },
    )

    result = step.compute_context_free(likert_dataset())

    assert pd.isna(result.new_columns["job_sat"].iloc[1])
    assert pd.isna(result.new_columns["job_sat"].iloc[2])
    assert result.new_columns["job_sat"].iloc[0] == 3.8
    assert result.notes[-1] == "Dropped 2 cases for missingness."


def test_import_change_recomputes_reverse_and_compose_steps(tmp_path) -> None:
    path = tmp_path / "survey.csv"
    path.write_text("q1,q2,q3,q4,q5\n5,4,1,5,4\n", encoding="utf-8")
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(path), "file_type": "csv"},
        )
    )
    pipeline.add(
        RecodeReverseStep(
            id="reverse",
            title="Reverse q3",
            params={"columns": ["q3"], "scale_min": 1, "scale_max": 5},
        )
    )
    pipeline.add(
        ComposeScaleStep(
            id="compose",
            title="Compose satisfaction",
            params={
                "items": ["q1", "q2", "q3_R", "q4", "q5"],
                "method": "mean",
                "name": "job_sat",
                "missing_policy": {"preset": "survey", "min_valid": 0.8},
            },
        )
    )
    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df["job_sat"].tolist() == [4.6]

    path.write_text("q1,q2,q3,q4,q5\n1,1,5,1,1\n", encoding="utf-8")
    pipeline.recompute(dirty_from="import")

    assert pipeline.current_dataset.df["q3_R"].tolist() == [1]
    assert pipeline.current_dataset.df["job_sat"].tolist() == [1.0]


def test_import_schema_contraction_does_not_reuse_stale_downstream_results(tmp_path) -> None:
    path = tmp_path / "survey.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(path), "file_type": "csv"},
        )
    )
    pipeline.add(
        ComposeScaleStep(
            id="compose",
            title="Compose score",
            params={
                "items": ["b"],
                "method": "mean",
                "name": "score",
                "missing_policy": {"preset": "survey", "min_valid": 1.0},
            },
        )
    )
    pipeline.recompute(dirty_from=None)
    assert pipeline.current_dataset.df["score"].tolist() == [2.0]

    path.write_text("a\n3\n", encoding="utf-8")

    with pytest.raises(KeyError, match="b"):
        pipeline.recompute(dirty_from="import")

    assert pipeline.current_dataset.df.to_dict(orient="list") == {
        "a": [1],
        "b": [2],
        "score": [2.0],
    }


def test_import_recompute_failure_preserves_previous_successful_dataset(tmp_path) -> None:
    path = tmp_path / "survey.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(path), "file_type": "csv"},
        )
    )
    pipeline.recompute(dirty_from=None)
    path.unlink()

    with pytest.raises(FileNotFoundError):
        pipeline.recompute(dirty_from="import")

    assert pipeline.current_dataset.df.to_dict(orient="list") == {"a": [1], "b": [2]}


def test_compose_scale_rejects_custom_missing_policy_without_min_valid() -> None:
    step = ComposeScaleStep(
        id="compose",
        title="Compose satisfaction",
        params={
            "items": ["q1", "q2"],
            "method": "mean",
            "name": "job_sat",
            "missing_policy": {"preset": "custom"},
        },
    )

    with pytest.raises(ValueError, match="custom missing_policy requires min_valid"):
        step.compute_context_free(likert_dataset())


def test_compose_scale_rejects_empty_item_list() -> None:
    step = ComposeScaleStep(
        id="compose",
        title="Compose satisfaction",
        params={
            "items": [],
            "method": "mean",
            "name": "job_sat",
            "missing_policy": {"preset": "survey", "min_valid": 0.8},
        },
    )

    with pytest.raises(ValueError, match="ComposeScaleStep requires at least one item"):
        step.compute_context_free(likert_dataset())


def test_compose_scale_rejects_duplicate_items() -> None:
    step = ComposeScaleStep(
        id="compose",
        title="Compose satisfaction",
        params={
            "items": ["q1", "q1", "q2"],
            "method": "mean",
            "name": "job_sat",
            "missing_policy": {"preset": "survey", "min_valid": 0.8},
        },
    )

    with pytest.raises(ValueError, match="ComposeScaleStep items must be unique"):
        step.compute_context_free(likert_dataset())


@pytest.mark.parametrize(
    "missing_policy",
    [
        {"preset": "custom", "min_valid": 0},
        {"preset": "custom", "min_valid": 1.01},
        {"preset": "survey", "min_valid": -0.1},
    ],
)
def test_compose_scale_rejects_min_valid_outside_valid_ratio_range(
    missing_policy,
) -> None:
    step = ComposeScaleStep(
        id="compose",
        title="Compose satisfaction",
        params={
            "items": ["q1", "q2"],
            "method": "mean",
            "name": "job_sat",
            "missing_policy": missing_policy,
        },
    )

    with pytest.raises(ValueError, match="min_valid must be greater than 0 and at most 1"):
        step.compute_context_free(likert_dataset())


def test_import_step_drops_duplicate_rows_on_param(tmp_path) -> None:
    path = tmp_path / "dupes.csv"
    path.write_text("지역,인구\n종로구,100\n종로구,100\n중구,200\n", encoding="utf-8")
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={
                "path": str(path),
                "file_type": "csv",
                "drop_duplicate_rows": True,
            },
        )
    )

    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df.to_dict(orient="records") == [
        {"지역": "종로구", "인구": 100},
        {"지역": "중구", "인구": 200},
    ]
    assert "중복 행 1개를 제외했습니다." in pipeline.step_results["import"].notes


def test_unify_values_step_writes_suffixed_column_without_touching_source(tmp_path) -> None:
    from modori.steps import UnifyValuesStep

    path = tmp_path / "regions.csv"
    path.write_text(
        "지역,인구\n서울특별시,100\n서울 특별시,200\n부산광역시,300\n",
        encoding="utf-8",
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(path), "file_type": "csv"},
        )
    )
    pipeline.add(
        UnifyValuesStep(
            id="transform:unify:지역",
            title="Unify region labels",
            params={
                "column": "지역",
                "mapping": {"서울 특별시": "서울특별시"},
            },
        )
    )

    pipeline.recompute(dirty_from=None)

    frame = pipeline.current_dataset.df
    assert list(frame["지역"]) == ["서울특별시", "서울 특별시", "부산광역시"]
    assert list(frame["지역_정리"]) == ["서울특별시", "서울특별시", "부산광역시"]
    notes = pipeline.step_results["transform:unify:지역"].notes
    assert any("1" in note for note in notes)


def test_unify_values_step_is_replay_deterministic(tmp_path) -> None:
    from modori.steps import UnifyValuesStep

    path = tmp_path / "regions.csv"
    path.write_text("지역,인구\n중구 ,100\n중구,200\n", encoding="utf-8")

    def build() -> Pipeline:
        pipeline = Pipeline(Dataset.empty())
        pipeline.add(
            ImportStep(
                id="import",
                title="Import CSV",
                params={"path": str(path), "file_type": "csv"},
            )
        )
        pipeline.add(
            UnifyValuesStep(
                id="transform:unify:지역",
                title="Unify region labels",
                params={"column": "지역", "mapping": {"중구 ": "중구"}},
            )
        )
        pipeline.recompute(dirty_from=None)
        return pipeline

    first = build().current_dataset.df["지역_정리"]
    second = build().current_dataset.df["지역_정리"]

    assert list(first) == list(second) == ["중구", "중구"]
