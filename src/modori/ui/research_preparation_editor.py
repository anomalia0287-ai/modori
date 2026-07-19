"""Exact, no-run confirmation adapter for passport-bound preparations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json

from modori.research_flow import (
    PassportBoundPreparation,
    PassportStepMapping,
    PreflightDisposition,
    preflight_mapped_step,
    validate_passport_bound_preparation,
)
from modori.ui.contracts import CommandResult


class ResearchPreparationError(ValueError):
    """Raised when a preparation cannot enter the exact review contract."""


def _read_version(provider: Callable[[], int]) -> int:
    value = provider()
    if type(value) is not int or value < 0:
        raise ResearchPreparationError(
            "current pipeline version must be a nonnegative integer"
        )
    return value


def _decode_params(preparation: PassportBoundPreparation) -> dict[str, object]:
    try:
        decoded = json.loads(preparation.canonical_step_params.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchPreparationError(
            "preparation settings are not canonical JSON"
        ) from exc
    if not isinstance(decoded, dict):
        raise ResearchPreparationError("preparation settings must be an object")
    return decoded


def _string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ResearchPreparationError(f"{field_name} must be a non-empty string")
    return value


def _string_list(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ResearchPreparationError(f"{field_name} must be a non-empty list")
    result = tuple(_string(item, field_name) for item in value)
    if len(result) != len(set(result)):
        raise ResearchPreparationError(f"{field_name} must not contain duplicates")
    return result


def _settings_rows(
    preparation: PassportBoundPreparation,
) -> tuple[tuple[str, str], ...]:
    params = _decode_params(preparation)
    step_type = preparation.step_type
    rows: list[tuple[str, str]] = [("step_type", step_type)]
    if step_type == "stats.descriptives_table1":
        rows.extend(
            (
                (
                    "variables",
                    ", ".join(_string_list(params.get("variables"), "variables")),
                ),
                ("group", "none" if params.get("group") is None else "invalid"),
                (
                    "include_missing_counts",
                    "true" if params.get("include_missing_counts") is True else "false",
                ),
                ("language", _string(params.get("language"), "language")),
            )
        )
    elif step_type == "stats.frequency_crosstab":
        rows.extend(
            (
                ("mode", _string(params.get("mode"), "mode")),
                (
                    "variables",
                    ", ".join(_string_list(params.get("variables"), "variables")),
                ),
                ("language", _string(params.get("language"), "language")),
            )
        )
    elif step_type == "stats.correlation":
        pairs = params.get("pairs")
        if (
            not isinstance(pairs, list)
            or len(pairs) != 1
            or not isinstance(pairs[0], list)
            or len(pairs[0]) != 2
        ):
            raise ResearchPreparationError("correlation pairs must contain one pair")
        rows.extend(
            (
                ("outcome", _string(pairs[0][0], "outcome")),
                ("focal_predictor", _string(pairs[0][1], "focal_predictor")),
                ("method", _string(params.get("method"), "method")),
                (
                    "missing_policy",
                    _string(params.get("missing_policy"), "missing_policy"),
                ),
                ("p_adjust", _string(params.get("p_adjust"), "p_adjust")),
            )
        )
    elif step_type == "stats.compare_groups":
        policy = params.get("routing_policy")
        if not isinstance(policy, Mapping):
            raise ResearchPreparationError("routing_policy must be an object")
        rows.extend(
            (
                ("outcome", _string(params.get("dv"), "outcome")),
                ("group", _string(params.get("group"), "group")),
                ("routing_policy", _string(policy.get("preset"), "routing_policy")),
            )
        )
    elif step_type == "stats.paired_comparison":
        policy = params.get("routing_policy")
        if not isinstance(policy, Mapping):
            raise ResearchPreparationError("routing_policy must be an object")
        rows.extend(
            (
                ("before", _string(params.get("before"), "before")),
                ("after", _string(params.get("after"), "after")),
                ("routing_policy", _string(policy.get("preset"), "routing_policy")),
            )
        )
    else:
        raise ResearchPreparationError("preparation step type is outside P1")
    rows.extend((("experimental", "true"), ("automatic_run", "false")))
    return tuple(rows)


@dataclass(frozen=True)
class PreparationReview:
    preparation: PassportBoundPreparation
    captured_pipeline_version: int
    settings_rows: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.preparation, PassportBoundPreparation):
            raise ResearchPreparationError("review preparation must be passport-bound")
        validate_passport_bound_preparation(self.preparation)
        if (
            type(self.captured_pipeline_version) is not int
            or self.captured_pipeline_version < 0
        ):
            raise ResearchPreparationError(
                "captured pipeline version must be nonnegative"
            )
        if self.settings_rows != _settings_rows(self.preparation):
            raise ResearchPreparationError(
                "review settings rows do not match the sealed preparation"
            )


class ResearchPreparationEditor:
    """Review and confirm exactly one sealed P1 step without running it."""

    def __init__(
        self,
        pipeline_ops: object | None = None,
        *,
        pipeline_ops_provider: Callable[[], object] | None = None,
        version_provider: Callable[[], int],
        current_dataset_fingerprint: Callable[[], str | None],
        commit_pipeline_change: Callable[[PassportBoundPreparation], int],
    ) -> None:
        if (pipeline_ops is None) == (pipeline_ops_provider is None):
            raise ResearchPreparationError(
                "provide exactly one pipeline operations source"
            )
        if pipeline_ops_provider is None:
            def fixed_pipeline_ops_provider() -> object | None:
                return pipeline_ops

            pipeline_ops_provider = fixed_pipeline_ops_provider
        if not callable(pipeline_ops_provider):
            raise ResearchPreparationError(
                "pipeline operations provider must be callable"
            )
        self._pipeline_ops_provider = pipeline_ops_provider
        if not hasattr(
            self._current_pipeline_ops(),
            "replace_research_os_analysis_step",
        ):
            raise ResearchPreparationError(
                "pipeline operations lack Research OS confirmation"
            )
        for value, name in (
            (version_provider, "version_provider"),
            (current_dataset_fingerprint, "current_dataset_fingerprint"),
            (commit_pipeline_change, "commit_pipeline_change"),
        ):
            if not callable(value):
                raise ResearchPreparationError(f"{name} must be callable")
        self._current_pipeline_version = version_provider
        self._current_dataset_fingerprint = current_dataset_fingerprint
        self._commit_pipeline_change = commit_pipeline_change

    def _current_pipeline_ops(self) -> object:
        try:
            pipeline_ops = self._pipeline_ops_provider()
        except Exception as exc:
            raise ResearchPreparationError(
                "pipeline operations are unavailable"
            ) from exc
        if not hasattr(pipeline_ops, "replace_research_os_analysis_step"):
            raise ResearchPreparationError(
                "pipeline operations lack Research OS confirmation"
            )
        return pipeline_ops

    def review(
        self,
        preparation: PassportBoundPreparation,
        *,
        pipeline_version: int,
    ) -> PreparationReview:
        if not isinstance(preparation, PassportBoundPreparation):
            raise ResearchPreparationError("review requires a passport preparation")
        validate_passport_bound_preparation(preparation)
        if preparation.preflight_disposition is not PreflightDisposition.PREPARE_READY:
            raise ResearchPreparationError("review requires a ready preparation")
        if (
            _read_version(self._current_pipeline_version) != pipeline_version
            or self._current_dataset_fingerprint() != preparation.dataset_fingerprint
        ):
            raise ResearchPreparationError("preparation is stale")
        return PreparationReview(
            preparation=preparation,
            captured_pipeline_version=pipeline_version,
            settings_rows=_settings_rows(preparation),
        )

    def confirm(
        self,
        review: PreparationReview,
        *,
        pipeline_version: int,
    ) -> CommandResult:
        try:
            review.__post_init__()
            preparation = review.preparation
            current_version = _read_version(self._current_pipeline_version)
            if (
                pipeline_version != current_version
                or review.captured_pipeline_version != current_version
                or self._current_dataset_fingerprint()
                != preparation.dataset_fingerprint
            ):
                return self._failure(
                    "현재 데이터가 구성 검토 시점과 달라졌습니다.",
                    "research_preparation_stale",
                    current_version,
                )
            pipeline_ops = self._current_pipeline_ops()
            mapping = PassportStepMapping.create(
                passport_artifact_id=preparation.passport_artifact_id,
                passport_digest=preparation.passport_digest,
                capability_key=preparation.capability_key,
                dataset_fingerprint=preparation.dataset_fingerprint,
                step_type=preparation.step_type,
                canonical_step_params=preparation.canonical_step_params,
            )
            preflight = preflight_mapped_step(
                mapping,
                pipeline_ops.current_dataset(),
                captured_pipeline_version=current_version,
                current_pipeline_version=self._current_pipeline_version,
            )
            if preflight.disposition is PreflightDisposition.STALE:
                return self._failure(
                    "현재 데이터가 구성 검토 시점과 달라졌습니다.",
                    "research_preparation_stale",
                    current_version,
                )
            if preflight.disposition is PreflightDisposition.PREPARE_BLOCKED:
                return self._failure(
                    "현재 데이터에서는 이 구성을 확정할 수 없습니다.",
                    "research_preparation_blocked",
                    current_version,
                )
            if (
                preflight.disposition is not PreflightDisposition.PREPARE_READY
                or preflight.preparation != preparation
            ):
                return self._failure(
                    "봉인된 분석 설정을 다시 검증하지 못했습니다.",
                    "research_preparation_invalid",
                    current_version,
                )

            def commit_exact(value: PassportBoundPreparation) -> int:
                committed = self._commit_pipeline_change(value)
                if type(committed) is not int or committed != current_version + 1:
                    raise ResearchPreparationError(
                        "pipeline version did not advance exactly once"
                    )
                return committed

            committed_result = pipeline_ops.replace_research_os_analysis_step(
                preparation,
                commit_pipeline_change=commit_exact,
            )
            if not isinstance(committed_result, tuple) or len(committed_result) != 2:
                raise ResearchPreparationError(
                    "pipeline confirmation returned no atomic commit result"
                )
            step_id, committed_version = committed_result
            if not isinstance(step_id, str) or type(committed_version) is not int:
                raise ResearchPreparationError(
                    "pipeline confirmation returned malformed identities"
                )
            return CommandResult(
                ok=True,
                message_ko="분석 설정을 확정했습니다. 실행은 아직 시작하지 않았습니다.",
                pipeline_version=committed_version,
                changed_step_ids=[step_id],
            )
        except (ResearchPreparationError, TypeError, ValueError):
            try:
                version = _read_version(self._current_pipeline_version)
            except ResearchPreparationError:
                version = 0
            return self._failure(
                "봉인된 분석 설정을 확정하지 못했습니다.",
                "research_preparation_invalid",
                version,
            )
        except Exception:
            try:
                version = _read_version(self._current_pipeline_version)
            except ResearchPreparationError:
                version = 0
            return self._failure(
                "분석 설정을 파이프라인에 추가하지 못했습니다.",
                "engine_error",
                version,
            )

    @staticmethod
    def _failure(message: str, code: str, version: int) -> CommandResult:
        return CommandResult(
            ok=False,
            message_ko=message,
            error_code=code,
            pipeline_version=version,
        )
