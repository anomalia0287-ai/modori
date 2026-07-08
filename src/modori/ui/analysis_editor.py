from __future__ import annotations

from collections.abc import Callable

from modori.ui.commands import AnalysisSelectionCommandBuilder, PipelineStepCommand
from modori.ui.contracts import CommandResult
from modori.ui.patches import PatchValidationError
from modori.ui.service_contracts import AnalysisPipelineOps


class AnalysisSelectionEditor:
    def __init__(self, pipeline_ops: AnalysisPipelineOps) -> None:
        self._pipeline_ops = pipeline_ops

    def reliability(self, item_keys_text: str, *, pipeline_version: int) -> CommandResult:
        return self._apply(
            lambda builder: builder.reliability(item_keys_text),
            pipeline_version=pipeline_version,
        )

    def descriptives(
        self,
        variable_keys_text: str,
        *,
        group_key: str = "",
        pipeline_version: int,
    ) -> CommandResult:
        return self._apply(
            lambda builder: builder.descriptives(
                variable_keys_text,
                group_key=group_key,
            ),
            pipeline_version=pipeline_version,
        )

    def comparison(
        self,
        outcome_key: str,
        group_key: str,
        *,
        pipeline_version: int,
    ) -> CommandResult:
        return self._apply(
            lambda builder: builder.comparison(outcome_key, group_key),
            pipeline_version=pipeline_version,
        )

    def regression(
        self,
        outcome_key: str,
        predictor_keys_text: str,
        *,
        pipeline_version: int,
    ) -> CommandResult:
        return self._apply(
            lambda builder: builder.regression(outcome_key, predictor_keys_text),
            pipeline_version=pipeline_version,
        )

    def frequency_crosstab(
        self,
        variable_keys_text: str,
        *,
        pipeline_version: int,
    ) -> CommandResult:
        return self._apply(
            lambda builder: builder.frequency_crosstab(variable_keys_text),
            pipeline_version=pipeline_version,
        )

    def correlation(
        self,
        variable_keys_text: str,
        *,
        pipeline_version: int,
    ) -> CommandResult:
        return self._apply(
            lambda builder: builder.correlation(variable_keys_text),
            pipeline_version=pipeline_version,
        )

    def anova_oneway(
        self,
        outcome_key: str,
        group_key: str,
        *,
        pipeline_version: int,
    ) -> CommandResult:
        return self._apply(
            lambda builder: builder.anova_oneway(outcome_key, group_key),
            pipeline_version=pipeline_version,
        )

    def kruskal_wallis(
        self,
        dependent_key: str,
        group_key: str,
        *,
        pipeline_version: int,
    ) -> CommandResult:
        return self._apply(
            lambda builder: builder.kruskal_wallis(dependent_key, group_key),
            pipeline_version=pipeline_version,
        )

    def ancova(
        self,
        outcome_key: str,
        group_key: str,
        covariate_keys_text: str,
        *,
        pipeline_version: int,
    ) -> CommandResult:
        return self._apply(
            lambda builder: builder.ancova(
                outcome_key,
                group_key,
                covariate_keys_text,
            ),
            pipeline_version=pipeline_version,
        )

    def factor_pca(
        self,
        variable_keys_text: str,
        *,
        pipeline_version: int,
    ) -> CommandResult:
        return self._apply(
            lambda builder: builder.factor_pca(variable_keys_text),
            pipeline_version=pipeline_version,
        )

    def _apply(
        self,
        build_command: Callable[[AnalysisSelectionCommandBuilder], PipelineStepCommand],
        *,
        pipeline_version: int,
    ) -> CommandResult:
        try:
            command = build_command(self._builder())
        except PatchValidationError as exc:
            return CommandResult(
                ok=False,
                message_ko=exc.message_ko,
                error_code=exc.error_code,
                pipeline_version=pipeline_version,
            )
        try:
            replace_analysis = getattr(self._pipeline_ops, "replace_managed_analysis_steps", None)
            pipeline = self._pipeline_ops.step_collection()
            if callable(replace_analysis) and pipeline is not None and hasattr(pipeline, "add"):
                replace_analysis(
                    step_id=command.step_id,
                    step_type=command.step_type,
                    params=command.params,
                )
            else:
                self._pipeline_ops.edit_params(command.step_id, command.params)
        except Exception:
            return CommandResult(
                ok=False,
                message_ko="분석 단계를 수정하지 못했습니다.",
                error_code="engine_error",
                pipeline_version=pipeline_version,
            )
        return CommandResult(
            ok=True,
            message_ko=command.message_ko,
            pipeline_version=pipeline_version,
            changed_step_ids=[command.step_id],
        )

    def _builder(self) -> AnalysisSelectionCommandBuilder:
        return AnalysisSelectionCommandBuilder(
            pipeline=self._pipeline_ops.step_collection(),
            variable_keys=self._pipeline_ops.known_variable_keys(),
        )
