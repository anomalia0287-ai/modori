from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AnalysisStatus(Enum):
    EXECUTABLE = "executable"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class AnalysisCapability:
    key: str
    label: str
    status: AnalysisStatus
    reason: str
    external_paths: tuple[str, ...] = ()


_CAPABILITIES: dict[str, AnalysisCapability] = {
    "independent_groups": AnalysisCapability(
        key="independent_groups",
        label="Independent two-group comparison",
        status=AnalysisStatus.EXECUTABLE,
        reason="Supported by CompareGroupsStep with Welch-first routing and Mann-Whitney fallback.",
    ),
    "paired_two_time": AnalysisCapability(
        key="paired_two_time",
        label="Two-time paired comparison",
        status=AnalysisStatus.EXECUTABLE,
        reason="Supported by PairedComparisonStep for paired t-test and Wilcoxon fallback.",
    ),
    "repeated_measures_anova": AnalysisCapability(
        key="repeated_measures_anova",
        label="Repeated-measures ANOVA",
        status=AnalysisStatus.DEFERRED,
        reason=(
            "Repeated-measures ANOVA is not executable in Survey Pipeline V1 because "
            "it requires sphericity evaluation, Greenhouse-Geisser correction when "
            "sphericity is violated, and Friedman routing for nonparametric cases."
        ),
        external_paths=("SPSS", "R", "jamovi"),
    ),
    "friedman": AnalysisCapability(
        key="friedman",
        label="Friedman test",
        status=AnalysisStatus.DEFERRED,
        reason="Friedman is paired with repeated-measures coverage and is V1.x with RM-ANOVA gates.",
        external_paths=("SPSS", "R", "jamovi"),
    ),
    "mediation": AnalysisCapability(
        key="mediation",
        label="Mediation analysis",
        status=AnalysisStatus.DEFERRED,
        reason=(
            "Mediation is V1.x because publishable output requires Bootstrap CI, "
            "indirect-effect reporting, and cross-checks against PROCESS/R/lavaan."
        ),
        external_paths=("PROCESS", "R/lavaan", "jamovi/jAMM"),
    ),
    "moderated_mediation": AnalysisCapability(
        key="moderated_mediation",
        label="Moderated mediation",
        status=AnalysisStatus.DEFERRED,
        reason="Moderated mediation requires the advanced process module and is not executable in V1.",
        external_paths=("PROCESS", "R/lavaan", "jamovi/jAMM"),
    ),
}


def get_capability(key: str) -> AnalysisCapability:
    try:
        return _CAPABILITIES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown analysis capability: {key}") from exc


def require_executable(key: str) -> AnalysisCapability:
    capability = get_capability(key)
    if capability.status is not AnalysisStatus.EXECUTABLE:
        raise ValueError(
            f"{capability.label} is not executable in Survey Pipeline V1: {capability.reason}"
        )
    return capability


def survey_v1_executable_keys() -> set[str]:
    return {
        key
        for key, capability in _CAPABILITIES.items()
        if capability.status is AnalysisStatus.EXECUTABLE
    }
