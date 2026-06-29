import pytest


def test_reliability_patch_rejects_unknown_fields() -> None:
    from modori.ui.patches import PatchValidationError, parse_step_patch

    with pytest.raises(PatchValidationError) as error:
        parse_step_patch(
            "reliability",
            {"item_keys": ["q1", "q2"], "language": "ko", "extra": True},
            variable_keys={"q1", "q2"},
        )

    assert error.value.error_code == "invalid_step_patch"
    assert "extra" in error.value.message_ko


def test_regression_patch_requires_existing_variables() -> None:
    from modori.ui.patches import PatchValidationError, parse_step_patch

    with pytest.raises(PatchValidationError) as error:
        parse_step_patch(
            "regression",
            {
                "outcome_key": "y",
                "predictor_keys": ["x1", "missing"],
                "include_intercept": True,
                "language": "ko",
            },
            variable_keys={"y", "x1"},
        )

    assert error.value.error_code == "invalid_step_patch"
    assert "missing" in error.value.message_ko


def test_comparison_patch_requires_two_distinct_groups() -> None:
    from modori.ui.patches import PatchValidationError, parse_step_patch

    with pytest.raises(PatchValidationError):
        parse_step_patch(
            "comparison",
            {
                "outcome_key": "score",
                "group_key": "group",
                "group_a": "A",
                "group_b": "A",
                "language": "ko",
            },
            variable_keys={"score", "group"},
        )


def test_valid_report_patch_parses_to_typed_object() -> None:
    from modori.ui.patches import ReportPatch, parse_step_patch

    patch = parse_step_patch(
        "report",
        {
            "language": "en",
            "include_reliability": True,
            "include_comparison": False,
            "include_regression": True,
            "include_figures": True,
        },
    )

    assert isinstance(patch, ReportPatch)
    assert patch.language == "en"
    assert patch.include_regression is True


def test_variable_metadata_patch_rejects_unsupported_display_type() -> None:
    from modori.ui.patches import PatchValidationError, parse_step_patch

    with pytest.raises(PatchValidationError) as error:
        parse_step_patch(
            "variable_metadata",
            {
                "variable_key": "group",
                "display_type": "numeric",
            },
            variable_keys={"group"},
        )

    assert error.value.error_code == "unsupported_metadata_patch"
    assert "display_type" in error.value.message_ko


def test_variable_metadata_patch_rejects_ambiguous_missing_aliases() -> None:
    from modori.ui.patches import PatchValidationError, parse_step_patch

    with pytest.raises(PatchValidationError) as error:
        parse_step_patch(
            "variable_metadata",
            {
                "variable_key": "group",
                "missing_codes": [1],
                "missing_values": [2],
            },
            variable_keys={"group"},
        )

    assert error.value.error_code == "invalid_metadata_patch"
    assert "missing_codes" in error.value.message_ko
    assert "missing_values" in error.value.message_ko
