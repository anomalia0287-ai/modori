import pytest

from modori.analysis_catalog import (
    AnalysisStatus,
    get_capability,
    require_executable,
    survey_v1_executable_keys,
)


def test_survey_v1_exposes_only_supported_executable_comparisons() -> None:
    keys = survey_v1_executable_keys()

    assert "independent_groups" in keys
    assert "paired_two_time" in keys
    assert "mediation" not in keys
    assert "moderated_mediation" not in keys
    assert "repeated_measures_anova" not in keys
    assert "friedman" not in keys


def test_deferred_advanced_analyses_fail_closed() -> None:
    capability = get_capability("repeated_measures_anova")

    assert capability.status is AnalysisStatus.DEFERRED
    assert "sphericity" in capability.reason
    assert "Greenhouse-Geisser" in capability.reason
    assert "Friedman" in capability.reason
    with pytest.raises(ValueError, match="not executable in Survey Pipeline V1"):
        require_executable("repeated_measures_anova")


def test_mediation_is_deferred_with_external_verification_paths() -> None:
    capability = get_capability("mediation")

    assert capability.status is AnalysisStatus.DEFERRED
    assert "Bootstrap CI" in capability.reason
    assert "PROCESS" in capability.external_paths
    assert "R/lavaan" in capability.external_paths
    assert "jamovi/jAMM" in capability.external_paths


def test_unknown_capability_key_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown analysis capability"):
        get_capability("unknown")
