from __future__ import annotations

from enum import Enum


class RecommendationEvidenceStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    EXPERIMENTAL = "experimental"
    VALIDATED = "validated"


class RecommendationRoutingPolicy(str, Enum):
    PRIMARY_REVIEW = "primary_review"
    SECONDARY_REVIEW = "secondary_review"
    HEIGHTENED_REVIEW = "heightened_review"
    MANUAL_ONLY = "manual_only"
    NEVER = "never"


class RecommendationRoutingTier(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    HEIGHTENED_REVIEW = "heightened_review"
