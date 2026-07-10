from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from modori.core import Dataset
from modori.recommendation_benchmark import (
    PredictionRecord,
    PrimaryAction,
    RecommendationIdentity,
)
from modori.recommendations import RecommendationCandidate, RecommendationService
from modori.steps.data_prep import metadata_variables
from modori.table_io import read_full


_FAMILY_BY_KIND = {
    "descriptives": "descriptives_table1",
    "reliability": "reliability",
    "comparison": "compare_groups",
    "regression": "regression_ols",
    "logistic_regression": "logistic_regression",
    "frequency_crosstab": "frequency_crosstab",
    "correlation": "correlation",
    "anova_oneway": "anova_oneway",
    "kruskal_wallis": "kruskal_wallis",
    "ancova": "ancova",
    "factor_pca": "factor_pca",
    "repeated_measures_anova": "repeated_measures_anova",
    "friedman": "friedman",
    "mediation": "mediation",
    "moderated_mediation": "moderated_mediation",
}
_DESIGN_MODE_BY_KIND = {
    "descriptives": "table1",
    "reliability": "scale_items",
    "comparison": "independent",
    "regression": "main_effects",
    "logistic_regression": "binary_main_effects",
    "frequency_crosstab": "categorical",
    "correlation": "bivariate",
    "anova_oneway": "independent_oneway",
    "kruskal_wallis": "independent_rank",
    "ancova": "main_effects",
    "factor_pca": "exploratory",
    "repeated_measures_anova": "repeated_wide",
    "friedman": "repeated_rank_wide",
    "mediation": "simple",
    "moderated_mediation": "conditional_process",
}
_LEVEL_MAP = {
    "강한 추천": "strong",
    "가능한 후보": "candidate",
    "주의 필요": "caution",
}


def _required_text(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"baseline case missing {key}")
    return value.strip()


def load_case_dataset(case: Mapping[str, object], pilot_root: Path) -> Dataset:
    data_file = _required_text(case, "data_file")
    root_resolved = pilot_root.resolve()
    data_path = (pilot_root / data_file).resolve()
    if data_path != root_resolved and root_resolved not in data_path.parents:
        raise ValueError("baseline case data path escapes pilot root")
    file_type = data_path.suffix.lower().lstrip(".")
    if file_type not in {"csv", "xlsx", "xls", "sav"}:
        raise ValueError(f"unsupported baseline case file type: {file_type}")
    result = read_full(data_path, file_type)
    variables = metadata_variables(
        result.frame,
        origin_step_id="benchmark-import",
        metadata=result.metadata,
    )
    return Dataset(df=result.frame, variables=variables)


def candidate_identity(candidate: RecommendationCandidate) -> RecommendationIdentity:
    family = _FAMILY_BY_KIND.get(candidate.kind)
    design_mode = _DESIGN_MODE_BY_KIND.get(candidate.kind)
    if family is None or design_mode is None:
        raise ValueError(f"unsupported baseline recommendation kind: {candidate.kind}")
    roles: list[tuple[str, tuple[str, ...]]] = []
    if candidate.outcome_key:
        roles.append(("outcome", (candidate.outcome_key,)))
    if candidate.group_key:
        roles.append(("group", (candidate.group_key,)))
    if candidate.predictor_keys:
        roles.append(("predictors", tuple(candidate.predictor_keys)))
    if candidate.item_keys:
        roles.append(("items", tuple(candidate.item_keys)))
    if candidate.variable_keys:
        roles.append(("variables", tuple(candidate.variable_keys)))
    if not roles:
        raise ValueError(
            f"baseline candidate has no normalized roles: {candidate.candidate_id}"
        )
    return RecommendationIdentity(
        family=family,
        roles=tuple(roles),
        design_mode=design_mode,
    )


def predict_current_baseline(
    case: Mapping[str, object],
    dataset: Dataset,
) -> PredictionRecord:
    case_id = _required_text(case, "case_id")
    evidence_stage = _required_text(case, "evidence_stage")
    state = RecommendationService().recommend(dataset)
    candidates = tuple(
        candidate_identity(candidate) for candidate in state.candidates[:3]
    )
    if state.default_candidate is None:
        reason = (
            "caution_only_requires_user_selection"
            if state.candidates
            else "no_safe_candidate"
        )
        return PredictionRecord(
            case_id=case_id,
            evidence_stage=evidence_stage,
            primary_action=PrimaryAction(kind="abstain", value=reason),
            candidates=candidates,
            level="none",
        )
    default_identity = candidate_identity(state.default_candidate)
    if not candidates or candidates[0] != default_identity:
        raise ValueError("current baseline default is not the first ranked candidate")
    return PredictionRecord(
        case_id=case_id,
        evidence_stage=evidence_stage,
        primary_action=PrimaryAction(kind="recommend", value=default_identity),
        candidates=candidates,
        level=_LEVEL_MAP[state.default_candidate.level],
    )
