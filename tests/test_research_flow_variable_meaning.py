from dataclasses import replace

import pandas as pd
import pytest

from modori.core import Dataset, Measure, Variable
from modori.research_flow import (
    VariableMeaningReview,
    build_variable_meaning_review,
)
from modori.research_os import P1RoleBindings, P1TaskProfile


def _dataset() -> Dataset:
    frame = pd.DataFrame(
        {
            "score": [1.0, 2.0, 99.0],
            "rank": [1, 2, 3],
            "category": [1, 2, 1],
            "group": [1, 2, 1],
            "before": [1.0, 2.0, 3.0],
            "after": [2.0, 3.0, 4.0],
            "x": [3.0, 2.0, 1.0],
        }
    )
    measures = {
        "score": Measure.SCALE,
        "rank": Measure.ORDINAL,
        "category": Measure.NOMINAL,
        "group": Measure.NOMINAL,
        "before": Measure.SCALE,
        "after": Measure.SCALE,
        "x": Measure.SCALE,
    }
    variables = {
        key: Variable(
            name=key,
            label={
                "score": "인지 점수",
                "rank": "순위",
                "category": "응답 범주",
                "group": "집단",
                "before": "이전 점수",
                "after": "이후 점수",
                "x": "함께 측정한 값",
            }[key],
            measure=measures[key],
            value_labels=(
                {1.0: "낮음", 2.0: "높음"} if key in {"category", "group"} else {}
            ),
            missing_values=[99.0] if key == "score" else [],
            dtype=str(frame[key].dtype),
            origin_step_id="import",
        )
        for key in frame.columns
    }
    return Dataset(df=frame, variables=variables)


def _review(
    profile: P1TaskProfile,
    roles: P1RoleBindings,
    *,
    dataset: Dataset | None = None,
) -> VariableMeaningReview:
    return build_variable_meaning_review(
        dataset or _dataset(),
        dataset_fingerprint="a" * 64,
        pipeline_version=7,
        profile=profile,
        roles=roles,
    )


@pytest.mark.parametrize(
    ("profile", "roles", "expected"),
    (
        (
            P1TaskProfile.NUMERIC_DISTRIBUTION,
            P1RoleBindings(outcome=("score", "rank")),
            (("outcome", "score"), ("outcome", "rank")),
        ),
        (
            P1TaskProfile.CATEGORY_FREQUENCY,
            P1RoleBindings(outcome=("category",)),
            (("outcome", "category"),),
        ),
        (
            P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
            P1RoleBindings(outcome=("score",), group=("group",)),
            (("outcome", "score"), ("group", "group")),
        ),
        (
            P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE,
            P1RoleBindings(repeated_measure_order=("before", "after")),
            (("before", "before"), ("after", "after")),
        ),
        (
            P1TaskProfile.LINEAR_CO_MOVEMENT,
            P1RoleBindings(outcome=("score",), focal_predictor=("x",)),
            (("outcome", "score"), ("focal_predictor", "x")),
        ),
        (
            P1TaskProfile.RANK_CO_MOVEMENT,
            P1RoleBindings(outcome=("rank",), focal_predictor=("x",)),
            (("outcome", "rank"), ("focal_predictor", "x")),
        ),
    ),
)
def test_review_covers_each_closed_p1_role_shape(
    profile: P1TaskProfile,
    roles: P1RoleBindings,
    expected: tuple[tuple[str, str], ...],
) -> None:
    review = _review(profile, roles)

    assert review.profile_id == profile.value
    assert tuple((row.role, row.variable_id) for row in review.rows) == expected
    assert review.dataset_fingerprint == "a" * 64
    assert review.pipeline_version == 7
    assert len(review.review_digest) == 64
    assert review.provenance_ref == (
        f"variable-meaning-review:v1:{review.review_digest}"
    )


def test_review_binds_current_display_metadata_without_inventing_semantics() -> None:
    review = _review(
        P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
        P1RoleBindings(outcome=("score",), group=("group",)),
    )
    score, group = review.rows

    assert score.label == "인지 점수"
    assert score.measure == "scale"
    assert score.value_labels == ()
    assert score.missing_codes == ("99",)
    assert score.storage_dtype == "float64"
    assert score.evidence_source == "current_dataset_metadata"
    assert score.concept_definition_status == "not_recorded"
    assert score.unit_status == "not_recorded"
    assert group.value_labels == (("1", "낮음"), ("2", "높음"))


def test_review_digest_changes_with_every_authority_boundary() -> None:
    roles = P1RoleBindings(outcome=("score",))
    original = _review(P1TaskProfile.NUMERIC_DISTRIBUTION, roles)
    changed_label_dataset = _dataset()
    changed_label_dataset = Dataset(
        df=changed_label_dataset.df,
        variables={
            **changed_label_dataset.variables,
            "score": replace(
                changed_label_dataset.variables["score"],
                label="다른 의미",
            ),
        },
    )
    changed_label = _review(
        P1TaskProfile.NUMERIC_DISTRIBUTION,
        roles,
        dataset=changed_label_dataset,
    )
    changed_version = build_variable_meaning_review(
        _dataset(),
        dataset_fingerprint="a" * 64,
        pipeline_version=8,
        profile=P1TaskProfile.NUMERIC_DISTRIBUTION,
        roles=roles,
    )
    changed_fingerprint = build_variable_meaning_review(
        _dataset(),
        dataset_fingerprint="b" * 64,
        pipeline_version=7,
        profile=P1TaskProfile.NUMERIC_DISTRIBUTION,
        roles=roles,
    )

    assert (
        len(
            {
                original.review_digest,
                changed_label.review_digest,
                changed_version.review_digest,
                changed_fingerprint.review_digest,
            }
        )
        == 4
    )


@pytest.mark.parametrize(
    "roles",
    (
        P1RoleBindings(outcome=("missing",), group=("group",)),
        P1RoleBindings(outcome=("score",)),
        P1RoleBindings(outcome=()),
    ),
)
def test_review_rejects_missing_or_wrong_shape_roles(
    roles: P1RoleBindings,
) -> None:
    with pytest.raises(ValueError):
        _review(P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN, roles)
