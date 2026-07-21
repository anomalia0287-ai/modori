from __future__ import annotations

import importlib
from collections.abc import Mapping

import pandas as pd
import pytest
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Variable


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.friedman")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.friedman":
            pytest.fail("modori.steps.friedman is not implemented")
        raise
    return module.FriedmanStep


def _params(measures: list[str] | None = None) -> dict[str, object]:
    return {
        "schema_version": 1,
        "measures": ["pre", "mid", "post"] if measures is None else measures,
        "within_factor": "time",
        "level_labels": ["사전", "중간", "사후"],
        "posthoc_method": "none",
        "p_adjust": "none",
        "language": "ko",
    }


def dataset_factory(
    frame: pd.DataFrame,
    *,
    measures: Mapping[str, Measure] | None = None,
) -> Dataset:
    measures = measures or {}
    variables = {
        column: Variable(
            name=column,
            label=column,
            measure=measures.get(column, Measure.ORDINAL),
            value_labels={},
            missing_values=[],
            dtype=str(frame[column].dtype),
            origin_step_id="import",
        )
        for column in frame.columns
    }
    return Dataset(df=frame, variables=variables)


def run_step(dataset: Dataset, params: dict[str, object]):
    step = _step_cls()(id="friedman-main", title="Friedman", params=dict(params))
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def _wide_dataset() -> Dataset:
    return dataset_factory(
        pd.DataFrame(
            {
                "pre": [1, 2, 2, 3, 4, 3, 5, 4],
                "mid": [2, 2, 3, 4, 4, 5, 5, 6],
                "post": [3, 4, 4, 5, 6, 6, 7, 7],
            }
        )
    )


def test_current_schema_rejects_missing_unknown_and_newer_params() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"measures": ["pre", "mid", "post"]})

    with pytest.raises(ValueError, match="unknown friedman params"):
        _step_cls().validate_params({**_params(), "extra": "bad"})

    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params({"schema_version": 999, "measures": ["a", "b", "c"]})


def test_friedman_matches_scipy_and_pingouin_reference_with_kendalls_w() -> None:
    pg = pytest.importorskip("pingouin")
    dataset = _wide_dataset()
    complete = dataset.df.loc[:, ["pre", "mid", "post"]]

    result = run_step(dataset, _params())

    scipy_reference = stats.friedmanchisquare(
        complete["pre"],
        complete["mid"],
        complete["post"],
    )
    pingouin_reference = pg.friedman(data=complete)
    expected_w = float(scipy_reference.statistic) / (8 * (3 - 1))

    assert result.analysis_key == "friedman"
    assert result.measures == ("pre", "mid", "post")
    assert result.n_total == 8
    assert result.n_used == 8
    assert result.n_excluded == 0
    assert [level.level_label for level in result.levels] == ["사전", "중간", "사후"]
    assert result.statistic_label == "Q"
    assert result.statistic == pytest.approx(scipy_reference.statistic, abs=1e-12)
    assert result.degrees_of_freedom == 2
    assert result.p_value == pytest.approx(scipy_reference.pvalue, abs=1e-12)
    assert result.kendalls_w == pytest.approx(expected_w, abs=1e-12)
    assert result.kendalls_w == pytest.approx(
        float(pingouin_reference.loc["Friedman", "W"]),
        abs=1e-12,
    )
    assert result.posthoc is None
    assert result.chart_spec is None
    assert result.no_canonical_chart_reason_ko


def test_friedman_records_tied_rank_and_chi_square_approximation_policy() -> None:
    frame = pd.DataFrame(
        {
            "pre": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 5],
            "mid": [1, 2, 2, 3, 3, 4, 4, 5, 5, 5, 5],
            "post": [2, 2, 3, 3, 4, 4, 5, 5, 5, 5, 5],
        }
    )
    dataset = dataset_factory(frame)

    result = run_step(dataset, _params())
    reference = stats.friedmanchisquare(frame["pre"], frame["mid"], frame["post"])

    assert result.statistic == pytest.approx(reference.statistic, abs=1e-12)
    assert result.p_value == pytest.approx(reference.pvalue, abs=1e-12)
    assert result.method_details == {
        "method": "chi_square_approximation",
        "ties_present": True,
        "tie_correction": "scipy_friedmanchisquare",
        "subjects": 11,
        "conditions": 3,
    }
    assert any("근사" in warning for warning in result.warnings_ko)


def test_friedman_does_not_emit_small_sample_warning_for_large_subject_count() -> None:
    frame = pd.DataFrame(
        {
            "pre": list(range(1, 21)),
            "mid": list(range(2, 22)),
            "post": list(range(3, 23)),
        }
    )
    dataset = dataset_factory(frame)

    result = run_step(dataset, _params())

    assert result.n_used == 20
    assert not any("카이제곱 근사" in warning for warning in result.warnings_ko)


def test_listwise_missing_subjects_match_complete_case_scipy_reference() -> None:
    frame = pd.DataFrame(
        {
            "pre": [1, 2, 2, 3, 4, 5],
            "mid": [2, 3, None, 4, 5, 6],
            "post": [3, 4, 4, None, 6, 7],
        }
    )
    dataset = dataset_factory(frame)
    complete = frame.loc[:, ["pre", "mid", "post"]].dropna(axis=0, how="any")
    scipy_reference = stats.friedmanchisquare(
        complete["pre"],
        complete["mid"],
        complete["post"],
    )
    expected_w = float(scipy_reference.statistic) / (4 * (3 - 1))

    result = run_step(dataset, _params())

    assert result.n_total == 6
    assert result.n_used == 4
    assert result.n_excluded == 2
    assert result.statistic == pytest.approx(scipy_reference.statistic, abs=1e-12)
    assert result.p_value == pytest.approx(scipy_reference.pvalue, abs=1e-12)
    assert result.kendalls_w == pytest.approx(expected_w, abs=1e-12)


def test_validation_rejects_unsupported_posthoc_shapes_and_bad_inputs() -> None:
    dataset = _wide_dataset()

    with pytest.raises(ValueError, match="three or more"):
        run_step(dataset, _params(measures=["pre", "post"]))

    with pytest.raises(ValueError, match="duplicate"):
        run_step(dataset, _params(measures=["pre", "mid", "pre"]))

    with pytest.raises(ValueError, match="posthoc"):
        run_step(dataset, {**_params(), "posthoc_method": "nemenyi"})

    nominal_dataset = dataset_factory(
        dataset.df,
        measures={"pre": Measure.NOMINAL, "mid": Measure.ORDINAL, "post": Measure.ORDINAL},
    )
    with pytest.raises(ValueError, match="scale or ordinal"):
        run_step(nominal_dataset, _params())

    non_numeric = dataset_factory(
        pd.DataFrame(
            {
                "pre": [1.0, 2.0, 3.0],
                "mid": [2.0, 3.0, 4.0],
                "post": ["high", "low", "mid"],
            }
        )
    )
    with pytest.raises(ValueError, match="numeric"):
        run_step(non_numeric, _params())
