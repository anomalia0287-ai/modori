from __future__ import annotations

import importlib

import pandas as pd
import pytest


def _design_module():
    return importlib.import_module("modori.regression_design")


def test_shared_design_builder_preserves_declared_dummy_order_and_metadata() -> None:
    module = _design_module()
    frame = pd.DataFrame(
        {
            "x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "group": ["treat", "control", "placebo"] * 2,
        }
    )
    encodings = {
        "group": module.CategoricalEncoding(
            variable="group",
            reference="control",
            levels=("control", "treat", "placebo"),
        )
    }

    design = module.build_regression_design_matrix(
        frame=frame,
        predictors=("x", "group"),
        categorical_encodings=encodings,
        interactions=(),
        center_scale_interactions=False,
        error_prefix="Regression",
    )

    assert list(design.x_pred) == [
        "x",
        "group[T.treat]",
        "group[T.placebo]",
    ]
    assert design.x_pred["group[T.treat]"].tolist() == [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    assert design.term_metadata["group[T.placebo]"] == module.TermMetadata(
        name="group[T.placebo]",
        term_type="categorical_level",
        source_variable="group",
        level="placebo",
        reference_level="control",
        components=("group",),
    )
    assert design.transformed_terms == {"x": "x"}
    assert design.centers == {}


def test_shared_design_builder_preserves_centered_interaction_contract() -> None:
    module = _design_module()
    frame = pd.DataFrame(
        {
            "x": [1.0, 2.0, 3.0, 4.0],
            "z": [8.0, 5.0, 4.0, 3.0],
        }
    )

    design = module.build_regression_design_matrix(
        frame=frame,
        predictors=("x", "z"),
        categorical_encodings={},
        interactions=(module.InteractionSpec(first="x", second="z"),),
        center_scale_interactions=True,
        error_prefix="Regression",
    )

    assert list(design.x_pred) == [
        "x_centered",
        "z_centered",
        "x_centered:z_centered",
    ]
    assert design.centers == pytest.approx({"x": 2.5, "z": 5.0})
    assert design.x_pred["x_centered:z_centered"].tolist() == pytest.approx(
        [-4.5, 0.0, -0.5, -3.0]
    )
    assert design.term_metadata["x_centered:z_centered"].components == ("x", "z")
