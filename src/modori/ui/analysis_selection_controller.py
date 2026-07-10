from __future__ import annotations

import re

from PySide6.QtCore import Slot

from modori.ui.contracts import CommandResult
from modori.ui.value_tokens import (
    categorical_reference_options,
    observed_value_options,
)


class AnalysisSelectionControllerMixin:
    @Slot(str, result="QVariantList")
    def logisticOutcomeOptions(self, outcome_key: str) -> list[dict[str, str]]:
        try:
            return observed_value_options(
                self._services.pipeline_ops.current_dataset(),
                outcome_key,
            )
        except ValueError:
            return []

    @Slot(str, result="QVariantList")
    def logisticCategoricalReferenceOptions(
        self,
        predictor_keys_text: str,
    ) -> list[dict[str, object]]:
        predictor_keys = [
            part
            for part in re.split(r"[\s,;]+", str(predictor_keys_text).strip())
            if part
        ]
        try:
            return categorical_reference_options(
                self._services.pipeline_ops.current_dataset(),
                predictor_keys,
            )
        except ValueError:
            return []

    def configureReliabilitySelection(self, item_keys_text: str) -> CommandResult:
        result = self._services.analysis_editor.reliability(
            item_keys_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, result=bool)
    def configureReliabilityFromText(self, item_keys_text: str) -> bool:
        return self.configureReliabilitySelection(item_keys_text).ok

    def configureDescriptivesSelection(
        self,
        variable_keys_text: str,
        *,
        group_key: str = "",
    ) -> CommandResult:
        result = self._services.analysis_editor.descriptives(
            variable_keys_text,
            group_key=group_key,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, result=bool)
    def configureDescriptivesFromText(
        self,
        variable_keys_text: str,
        group_key: str,
    ) -> bool:
        return self.configureDescriptivesSelection(
            variable_keys_text,
            group_key=group_key,
        ).ok

    def configureComparisonSelection(self, outcome_key: str, group_key: str) -> CommandResult:
        result = self._services.analysis_editor.comparison(
            outcome_key,
            group_key,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, result=bool)
    def configureComparisonFromText(self, outcome_key: str, group_key: str) -> bool:
        return self.configureComparisonSelection(outcome_key, group_key).ok

    def configureRegressionSelection(
        self,
        outcome_key: str,
        predictor_keys_text: str,
    ) -> CommandResult:
        result = self._services.analysis_editor.regression(
            outcome_key,
            predictor_keys_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, result=bool)
    def configureRegressionFromText(self, outcome_key: str, predictor_keys_text: str) -> bool:
        return self.configureRegressionSelection(outcome_key, predictor_keys_text).ok

    def configureLogisticRegression(
        self,
        outcome_key: str,
        event_token: str,
        predictor_keys_text: str,
        categorical_reference_tokens: dict[str, str] | None = None,
    ) -> CommandResult:
        result = self._services.analysis_editor.logistic_regression(
            outcome_key,
            event_token,
            predictor_keys_text,
            categorical_reference_tokens,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, str, "QVariantMap", result=bool)
    def configureLogisticRegressionFromTokens(
        self,
        outcome_key: str,
        event_token: str,
        predictor_keys_text: str,
        categorical_reference_tokens: dict[str, str],
    ) -> bool:
        return self.configureLogisticRegression(
            outcome_key,
            event_token,
            predictor_keys_text,
            categorical_reference_tokens,
        ).ok

    def configureFrequencyCrosstabSelection(self, variable_keys_text: str) -> CommandResult:
        result = self._services.analysis_editor.frequency_crosstab(
            variable_keys_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, result=bool)
    def configureFrequencyCrosstabFromText(self, variable_keys_text: str) -> bool:
        return self.configureFrequencyCrosstabSelection(variable_keys_text).ok

    def configureCorrelationSelection(self, variable_keys_text: str) -> CommandResult:
        result = self._services.analysis_editor.correlation(
            variable_keys_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, result=bool)
    def configureCorrelationFromText(self, variable_keys_text: str) -> bool:
        return self.configureCorrelationSelection(variable_keys_text).ok

    def configureAnovaOneWaySelection(
        self,
        outcome_key: str,
        group_key: str,
    ) -> CommandResult:
        result = self._services.analysis_editor.anova_oneway(
            outcome_key,
            group_key,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, result=bool)
    def configureAnovaOneWayFromText(self, outcome_key: str, group_key: str) -> bool:
        return self.configureAnovaOneWaySelection(outcome_key, group_key).ok

    def configureKruskalWallisSelection(
        self,
        dependent_key: str,
        group_key: str,
    ) -> CommandResult:
        result = self._services.analysis_editor.kruskal_wallis(
            dependent_key,
            group_key,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, result=bool)
    def configureKruskalWallisFromText(self, dependent_key: str, group_key: str) -> bool:
        return self.configureKruskalWallisSelection(dependent_key, group_key).ok

    def configureAncovaSelection(
        self,
        outcome_key: str,
        group_key: str,
        covariate_keys_text: str,
    ) -> CommandResult:
        result = self._services.analysis_editor.ancova(
            outcome_key,
            group_key,
            covariate_keys_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, str, result=bool)
    def configureAncovaFromText(
        self,
        outcome_key: str,
        group_key: str,
        covariate_keys_text: str,
    ) -> bool:
        return self.configureAncovaSelection(
            outcome_key,
            group_key,
            covariate_keys_text,
        ).ok

    def configureFactorPcaSelection(self, variable_keys_text: str) -> CommandResult:
        result = self._services.analysis_editor.factor_pca(
            variable_keys_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, result=bool)
    def configureFactorPcaFromText(self, variable_keys_text: str) -> bool:
        return self.configureFactorPcaSelection(variable_keys_text).ok

    def configureRepeatedMeasuresAnovaSelection(self, measures_text: str) -> CommandResult:
        result = self._services.analysis_editor.repeated_measures_anova(
            measures_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, result=bool)
    def configureRepeatedMeasuresAnovaFromText(self, measures_text: str) -> bool:
        return self.configureRepeatedMeasuresAnovaSelection(measures_text).ok

    def configureFriedmanSelection(self, measures_text: str) -> CommandResult:
        result = self._services.analysis_editor.friedman(
            measures_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, result=bool)
    def configureFriedmanFromText(self, measures_text: str) -> bool:
        return self.configureFriedmanSelection(measures_text).ok

    def configureMediationSelection(
        self,
        x_key: str,
        mediator_key: str,
        y_key: str,
        covariate_keys_text: str = "",
    ) -> CommandResult:
        result = self._services.analysis_editor.mediation(
            x_key,
            mediator_key,
            y_key,
            covariate_keys_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, str, str, result=bool)
    def configureMediationFromText(
        self,
        x_key: str,
        mediator_key: str,
        y_key: str,
        covariate_keys_text: str,
    ) -> bool:
        return self.configureMediationSelection(
            x_key,
            mediator_key,
            y_key,
            covariate_keys_text,
        ).ok

    def configureModeratedMediationSelection(
        self,
        model: str,
        x_key: str,
        mediator_key: str,
        moderator_key: str,
        y_key: str,
        covariate_keys_text: str = "",
    ) -> CommandResult:
        result = self._services.analysis_editor.moderated_mediation(
            model,
            x_key,
            mediator_key,
            moderator_key,
            y_key,
            covariate_keys_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, str, str, str, str, result=bool)
    def configureModeratedMediationFromText(
        self,
        model: str,
        x_key: str,
        mediator_key: str,
        moderator_key: str,
        y_key: str,
        covariate_keys_text: str,
    ) -> bool:
        return self.configureModeratedMediationSelection(
            model,
            x_key,
            mediator_key,
            moderator_key,
            y_key,
            covariate_keys_text,
        ).ok
