from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json

import pytest

from modori.core import Pipeline
from modori.research_flow import (
    PassportBoundPreparation,
    PreflightDisposition,
    preflight_mapped_step,
)
from modori.research_os import P1TaskProfile
from modori.research_memory import canonical_bytes
from modori.ui.pipeline_ops import PipelineOperations
from modori.ui.research_preparation_editor import (
    ResearchPreparationEditor,
)
from tests.test_research_flow_handoff import EXPECTED_HANDOFFS
from tests.test_research_flow_preflight import _mapping, _valid_dataset


class NoRunPipeline(Pipeline):
    def recompute(self, dirty_from: str | None) -> None:
        raise AssertionError(
            f"Prepare and Confirm must not execute the pipeline: {dirty_from}"
        )


def _ready(profile: P1TaskProfile, *, version: int = 7):
    dataset = _valid_dataset(profile)
    result = preflight_mapped_step(
        _mapping(profile),
        dataset,
        captured_pipeline_version=version,
        current_pipeline_version=lambda: version,
    )
    assert result.disposition is PreflightDisposition.PREPARE_READY
    assert result.preparation is not None
    return dataset, result.preparation


def _editor(
    pipeline: Pipeline,
    preparation: PassportBoundPreparation,
    *,
    version: list[int] | None = None,
    fingerprint: list[str] | None = None,
    commits: list[PassportBoundPreparation] | None = None,
) -> ResearchPreparationEditor:
    version = version if version is not None else [7]
    fingerprint = (
        fingerprint if fingerprint is not None else [preparation.dataset_fingerprint]
    )
    commits = commits if commits is not None else []

    def commit_pipeline_change(value: PassportBoundPreparation) -> int:
        commits.append(value)
        version[0] += 1
        return version[0]

    return ResearchPreparationEditor(
        PipelineOperations(pipeline),
        version_provider=lambda: version[0],
        current_dataset_fingerprint=lambda: fingerprint[0],
        commit_pipeline_change=commit_pipeline_change,
    )


def _reseal(
    preparation: PassportBoundPreparation,
    params: dict[str, object],
) -> PassportBoundPreparation:
    param_bytes = canonical_bytes(params)
    digest = PassportBoundPreparation.compute_digest(
        passport_artifact_id=preparation.passport_artifact_id,
        passport_digest=preparation.passport_digest,
        capability_key=preparation.capability_key,
        dataset_fingerprint=preparation.dataset_fingerprint,
        step_type=preparation.step_type,
        canonical_step_params=param_bytes,
        mapping_digest=preparation.mapping_digest,
        preflight_disposition=preparation.preflight_disposition,
        experimental=True,
        requires_explicit_configure_confirm_run=True,
    )
    return replace(
        preparation,
        canonical_step_params=param_bytes,
        preparation_digest=digest,
    )


def test_prepare_review_is_immutable_exact_and_does_not_mutate_pipeline() -> None:
    dataset, preparation = _ready(P1TaskProfile.LINEAR_CO_MOVEMENT)
    pipeline = NoRunPipeline(dataset)
    before_json = pipeline.to_json()
    before_dataset = pipeline.current_dataset
    editor = _editor(pipeline, preparation)

    review = editor.review(preparation, pipeline_version=7)

    assert tuple(review.__dataclass_fields__) == (
        "preparation",
        "captured_pipeline_version",
        "settings_rows",
    )
    assert review.preparation is preparation
    assert review.captured_pipeline_version == 7
    assert dict(review.settings_rows) == {
        "step_type": "stats.correlation",
        "outcome": "y",
        "focal_predictor": "x",
        "method": "pearson",
        "missing_policy": "pairwise",
        "p_adjust": "none",
        "experimental": "true",
        "automatic_run": "false",
    }
    assert preparation.preparation_digest
    assert pipeline.to_json() == before_json
    assert pipeline.current_dataset is before_dataset
    assert pipeline.steps == []
    assert pipeline.analysis_objects == {}
    with pytest.raises(FrozenInstanceError):
        review.captured_pipeline_version = 8  # type: ignore[misc]
    with pytest.raises(ValueError, match="settings rows"):
        replace(review, settings_rows=(("method", "auto"),))


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
def test_confirm_adds_one_exact_step_once_without_running(
    profile: P1TaskProfile,
) -> None:
    dataset, preparation = _ready(profile)
    pipeline = NoRunPipeline(dataset)
    version = [7]
    commits: list[PassportBoundPreparation] = []
    editor = _editor(
        pipeline,
        preparation,
        version=version,
        commits=commits,
    )
    review = editor.review(preparation, pipeline_version=7)
    expected_params = json.loads(preparation.canonical_step_params.decode("utf-8"))
    expected_class = EXPECTED_HANDOFFS[profile][3]

    result = editor.confirm(review, pipeline_version=7)

    assert result.ok is True
    assert result.pipeline_version == 8
    assert len(result.changed_step_ids) == 1
    assert len(pipeline.steps) == 1
    assert isinstance(pipeline.steps[0], expected_class)
    assert pipeline.steps[0].params == expected_params
    assert pipeline.analysis_objects == {}
    assert commits == [preparation]
    assert version == [8]

    repeated = editor.confirm(review, pipeline_version=8)
    assert repeated.ok is False
    assert repeated.error_code == "research_preparation_stale"
    assert len(pipeline.steps) == 1
    assert commits == [preparation]


def test_confirm_rejects_version_or_fingerprint_drift_without_mutation() -> None:
    dataset, preparation = _ready(P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN)
    pipeline = NoRunPipeline(dataset)
    version = [7]
    fingerprint = [preparation.dataset_fingerprint]
    commits: list[PassportBoundPreparation] = []
    editor = _editor(
        pipeline,
        preparation,
        version=version,
        fingerprint=fingerprint,
        commits=commits,
    )
    review = editor.review(preparation, pipeline_version=7)

    version[0] = 8
    stale_version = editor.confirm(review, pipeline_version=8)
    assert stale_version.ok is False
    assert stale_version.error_code == "research_preparation_stale"

    version[0] = 7
    fingerprint[0] = "0" * 64
    stale_fingerprint = editor.confirm(review, pipeline_version=7)
    assert stale_fingerprint.ok is False
    assert stale_fingerprint.error_code == "research_preparation_stale"
    assert pipeline.steps == []
    assert commits == []


def test_confirm_rechecks_preflight_and_rejects_new_structural_block() -> None:
    dataset, preparation = _ready(P1TaskProfile.LINEAR_CO_MOVEMENT)
    pipeline = NoRunPipeline(dataset)
    editor = _editor(pipeline, preparation)
    review = editor.review(preparation, pipeline_version=7)
    pipeline.current_dataset = type(dataset)(
        df=dataset.df.iloc[:2].copy(),
        variables=dict(dataset.variables),
    )

    result = editor.confirm(review, pipeline_version=7)

    assert result.ok is False
    assert result.error_code == "research_preparation_blocked"
    assert pipeline.steps == []


def test_review_rejects_blocked_preparation() -> None:
    _, ready = _ready(P1TaskProfile.NUMERIC_DISTRIBUTION)
    blocked = replace(
        ready,
        preflight_disposition=PreflightDisposition.PREPARE_BLOCKED,
        preparation_digest=PassportBoundPreparation.compute_digest(
            passport_artifact_id=ready.passport_artifact_id,
            passport_digest=ready.passport_digest,
            capability_key=ready.capability_key,
            dataset_fingerprint=ready.dataset_fingerprint,
            step_type=ready.step_type,
            canonical_step_params=ready.canonical_step_params,
            mapping_digest=ready.mapping_digest,
            preflight_disposition=PreflightDisposition.PREPARE_BLOCKED,
            experimental=True,
            requires_explicit_configure_confirm_run=True,
        ),
    )
    editor = _editor(
        NoRunPipeline(_valid_dataset(P1TaskProfile.NUMERIC_DISTRIBUTION)), blocked
    )

    with pytest.raises(ValueError, match="ready preparation"):
        editor.review(blocked, pipeline_version=7)


@pytest.mark.parametrize(
    ("profile", "mutate"),
    (
        (
            P1TaskProfile.LINEAR_CO_MOVEMENT,
            lambda params: {**params, "method": "auto"},
        ),
        (
            P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
            lambda params: {
                **params,
                "routing_policy": {"preset": "modern"},
            },
        ),
        (
            P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE,
            lambda params: {
                **params,
                "routing_policy": {"preset": "modern"},
            },
        ),
        (
            P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE,
            lambda params: {
                **params,
                "before": params["after"],
                "after": params["before"],
            },
        ),
    ),
)
def test_review_rejects_self_resealed_handoff_mutants(
    profile: P1TaskProfile,
    mutate,
) -> None:
    dataset, preparation = _ready(profile)
    params = json.loads(preparation.canonical_step_params.decode("utf-8"))
    forged = _reseal(preparation, mutate(params))
    editor = _editor(NoRunPipeline(dataset), forged)

    with pytest.raises(ValueError, match="handoff oracle"):
        editor.review(forged, pipeline_version=7)


def test_paired_confirmation_binds_result_as_comparison_only_after_explicit_run() -> (
    None
):
    dataset, preparation = _ready(P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE)
    pipeline = Pipeline(dataset)
    editor = _editor(pipeline, preparation)
    review = editor.review(preparation, pipeline_version=7)

    confirmed = editor.confirm(review, pipeline_version=7)

    assert confirmed.ok is True
    assert pipeline.analysis_objects == {}
    pipeline.recompute(dirty_from=None)
    assert "comparison:before:after:paired" in pipeline.analysis_objects
    assert (
        PipelineOperations._kind_for_result("comparison:before:after:paired")
        == "comparison"
    )


def test_confirmation_callback_failure_rolls_back_the_pipeline() -> None:
    dataset, preparation = _ready(P1TaskProfile.RANK_CO_MOVEMENT)
    pipeline = NoRunPipeline(dataset)
    before_json = pipeline.to_json()

    def fail_commit(_preparation: PassportBoundPreparation) -> int:
        raise RuntimeError("host commit failed")

    editor = ResearchPreparationEditor(
        PipelineOperations(pipeline),
        version_provider=lambda: 7,
        current_dataset_fingerprint=lambda: preparation.dataset_fingerprint,
        commit_pipeline_change=fail_commit,
    )
    review = editor.review(preparation, pipeline_version=7)

    result = editor.confirm(review, pipeline_version=7)

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert pipeline.to_json() == before_json
    assert pipeline.steps == []
