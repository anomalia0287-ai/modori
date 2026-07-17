from __future__ import annotations

import re
from pathlib import Path

from modori.ui.controller import UiController
from modori.ui.recommendation_controller import RecommendationControllerMixin
from modori.ui.report_export_controller import ReportExportControllerMixin


def test_ui_controller_preserves_release_and_research_properties() -> None:
    release_api = {
        "canRerun",
        "selectionConfirmationRequired",
        "stepChainDisplayText",
    }
    research_api = {
        "analysisSelectionOrigin",
        "markCurrentSelectionExperimental",
    }

    missing = sorted(
        name for name in release_api | research_api if not hasattr(UiController, name)
    )

    assert missing == []


def test_recommendation_mixin_preserves_both_parent_contracts() -> None:
    release_api = {
        "recommendationKind",
        "preparedReliabilityItems",
        "preparedDescriptiveVariables",
        "preparedVariableKeys",
        "preparedOutcomeKey",
        "preparedGroupKey",
        "preparedPredictorKeys",
        "preparedCovariateKeys",
    }
    research_api = {
        "recommendationRequiresConfiguration",
        "recommendationPreparationPending",
        "experimentalRecommendationConfirmed",
        "preparedRecommendationIntent",
        "preparedRecommendationReviewRequirement",
        "prepareSelectedRecommendationNow",
        "setExperimentalRecommendationConfirmed",
        "clearExperimentalRecommendationPreparation",
        "clearExperimentalRecommendationSelection",
        "preparedRecommendationField",
        "selectedRecommendationFieldText",
        "recommendationCandidateReviewRequirementAt",
    }

    missing = sorted(
        name
        for name in release_api | research_api
        if not hasattr(RecommendationControllerMixin, name)
    )

    assert missing == []

    forbidden_confidence_api = {
        "recommendationLevel",
        "recommendationAlternativesText",
        "recommendationCandidateLevelAt",
    }
    assert not any(
        hasattr(RecommendationControllerMixin, name)
        for name in forbidden_confidence_api
    )


def test_report_export_mixin_owns_qml_export_adapters() -> None:
    expected_api = {
        "exportReportNow",
        "exportReportWithOptions",
        "exportReportWithSelections",
    }

    assert expected_api <= ReportExportControllerMixin.__dict__.keys()
    assert expected_api <= {name for name in expected_api if hasattr(UiController, name)}


def test_legacy_recommendation_mixin_does_not_import_passport_rationale() -> None:
    source = Path("src/modori/ui/recommendation_controller.py").read_text(
        encoding="utf-8"
    )

    assert "question_rationale_presenter" not in source
    assert "QuestionRationalePresenter" not in source
    assert "QuestionRationaleResult" not in source


def test_qml_does_not_alias_legacy_reason_as_passport_rationale() -> None:
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "src/modori/ui/qml/components/GuideRail.qml",
            "src/modori/ui/qml/components/PipelineRail.qml",
        )
    )
    forbidden_alias = re.compile(
        r"(?:question|passport)\w*rationale\w*\s*:\s*"
        r"(?:controller\.)?recommendationReason",
        re.IGNORECASE,
    )

    assert forbidden_alias.search(sources) is None
