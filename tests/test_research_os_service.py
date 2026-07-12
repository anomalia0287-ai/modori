from __future__ import annotations

from dataclasses import replace

import modori.research_os as research_os
from modori.research_os.contracts import (
    AssignmentMechanism,
    AssociationTarget,
    CaptureMode,
    CausalIntent,
    ClaimBasis,
    ContrastKind,
    DataLayout,
    DependenceKind,
    DesignFamily,
    EffectScale,
    EstimandSpec,
    EstimandTemplate,
    Fact,
    Language,
    QuestionSpec,
    ResearchGoal,
    SamplingDesign,
    SchemaEnvelope,
    StudyRole,
    StudyRoleBinding,
    StudySpec,
    TargetRole,
    TargetRoleBinding,
    TemporalStructure,
    UnitKind,
)
from modori.research_os.resolver import PrimaryAction, ProductSurface
from modori.research_os.service import ResearchOsService, ResearchRequest


DATASET_FINGERPRINT = "a" * 64
SCHEMA_FINGERPRINT = "b" * 64
WELCH_KEY = (
    "compare_two_groups:welch_mean_difference:group_contrast_mean:"
    "independent_unweighted:roles-v1"
)
PAIRED_KEY = (
    "compare_two_groups:paired_t_mean_change:within_unit_mean_change:"
    "paired_unweighted:roles-v1"
)
PEARSON_KEY = (
    "bivariate_association:pearson_product_moment:association_correlation:"
    "independent_unweighted:roles-v1"
)
SPEARMAN_KEY = (
    "bivariate_association:spearman_rank_monotonic:association_correlation:"
    "independent_unweighted:roles-v1"
)


def _envelope(schema_id: str, object_id: str, project_id: str = "project-1") -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id=schema_id,
        schema_version=1,
        project_id=project_id,
        object_id=object_id,
        revision=1,
        supersedes_revision=None,
        created_event_ref=f"event:{object_id}:1",
    )


def _confirmed(value: object, ref: str) -> Fact[object]:
    return Fact.user_confirmed(value, provenance_refs=(ref,))


def _question(
    goal: ResearchGoal,
    *,
    causal_intent: CausalIntent = CausalIntent.NONCAUSAL,
    project_id: str = "project-1",
) -> QuestionSpec:
    return QuestionSpec(
        envelope=_envelope("modori.question_spec", "question-1", project_id),
        capture_mode=CaptureMode.STRUCTURED,
        language=Language.KO,
        local_text=None,
        research_goal=Fact.user_confirmed(
            goal,
            provenance_refs=("answer:goal",),
        ),
        causal_intent=Fact.user_confirmed(
            causal_intent,
            provenance_refs=("answer:causal",),
        ),
    )


def _estimand(
    *,
    template: EstimandTemplate,
    effect_scale: EffectScale,
    roles: tuple[tuple[TargetRole, tuple[str, ...]], ...],
    contrast: ContrastKind | None,
    association_target: AssociationTarget | None,
    project_id: str = "project-1",
) -> EstimandSpec:
    target_roles = tuple(
        TargetRoleBinding(
            role=role,
            variable_ids=Fact.user_confirmed(
                variable_ids,
                provenance_refs=(f"answer:role:{role.value}",),
            ),
        )
        for role, variable_ids in roles
    )
    return EstimandSpec(
        envelope=_envelope("modori.estimand_spec", "estimand-1", project_id),
        template=Fact.user_confirmed(
            template,
            provenance_refs=("answer:template",),
        ),
        claim_basis=Fact.user_confirmed(
            (
                ClaimBasis.ASSOCIATIONAL
                if template
                in {
                    EstimandTemplate.ASSOCIATION,
                    EstimandTemplate.GROUP_CONTRAST,
                    EstimandTemplate.WITHIN_UNIT_CHANGE,
                }
                else ClaimBasis.DESCRIPTIVE
            ),
            provenance_refs=("answer:claim",),
        ),
        target_population=Fact.user_confirmed(
            "조사 대상 모집단",
            provenance_refs=("answer:population",),
        ),
        unit_of_analysis=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:unit",),
        ),
        target_roles=target_roles,
        contrast=(
            Fact.not_applicable(reason_code="contrast_not_applicable")
            if contrast is None
            else Fact.user_confirmed(
                contrast,
                provenance_refs=("answer:contrast",),
            )
        ),
        time_scope=Fact.user_confirmed(
            "declared_study_window",
            provenance_refs=("answer:time",),
        ),
        effect_scale=Fact.user_confirmed(
            effect_scale,
            provenance_refs=("answer:scale",),
        ),
        association_target=(
            Fact.not_applicable(reason_code="not_an_association_estimand")
            if association_target is None
            else Fact.user_confirmed(
                association_target,
                provenance_refs=("answer:association-target",),
            )
        ),
    )


def _study(
    *,
    dependence: Fact[DependenceKind],
    temporal: TemporalStructure = TemporalStructure.SINGLE_WAVE,
    layout: DataLayout = DataLayout.UNIT_ROWS,
    weight_binding: Fact[tuple[str, ...]] | None = None,
    include_weight_binding: bool = True,
    repeated_order: Fact[tuple[str, ...]] | None = None,
    project_id: str = "project-1",
) -> StudySpec:
    roles = [
        StudyRoleBinding(
            role=StudyRole.CLUSTER,
            variable_ids=Fact.user_confirmed(
                (),
                provenance_refs=("answer:no-cluster",),
            ),
        )
    ]
    if include_weight_binding:
        roles.append(
            StudyRoleBinding(
                role=StudyRole.WEIGHT,
                variable_ids=(
                    weight_binding
                    if weight_binding is not None
                    else Fact.user_confirmed(
                        (),
                        provenance_refs=("answer:no-weight",),
                    )
                ),
            )
        )
    return StudySpec(
        envelope=_envelope("modori.study_spec", "study-1", project_id),
        dataset_fingerprint=DATASET_FINGERPRINT,
        source_schema_fingerprint=SCHEMA_FINGERPRINT,
        unit_of_observation=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:observation-unit",),
        ),
        unit_of_analysis=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:analysis-unit",),
        ),
        design_family=Fact.user_confirmed(
            DesignFamily.OBSERVATIONAL,
            provenance_refs=("answer:design",),
        ),
        data_layout=Fact.observed(
            layout,
            provenance_refs=("profile:layout",),
        ),
        temporal_structure=Fact.user_confirmed(
            temporal,
            provenance_refs=("answer:temporal",),
        ),
        dependence_structure=dependence,
        assignment_mechanism=Fact.user_confirmed(
            AssignmentMechanism.NONRANDOMIZED,
            provenance_refs=("answer:assignment",),
        ),
        sampling_design=Fact.user_confirmed(
            SamplingDesign.CONVENIENCE,
            provenance_refs=("answer:sampling",),
        ),
        design_roles=tuple(roles),
        repeated_measure_order=(
            repeated_order
            if repeated_order is not None
            else Fact.not_applicable(reason_code="not_a_repeated_design")
        ),
        missing_code_meanings=(),
    )


def _request(
    question: QuestionSpec,
    estimand: EstimandSpec,
    study: StudySpec,
    variables: tuple[str, ...],
    *,
    current_fingerprint: str = DATASET_FINGERPRINT,
    surface: ProductSurface = ProductSurface.EXPERIMENTAL,
) -> ResearchRequest:
    return ResearchRequest(
        question=question,
        estimand=estimand,
        study=study,
        current_dataset_fingerprint=current_fingerprint,
        available_variable_ids=variables,
        surface=surface,
    )


def _independent_mean_request() -> ResearchRequest:
    return _request(
        _question(ResearchGoal.COMPARE),
        _estimand(
            template=EstimandTemplate.GROUP_CONTRAST,
            effect_scale=EffectScale.DIFFERENCE,
            roles=(
                (TargetRole.OUTCOME, ("score",)),
                (TargetRole.GROUP, ("arm",)),
            ),
            contrast=ContrastKind.PAIRWISE,
            association_target=None,
        ),
        _study(
            dependence=Fact.user_confirmed(
                DependenceKind.INDEPENDENT,
                provenance_refs=("answer:dependence",),
            )
        ),
        ("arm", "score"),
    )


def _association_request(target: AssociationTarget) -> ResearchRequest:
    return _request(
        _question(ResearchGoal.ASSOCIATE),
        _estimand(
            template=EstimandTemplate.ASSOCIATION,
            effect_scale=EffectScale.CORRELATION,
            roles=(
                (TargetRole.OUTCOME, ("stress",)),
                (TargetRole.FOCAL_PREDICTOR, ("sleep",)),
            ),
            contrast=None,
            association_target=target,
        ),
        _study(
            dependence=Fact.user_confirmed(
                DependenceKind.INDEPENDENT,
                provenance_refs=("answer:dependence",),
            )
        ),
        ("stress", "sleep"),
    )


def _paired_request(dependence: Fact[DependenceKind]) -> ResearchRequest:
    return _request(
        _question(ResearchGoal.COMPARE),
        _estimand(
            template=EstimandTemplate.WITHIN_UNIT_CHANGE,
            effect_scale=EffectScale.DIFFERENCE,
            roles=(
                (TargetRole.OUTCOME, ("post",)),
                (TargetRole.REPEATED_MEASURE, ("pre", "post")),
            ),
            contrast=ContrastKind.PAIRWISE,
            association_target=None,
        ),
        _study(
            dependence=dependence,
            temporal=TemporalStructure.REPEATED_PANEL,
            layout=DataLayout.WIDE_REPEATED,
            repeated_order=Fact.user_confirmed(
                ("pre", "post"),
                provenance_refs=("answer:repeated-order",),
            ),
        ),
        ("id", "pre", "post"),
    )


def test_independent_mean_request_resolves_only_exact_welch_identity() -> None:
    decision = ResearchOsService().resolve(_independent_mean_request())

    assert decision.action is PrimaryAction.RECOMMEND_LOCAL
    assert decision.capability_keys == (WELCH_KEY,)
    assert not any("rank" in key for key in decision.capability_keys)


def test_association_target_switches_exact_identity_without_data_change() -> None:
    pearson = ResearchOsService().resolve(
        _association_request(AssociationTarget.PRODUCT_MOMENT)
    )
    spearman = ResearchOsService().resolve(
        _association_request(AssociationTarget.RANK_MONOTONIC)
    )

    assert pearson.capability_keys == (PEARSON_KEY,)
    assert spearman.capability_keys == (SPEARMAN_KEY,)


def test_unknown_pairing_returns_clarification_without_candidate() -> None:
    decision = ResearchOsService().resolve(
        _paired_request(Fact.unknown(reason_code="pairing_not_confirmed"))
    )

    assert decision.action is PrimaryAction.CLARIFY
    assert decision.capability_keys == ()
    assert "confirm_dependence" in decision.clarification_ids


def test_inferred_pairing_cannot_open_paired_recommendation() -> None:
    decision = ResearchOsService().resolve(
        _paired_request(
            Fact.inferred(
                DependenceKind.PAIRED,
                provenance_refs=("lexical:pre-post-columns",),
            )
        )
    )

    assert decision.action is PrimaryAction.CLARIFY
    assert decision.capability_keys == ()


def test_absent_weight_binding_is_unknown_not_unweighted() -> None:
    request = _independent_mean_request()
    request = replace(
        request,
        study=_study(
            dependence=Fact.user_confirmed(
                DependenceKind.INDEPENDENT,
                provenance_refs=("answer:dependence",),
            ),
            include_weight_binding=False,
        ),
    )

    decision = ResearchOsService().resolve(request)

    assert decision.action is PrimaryAction.CLARIFY
    assert "confirm_weight_use" in decision.clarification_ids


def test_causal_request_fails_closed_in_p1() -> None:
    request = _independent_mean_request()
    request = replace(
        request,
        question=_question(
            ResearchGoal.ESTIMATE_EFFECT,
            causal_intent=CausalIntent.CAUSAL,
        ),
    )

    decision = ResearchOsService().resolve(request)

    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.reason_codes == ("unsupported_causal_target",)


def test_project_mismatch_is_an_integrity_abstention() -> None:
    request = _independent_mean_request()
    request = replace(
        request,
        estimand=replace(
            request.estimand,
            envelope=replace(request.estimand.envelope, project_id="project-2"),
        ),
    )

    decision = ResearchOsService().resolve(request)

    assert decision.action is PrimaryAction.ABSTAIN
    assert "integrity:project_id_mismatch" in decision.reason_codes


def test_stale_dataset_binding_is_an_integrity_abstention() -> None:
    request = replace(
        _independent_mean_request(),
        current_dataset_fingerprint="c" * 64,
    )

    decision = ResearchOsService().resolve(request)

    assert decision.action is PrimaryAction.ABSTAIN
    assert "integrity:dataset_fingerprint_mismatch" in decision.reason_codes


def test_unknown_role_variable_is_an_integrity_abstention() -> None:
    request = replace(
        _independent_mean_request(),
        available_variable_ids=("arm",),
    )

    decision = ResearchOsService().resolve(request)

    assert decision.action is PrimaryAction.ABSTAIN
    assert "integrity:unknown_variable_reference" in decision.reason_codes


def test_available_variable_order_does_not_change_decision() -> None:
    request = _independent_mean_request()
    reversed_request = replace(
        request,
        available_variable_ids=tuple(reversed(request.available_variable_ids)),
    )

    left = ResearchOsService().resolve(request)
    right = ResearchOsService().resolve(reversed_request)

    assert left.semantic_signature == right.semantic_signature


def test_experimental_p1_catalog_does_not_emit_on_ordinary_surface() -> None:
    request = replace(
        _independent_mean_request(),
        surface=ProductSurface.ORDINARY,
    )

    decision = ResearchOsService().resolve(request)

    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.capability_keys == ()


def test_paired_mean_request_resolves_exact_paired_t_identity() -> None:
    decision = ResearchOsService().resolve(
        _paired_request(
            Fact.user_confirmed(
                DependenceKind.PAIRED,
                provenance_refs=("answer:dependence",),
            )
        )
    )

    assert decision.action is PrimaryAction.RECOMMEND_LOCAL
    assert decision.capability_keys == (PAIRED_KEY,)


def test_p1_service_is_exposed_from_research_os_package() -> None:
    assert research_os.ResearchOsService is ResearchOsService
    assert research_os.ResearchRequest is ResearchRequest
    assert callable(research_os.build_p1_method_space)
