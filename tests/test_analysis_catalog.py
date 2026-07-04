import pytest

from modori.analysis_catalog import (
    AnalysisStatus,
    get_capability,
    require_executable,
    survey_v1_executable_keys,
)


DEFERRED_KEYS = (
    "repeated_measures_anova",
    "friedman",
    "mediation",
    "moderated_mediation",
)


def test_survey_v1_exposes_only_supported_executable_comparisons() -> None:
    keys = survey_v1_executable_keys()

    assert "independent_groups" in keys
    assert "paired_two_time" in keys
    assert "mediation" not in keys
    assert "moderated_mediation" not in keys
    assert "repeated_measures_anova" not in keys
    assert "friedman" not in keys


@pytest.mark.parametrize("key", DEFERRED_KEYS)
def test_deferred_advanced_analyses_are_registered(key: str) -> None:
    capability = get_capability(key)

    assert capability.status is AnalysisStatus.DEFERRED


def test_repeated_measures_anova_explains_v1_deferment() -> None:
    capability = get_capability("repeated_measures_anova")

    assert "sphericity" in capability.reason
    assert "Greenhouse-Geisser" in capability.reason
    assert "Friedman" in capability.reason


@pytest.mark.parametrize("key", DEFERRED_KEYS)
def test_deferred_advanced_analyses_fail_closed(key: str) -> None:
    with pytest.raises(ValueError, match="not executable in Survey Pipeline V1"):
        require_executable(key)


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
