from __future__ import annotations

from pathlib import Path

import pandas as pd

from modori.ui.contracts import ImportOptions
from modori.ui.controller import UiController


def _write_csv(path: Path) -> None:
    pd.DataFrame({"q1": [1, 2], "q2": [2, 3], "q3": [5, 4], "group": [1, 2]}).to_csv(
        path,
        index=False,
    )


def test_controller_applies_reverse_code_transform_and_marks_results_stale(
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    controller = UiController()
    assert controller.openDataFile(data_path, ImportOptions(confirm_new_session=True)).ok is True
    before_version = controller.pipeline_version

    result = controller.applyReverseCodeTransform(
        {"columns": ["q3"], "scale_min": 1, "scale_max": 5, "suffix": "_R"}
    )

    assert result.ok is True
    assert result.changed_step_ids == ["transform:reverse"]
    assert controller.pipeline_version == before_version + 1
    assert controller.stale is True
    assert "Reverse-code items" in controller.stepChainText
    assert "q3_R" in controller.pipeline.current_dataset.df.columns


def test_controller_applies_scale_score_transform(tmp_path: Path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    controller = UiController()
    controller.openDataFile(data_path, ImportOptions(confirm_new_session=True))

    result = controller.applyScaleScoreTransform(
        {
            "items": ["q1", "q2", "q3"],
            "name": "score",
            "method": "mean",
            "missing_policy": {"preset": "survey", "min_valid": 0.8},
        }
    )

    assert result.ok is True
    assert "Compose scale score" in controller.stepChainText
    assert "score" in controller.pipeline.current_dataset.df.columns


def test_controller_rejects_invalid_transform_without_version_bump(
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    controller = UiController()
    controller.openDataFile(data_path, ImportOptions(confirm_new_session=True))
    before_version = controller.pipeline_version

    result = controller.applyScaleScoreTransform(
        {
            "items": ["q1"],
            "name": "",
            "method": "mean",
            "missing_policy": {"preset": "survey"},
        }
    )

    assert result.ok is False
    assert result.error_code == "invalid_transform"
    assert controller.pipeline_version == before_version
    assert "score" not in controller.pipeline.current_dataset.df.columns


def test_value_unification_suggestion_flow(tmp_path) -> None:
    from modori.ui.controller import UiController

    data_path = tmp_path / "regions.csv"
    data_path.write_text(
        "지역,인구\n서울특별시,100\n서울 특별시,200\n부산광역시,300\n",
        encoding="utf-8",
    )
    controller = UiController()
    assert controller.openDataFilePath(str(data_path)) is True

    suggestions = controller.valueUnificationSuggestions
    assert len(suggestions) == 1
    assert suggestions[0]["column"] == "지역"
    assert suggestions[0]["mapping"] == {"서울 특별시": "서울특별시"}

    assert controller.applyValueUnification("지역") is True

    frame = controller.pipeline.current_dataset.df
    assert frame["지역_정리"].tolist() == ["서울특별시", "서울특별시", "부산광역시"]
    assert controller.valueUnificationSuggestions == []


def test_apply_value_unification_without_suggestion_sets_error() -> None:
    from modori.ui.controller import UiController

    controller = UiController()

    assert controller.applyValueUnification("지역") is False
    assert controller.lastError != ""


def test_controller_exposes_value_recode_inventory_and_applies_text_rules(tmp_path) -> None:
    from modori.ui.controller import UiController

    data_path = tmp_path / "regions.csv"
    data_path.write_text(
        "지역,인구\n서울특별시,100\n서울 특별시,200\n부산광역시,300\n",
        encoding="utf-8",
    )
    controller = UiController()
    assert controller.openDataFilePath(str(data_path)) is True

    inventory = {entry["column"]: entry for entry in controller.valueRecodeInventory}
    assert inventory["지역"]["eligible"] is True
    assert inventory["지역"]["values"][0] == {"value": "서울특별시", "count": 1}
    assert inventory["인구"]["eligible"] is False

    assert controller.mapValuesFromText(
        "지역",
        "서울 특별시=서울특별시",
        "부산광역시",
        "_수정",
    ) is True

    frame = controller.pipeline.current_dataset.df
    values = frame["지역_수정"].tolist()
    assert values[:2] == ["서울특별시", "서울특별시"]
    assert pd.isna(values[2])
    assert controller.stale is True


def test_controller_rejects_malformed_value_recode_text(tmp_path) -> None:
    from modori.ui.controller import UiController

    data_path = tmp_path / "regions.csv"
    data_path.write_text("지역\n서울특별시\n서울 특별시\n", encoding="utf-8")
    controller = UiController()
    assert controller.openDataFilePath(str(data_path)) is True

    assert controller.mapValuesFromText("지역", "서울 특별시", "", "_수정") is False
    assert controller.lastError == "값 수정 규칙은 기존값=새값 형식이어야 합니다."
