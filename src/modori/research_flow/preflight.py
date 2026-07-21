"""Deterministic, non-inferential preflight for passport-bound step mappings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json

from modori.core import Dataset, Measure
from modori.research_flow.contracts import (
    PassportBoundPreparation,
    PassportStepMapping,
    PreflightDisposition,
)
from modori.steps.input_validation import StepInputIssue, validate_step_input


_SUPPORTED_STEP_TYPES = frozenset(
    {
        "stats.descriptives_table1",
        "stats.frequency_crosstab",
        "stats.correlation",
        "stats.compare_groups",
        "stats.paired_comparison",
    }
)


@dataclass(frozen=True)
class PreflightResult:
    disposition: PreflightDisposition
    issues: tuple[StepInputIssue, ...]
    preparation: PassportBoundPreparation | None
    captured_pipeline_version: int

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, PreflightDisposition):
            raise ValueError("disposition must be a PreflightDisposition")
        if not isinstance(self.issues, tuple) or any(
            not isinstance(issue, StepInputIssue) for issue in self.issues
        ):
            raise ValueError("issues must be a tuple of StepInputIssue values")
        if (
            type(self.captured_pipeline_version) is not int
            or self.captured_pipeline_version < 0
        ):
            raise ValueError("captured_pipeline_version must be a nonnegative integer")
        if self.disposition is PreflightDisposition.PREPARE_READY:
            if self.issues or self.preparation is None:
                raise ValueError(
                    "ready preflight requires one preparation and no issues"
                )
        elif self.disposition is PreflightDisposition.PREPARE_BLOCKED:
            if not self.issues or self.preparation is None:
                raise ValueError(
                    "blocked preflight requires issues and one preparation"
                )
        elif self.preparation is not None or not self.issues:
            raise ValueError("stale or failed preflight cannot contain a preparation")
        if (
            self.preparation is not None
            and self.preparation.preflight_disposition is not self.disposition
        ):
            raise ValueError("preparation disposition does not match its result")
        if self.disposition is PreflightDisposition.STALE and self.issues != (
            StepInputIssue(code="pipeline_changed"),
        ):
            raise ValueError("stale preflight requires the pipeline_changed issue")
        if self.disposition is PreflightDisposition.FAILURE and self.issues[
            0
        ].code not in {
            "invalid_params",
            "preflight_failure",
            "unsupported_step_type",
        }:
            raise ValueError("failure preflight requires a closed failure issue")


def _read_pipeline_version(current_pipeline_version: Callable[[], int]) -> int:
    value = current_pipeline_version()
    if type(value) is not int or value < 0:
        raise ValueError("current pipeline version must be a nonnegative integer")
    return value


def _terminal_result(
    disposition: PreflightDisposition,
    issue_code: str,
    captured_pipeline_version: int,
) -> PreflightResult:
    return PreflightResult(
        disposition=disposition,
        issues=(StepInputIssue(code=issue_code),),
        preparation=None,
        captured_pipeline_version=captured_pipeline_version,
    )


def _decode_and_validate_params(
    mapping: PassportStepMapping,
) -> dict[str, object] | None:
    try:
        if mapping.step_type == "stats.descriptives_table1":
            from modori.steps.descriptives_table1 import DescriptivesTableStep

            step_class = DescriptivesTableStep
        elif mapping.step_type == "stats.frequency_crosstab":
            from modori.steps.frequency_crosstab import FrequencyCrosstabStep

            step_class = FrequencyCrosstabStep
        elif mapping.step_type == "stats.correlation":
            from modori.steps.correlation import CorrelationStep

            step_class = CorrelationStep
        elif mapping.step_type in {
            "stats.compare_groups",
            "stats.paired_comparison",
        }:
            from modori.steps.statistics import CompareGroupsStep, PairedComparisonStep

            step_class = (
                CompareGroupsStep
                if mapping.step_type == "stats.compare_groups"
                else PairedComparisonStep
            )
        else:
            return None
        raw = json.loads(mapping.canonical_step_params.decode("utf-8"))
        if not isinstance(raw, dict):
            return None
        migrated = step_class.migrate_params(raw)
        return step_class.validate_params(migrated)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _p1_semantic_issues(
    mapping: PassportStepMapping,
    dataset: Dataset,
    params: dict[str, object],
) -> tuple[StepInputIssue, ...]:
    if mapping.step_type == "stats.descriptives_table1":
        variables = [str(item) for item in params["variables"]]
        for key in variables:
            if dataset.variables[key].measure is not Measure.SCALE:
                return (
                    StepInputIssue(
                        code="p1_requires_scale",
                        role="outcome",
                        variable_id=key,
                    ),
                )
        frame = dataset.frame_for_compute(variables)
        for key in variables:
            if frame[key].notna().sum() == 0:
                return (
                    StepInputIssue(
                        code="no_nonmissing_value",
                        role="outcome",
                        variable_id=key,
                    ),
                )
    elif mapping.step_type == "stats.frequency_crosstab":
        variables = [str(item) for item in params["variables"]]
        frame = dataset.frame_for_compute(variables)
        for key in variables:
            if frame[key].notna().sum() == 0:
                return (
                    StepInputIssue(
                        code="no_nonmissing_value",
                        role="outcome",
                        variable_id=key,
                    ),
                )
    elif mapping.step_type == "stats.compare_groups":
        outcome = str(params["dv"])
        group = str(params["group"])
        if dataset.variables[outcome].measure is not Measure.SCALE:
            return (
                StepInputIssue(
                    code="p1_requires_scale",
                    role="outcome",
                    variable_id=outcome,
                ),
            )
        if dataset.variables[group].measure not in {Measure.NOMINAL, Measure.ORDINAL}:
            return (
                StepInputIssue(
                    code="p1_group_requires_categorical",
                    role="group",
                    variable_id=group,
                ),
            )
    return ()


def _seal_preparation(
    mapping: PassportStepMapping,
    disposition: PreflightDisposition,
) -> PassportBoundPreparation:
    digest = PassportBoundPreparation.compute_digest(
        passport_artifact_id=mapping.passport_artifact_id,
        passport_digest=mapping.passport_digest,
        capability_key=mapping.capability_key,
        dataset_fingerprint=mapping.dataset_fingerprint,
        step_type=mapping.step_type,
        canonical_step_params=mapping.canonical_step_params,
        mapping_digest=mapping.mapping_digest,
        preflight_disposition=disposition,
        experimental=True,
        requires_explicit_configure_confirm_run=True,
    )
    return PassportBoundPreparation(
        passport_artifact_id=mapping.passport_artifact_id,
        passport_digest=mapping.passport_digest,
        capability_key=mapping.capability_key,
        dataset_fingerprint=mapping.dataset_fingerprint,
        step_type=mapping.step_type,
        canonical_step_params=mapping.canonical_step_params,
        mapping_digest=mapping.mapping_digest,
        preflight_disposition=disposition,
        experimental=True,
        requires_explicit_configure_confirm_run=True,
        preparation_digest=digest,
    )


def preflight_mapped_step(
    mapping: PassportStepMapping,
    dataset: Dataset,
    *,
    captured_pipeline_version: int,
    current_pipeline_version: Callable[[], int],
) -> PreflightResult:
    """Check execution feasibility without inference or pipeline mutation."""

    if type(captured_pipeline_version) is not int or captured_pipeline_version < 0:
        raise ValueError("captured_pipeline_version must be a nonnegative integer")
    if not callable(current_pipeline_version):
        raise ValueError("current_pipeline_version must be callable")
    try:
        if (
            _read_pipeline_version(current_pipeline_version)
            != captured_pipeline_version
        ):
            return _terminal_result(
                PreflightDisposition.STALE,
                "pipeline_changed",
                captured_pipeline_version,
            )
    except Exception:
        return _terminal_result(
            PreflightDisposition.FAILURE,
            "preflight_failure",
            captured_pipeline_version,
        )
    if not isinstance(mapping, PassportStepMapping) or not isinstance(dataset, Dataset):
        return _terminal_result(
            PreflightDisposition.FAILURE,
            "preflight_failure",
            captured_pipeline_version,
        )
    if mapping.step_type not in _SUPPORTED_STEP_TYPES:
        return _terminal_result(
            PreflightDisposition.FAILURE,
            "unsupported_step_type",
            captured_pipeline_version,
        )
    params = _decode_and_validate_params(mapping)
    if params is None:
        return _terminal_result(
            PreflightDisposition.FAILURE,
            "invalid_params",
            captured_pipeline_version,
        )
    try:
        issues = validate_step_input(dataset, mapping.step_type, params)
        if not issues:
            issues = _p1_semantic_issues(mapping, dataset, params)
    except Exception:
        return _terminal_result(
            PreflightDisposition.FAILURE,
            "preflight_failure",
            captured_pipeline_version,
        )
    try:
        if (
            _read_pipeline_version(current_pipeline_version)
            != captured_pipeline_version
        ):
            return _terminal_result(
                PreflightDisposition.STALE,
                "pipeline_changed",
                captured_pipeline_version,
            )
    except Exception:
        return _terminal_result(
            PreflightDisposition.FAILURE,
            "preflight_failure",
            captured_pipeline_version,
        )
    disposition = (
        PreflightDisposition.PREPARE_BLOCKED
        if issues
        else PreflightDisposition.PREPARE_READY
    )
    try:
        preparation = _seal_preparation(mapping, disposition)
    except (TypeError, ValueError):
        return _terminal_result(
            PreflightDisposition.FAILURE,
            "preflight_failure",
            captured_pipeline_version,
        )
    try:
        if (
            _read_pipeline_version(current_pipeline_version)
            != captured_pipeline_version
        ):
            return _terminal_result(
                PreflightDisposition.STALE,
                "pipeline_changed",
                captured_pipeline_version,
            )
    except Exception:
        return _terminal_result(
            PreflightDisposition.FAILURE,
            "preflight_failure",
            captured_pipeline_version,
        )
    return PreflightResult(
        disposition=disposition,
        issues=issues,
        preparation=preparation,
        captured_pipeline_version=captured_pipeline_version,
    )
