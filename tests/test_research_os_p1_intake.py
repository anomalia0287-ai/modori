from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import inspect

import pytest

from modori.research_os import (
    AnswerValue,
    AnswerValueKind,
    AssociationTarget,
    CaptureMode,
    CausalIntent,
    ClaimBasis,
    ClarificationAnswerEvent,
    ClarificationTransitionService,
    ContrastKind,
    DataLayout,
    DependenceKind,
    EffectScale,
    EstimandTemplate,
    Fact,
    FactState,
    Language,
    P1IntakeDraft,
    P1IntakeError,
    P1RoleBindings,
    P1TaskProfile,
    PrimaryAction,
    ProductSurface,
    ResearchGoal,
    ResearchOsService,
    ResearchRequest,
    SchemaEnvelope,
    StudyRole,
    StudyRoleBinding,
    TargetRole,
    TemporalStructure,
    TransitionError,
    build_causal_abstention_request,
    build_p1_request,
)


DATASET_FINGERPRINT = "a" * 64
SOURCE_SCHEMA_FINGERPRINT = "b" * 64
TASK_PROJECT_ID = "task:p1:1"
INITIAL_EVENT_ID = "event:project:1"
VARIABLES = (
    "outcome",
    "group",
    "before",
    "after",
    "x",
    "y",
    "weight",
    "cluster",
)


def _roles(profile: P1TaskProfile) -> P1RoleBindings:
    if profile in {
        P1TaskProfile.NUMERIC_DISTRIBUTION,
        P1TaskProfile.CATEGORY_FREQUENCY,
    }:
        return P1RoleBindings(outcome=("outcome", "x"))
    if profile is P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN:
        return P1RoleBindings(outcome=("outcome",), group=("group",))
    if profile is P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE:
        return P1RoleBindings(repeated_measure_order=("before", "after"))
    return P1RoleBindings(outcome=("y",), focal_predictor=("x",))


def _request(profile: P1TaskProfile) -> ResearchRequest:
    return build_p1_request(
        P1IntakeDraft(profile=profile, roles=_roles(profile)),
        task_project_id=TASK_PROJECT_ID,
        initial_event_id=INITIAL_EVENT_ID,
        dataset_fingerprint=DATASET_FINGERPRINT,
        source_schema_fingerprint=SOURCE_SCHEMA_FINGERPRINT,
        available_variable_ids=VARIABLES,
        language=Language.KO,
    )


PROFILE_FACTS = (
    (
        P1TaskProfile.NUMERIC_DISTRIBUTION,
        ResearchGoal.DESCRIBE,
        EstimandTemplate.SUMMARY,
        ClaimBasis.DESCRIPTIVE,
        EffectScale.DISTRIBUTION,
        None,
        None,
        None,
        None,
        None,
    ),
    (
        P1TaskProfile.CATEGORY_FREQUENCY,
        ResearchGoal.DESCRIBE,
        EstimandTemplate.FREQUENCY_DISTRIBUTION,
        ClaimBasis.DESCRIPTIVE,
        EffectScale.DISTRIBUTION,
        None,
        None,
        None,
        None,
        None,
    ),
    (
        P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
        ResearchGoal.COMPARE,
        EstimandTemplate.GROUP_CONTRAST,
        ClaimBasis.ASSOCIATIONAL,
        EffectScale.DIFFERENCE,
        None,
        ContrastKind.PAIRWISE,
        DependenceKind.INDEPENDENT,
        None,
        None,
    ),
    (
        P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE,
        ResearchGoal.COMPARE,
        EstimandTemplate.WITHIN_UNIT_CHANGE,
        ClaimBasis.ASSOCIATIONAL,
        EffectScale.DIFFERENCE,
        None,
        ContrastKind.PAIRWISE,
        DependenceKind.PAIRED,
        DataLayout.WIDE_REPEATED,
        TemporalStructure.REPEATED_PANEL,
    ),
    (
        P1TaskProfile.LINEAR_CO_MOVEMENT,
        ResearchGoal.ASSOCIATE,
        EstimandTemplate.ASSOCIATION,
        ClaimBasis.ASSOCIATIONAL,
        EffectScale.CORRELATION,
        AssociationTarget.PRODUCT_MOMENT,
        None,
        None,
        None,
        None,
    ),
    (
        P1TaskProfile.RANK_CO_MOVEMENT,
        ResearchGoal.ASSOCIATE,
        EstimandTemplate.ASSOCIATION,
        ClaimBasis.ASSOCIATIONAL,
        EffectScale.CORRELATION,
        AssociationTarget.RANK_MONOTONIC,
        None,
        None,
        None,
        None,
    ),
)


@pytest.mark.parametrize(
    (
        "profile",
        "goal",
        "template",
        "claim",
        "scale",
        "association",
        "contrast",
        "dependence",
        "layout",
        "temporal",
    ),
    PROFILE_FACTS,
)
def test_profile_mapping_sets_only_the_exact_visible_facts(
    profile: P1TaskProfile,
    goal: ResearchGoal,
    template: EstimandTemplate,
    claim: ClaimBasis,
    scale: EffectScale,
    association: AssociationTarget | None,
    contrast: ContrastKind | None,
    dependence: DependenceKind | None,
    layout: DataLayout | None,
    temporal: TemporalStructure | None,
) -> None:
    request = _request(profile)

    assert request.surface is ProductSurface.EXPERIMENTAL
    assert request.question_budget_remaining == 3
    assert request.current_dataset_fingerprint == DATASET_FINGERPRINT
    assert request.available_variable_ids == VARIABLES
    assert request.study.dataset_fingerprint == DATASET_FINGERPRINT
    assert request.study.source_schema_fingerprint == SOURCE_SCHEMA_FINGERPRINT
    assert {
        request.question.envelope.project_id,
        request.estimand.envelope.project_id,
        request.study.envelope.project_id,
    } == {TASK_PROJECT_ID}
    assert {
        request.question.envelope.created_event_ref,
        request.estimand.envelope.created_event_ref,
        request.study.envelope.created_event_ref,
    } == {INITIAL_EVENT_ID}

    assert request.question.capture_mode is CaptureMode.STRUCTURED
    assert request.question.language is Language.KO
    assert request.question.local_text is None
    assert request.question.role_hints == ()
    assert request.question.research_goal.state is FactState.USER_CONFIRMED
    assert request.question.research_goal.value is goal
    assert request.question.causal_intent.state is FactState.USER_CONFIRMED
    assert request.question.causal_intent.value is CausalIntent.NONCAUSAL

    assert request.estimand.template.state is FactState.USER_CONFIRMED
    assert request.estimand.template.value is template
    assert request.estimand.claim_basis.state is FactState.USER_CONFIRMED
    assert request.estimand.claim_basis.value is claim
    assert request.estimand.effect_scale.state is FactState.USER_CONFIRMED
    assert request.estimand.effect_scale.value is scale
    if association is None:
        assert request.estimand.association_target.state is FactState.NOT_APPLICABLE
        assert request.estimand.association_target.value is None
    else:
        assert request.estimand.association_target.state is FactState.USER_CONFIRMED
        assert request.estimand.association_target.value is association
    if contrast is None:
        assert request.estimand.contrast.state is FactState.NOT_APPLICABLE
        assert request.estimand.contrast.value is None
    else:
        assert request.estimand.contrast.state is FactState.USER_CONFIRMED
        assert request.estimand.contrast.value is contrast

    for unknown in (
        request.estimand.target_population,
        request.estimand.unit_of_analysis,
        request.estimand.time_scope,
        request.study.unit_of_observation,
        request.study.unit_of_analysis,
        request.study.design_family,
        request.study.assignment_mechanism,
        request.study.sampling_design,
    ):
        assert unknown.state is FactState.UNKNOWN
        assert unknown.value is None

    for fact, expected in (
        (request.study.dependence_structure, dependence),
        (request.study.data_layout, layout),
        (request.study.temporal_structure, temporal),
    ):
        if expected is None:
            assert fact.state is FactState.UNKNOWN
            assert fact.value is None
        else:
            assert fact.state is FactState.USER_CONFIRMED
            assert fact.value is expected
    assert request.study.design_roles == ()
    assert request.study.missing_code_meanings == ()


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
def test_profile_roles_have_exact_cardinality_order_and_user_authority(
    profile: P1TaskProfile,
) -> None:
    request = _request(profile)
    roles = {
        binding.role: binding.variable_ids
        for binding in request.estimand.target_roles
    }
    assert all(fact.state is FactState.USER_CONFIRMED for fact in roles.values())

    if profile in {
        P1TaskProfile.NUMERIC_DISTRIBUTION,
        P1TaskProfile.CATEGORY_FREQUENCY,
    }:
        assert {role: fact.value for role, fact in roles.items()} == {
            TargetRole.OUTCOME: ("outcome", "x")
        }
        assert request.study.repeated_measure_order.state is FactState.UNKNOWN
    elif profile is P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN:
        assert {role: fact.value for role, fact in roles.items()} == {
            TargetRole.OUTCOME: ("outcome",),
            TargetRole.GROUP: ("group",),
        }
        assert request.study.repeated_measure_order.state is FactState.UNKNOWN
    elif profile is P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE:
        assert {role: fact.value for role, fact in roles.items()} == {
            TargetRole.OUTCOME: ("after",),
            TargetRole.REPEATED_MEASURE: ("before", "after"),
        }
        assert request.study.repeated_measure_order.state is FactState.USER_CONFIRMED
        assert request.study.repeated_measure_order.value == ("before", "after")
    else:
        assert {role: fact.value for role, fact in roles.items()} == {
            TargetRole.OUTCOME: ("y",),
            TargetRole.FOCAL_PREDICTOR: ("x",),
        }
        assert request.study.repeated_measure_order.state is FactState.UNKNOWN


def test_intake_contracts_are_frozen_closed_and_have_no_causal_or_design_role_input() -> None:
    roles = P1RoleBindings(outcome=("outcome",))
    draft = P1IntakeDraft(
        profile=P1TaskProfile.NUMERIC_DISTRIBUTION,
        roles=roles,
    )

    assert tuple(P1RoleBindings.__dataclass_fields__) == (
        "outcome",
        "group",
        "focal_predictor",
        "repeated_measure_order",
    )
    assert tuple(P1IntakeDraft.__dataclass_fields__) == ("profile", "roles")
    with pytest.raises(FrozenInstanceError):
        roles.outcome = ("x",)  # type: ignore[misc]
    with pytest.raises(TypeError, match="weight"):
        P1RoleBindings(weight=("weight",))  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="cluster"):
        P1RoleBindings(cluster=("cluster",))  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="causal"):
        P1IntakeDraft(  # type: ignore[call-arg]
            profile=P1TaskProfile.NUMERIC_DISTRIBUTION,
            roles=roles,
            causal_intent=CausalIntent.CAUSAL,
        )
    assert "causal_intent" not in inspect.signature(build_p1_request).parameters
    assert draft.roles == roles


@pytest.mark.parametrize(
    "draft",
    (
        P1IntakeDraft(
            P1TaskProfile.NUMERIC_DISTRIBUTION,
            P1RoleBindings(),
        ),
        P1IntakeDraft(
            P1TaskProfile.NUMERIC_DISTRIBUTION,
            P1RoleBindings(outcome=("outcome",), group=("group",)),
        ),
        P1IntakeDraft(
            P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
            P1RoleBindings(outcome=("outcome", "x"), group=("group",)),
        ),
        P1IntakeDraft(
            P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
            P1RoleBindings(outcome=("outcome",), group=()),
        ),
        P1IntakeDraft(
            P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE,
            P1RoleBindings(repeated_measure_order=("before",)),
        ),
        P1IntakeDraft(
            P1TaskProfile.RANK_CO_MOVEMENT,
            P1RoleBindings(outcome=("y",), focal_predictor=()),
        ),
    ),
)
def test_wrong_cardinality_undeclared_and_duplicate_roles_fail_closed(
    draft: P1IntakeDraft,
) -> None:
    with pytest.raises(P1IntakeError):
        build_p1_request(
            draft,
            task_project_id=TASK_PROJECT_ID,
            initial_event_id=INITIAL_EVENT_ID,
            dataset_fingerprint=DATASET_FINGERPRINT,
            source_schema_fingerprint=SOURCE_SCHEMA_FINGERPRINT,
            available_variable_ids=VARIABLES,
            language=Language.KO,
        )


def test_wrong_types_unavailable_variables_and_ambiguous_identities_fail_closed() -> None:
    with pytest.raises(P1IntakeError, match="profile"):
        P1IntakeDraft(  # type: ignore[arg-type]
            profile="numeric_distribution",
            roles=P1RoleBindings(outcome=("outcome",)),
        )
    with pytest.raises(P1IntakeError, match="tuple"):
        P1RoleBindings(outcome=["outcome"])  # type: ignore[arg-type]
    with pytest.raises(P1IntakeError, match="duplicate"):
        P1RoleBindings(repeated_measure_order=("before", "before"))
    with pytest.raises(P1IntakeError, match="duplicated"):
        P1RoleBindings(outcome=("y",), focal_predictor=("y",))

    draft = P1IntakeDraft(
        P1TaskProfile.NUMERIC_DISTRIBUTION,
        P1RoleBindings(outcome=("missing",)),
    )
    with pytest.raises(P1IntakeError, match="available"):
        build_p1_request(
            draft,
            task_project_id=TASK_PROJECT_ID,
            initial_event_id=INITIAL_EVENT_ID,
            dataset_fingerprint=DATASET_FINGERPRINT,
            source_schema_fingerprint=SOURCE_SCHEMA_FINGERPRINT,
            available_variable_ids=VARIABLES,
            language=Language.KO,
        )
    with pytest.raises(P1IntakeError, match="available_variable_ids"):
        build_p1_request(
            replace(draft, roles=P1RoleBindings(outcome=("outcome",))),
            task_project_id=TASK_PROJECT_ID,
            initial_event_id=INITIAL_EVENT_ID,
            dataset_fingerprint=DATASET_FINGERPRINT,
            source_schema_fingerprint=SOURCE_SCHEMA_FINGERPRINT,
            available_variable_ids=("outcome", "outcome"),
            language=Language.KO,
        )
    with pytest.raises(P1IntakeError, match="source_schema_fingerprint"):
        build_p1_request(
            replace(draft, roles=P1RoleBindings(outcome=("outcome",))),
            task_project_id=TASK_PROJECT_ID,
            initial_event_id=INITIAL_EVENT_ID,
            dataset_fingerprint=DATASET_FINGERPRINT,
            source_schema_fingerprint="not-a-digest",
            available_variable_ids=VARIABLES,
            language=Language.KO,
        )


def _passport_envelope(request: ResearchRequest, round_number: int) -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id="modori.analysis_passport",
        schema_version=2,
        project_id=request.question.envelope.project_id,
        object_id=f"passport:round:{round_number}",
        revision=1,
        supersedes_revision=None,
        created_event_ref=f"event:passport:{round_number}",
    )


def _answer_selected(
    request: ResearchRequest,
    passport: object,
    value: AnswerValue,
    *,
    sequence: int,
) -> ClarificationAnswerEvent:
    clarify = passport.clarify
    assert clarify is not None
    reference = clarify.clarification_ref
    return ClarificationAnswerEvent(
        event_id=f"answer:{sequence}",
        project_id=request.question.envelope.project_id,
        event_sequence=sequence,
        source_passport_digest=passport.digest(),
        question_id=reference.question_id,
        question_version=reference.question_version,
        question_digest=reference.question_digest,
        fact_address=reference.fact_address,
        answer_value=value,
    )


def _safe_value(fact_address: str) -> AnswerValue:
    if fact_address in {"study.role.cluster", "study.role.weight"}:
        return AnswerValue(kind=AnswerValueKind.VARIABLES, variable_ids=())
    if fact_address == "study.dependence_structure":
        return AnswerValue(
            kind=AnswerValueKind.CHOICE,
            choice_value="independent",
        )
    raise AssertionError(f"unexpected P1 intake blocker: {fact_address}")


EXPECTED_TERMINALS = {
    P1TaskProfile.NUMERIC_DISTRIBUTION: ("unweighted_summary", 3),
    P1TaskProfile.CATEGORY_FREQUENCY: ("unweighted_frequency", 3),
    P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN: ("welch_mean_difference", 2),
    P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE: ("paired_t_mean_change", 2),
    P1TaskProfile.LINEAR_CO_MOVEMENT: ("pearson_product_moment", 3),
    P1TaskProfile.RANK_CO_MOVEMENT: ("spearman_rank_monotonic", 3),
}


P1_LIVE_TERMINAL_PATH_COUNTS = {
    P1TaskProfile.NUMERIC_DISTRIBUTION: 15,
    P1TaskProfile.CATEGORY_FREQUENCY: 15,
    P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN: 7,
    P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE: 7,
    P1TaskProfile.LINEAR_CO_MOVEMENT: 15,
    P1TaskProfile.RANK_CO_MOVEMENT: 15,
}


def _all_p1_live_branch_values(fact_address: str) -> tuple[AnswerValue, ...]:
    not_sure = AnswerValue(kind=AnswerValueKind.NOT_SURE)
    if fact_address in {"study.role.cluster", "study.role.weight"}:
        selected_variable = (
            "cluster" if fact_address == "study.role.cluster" else "weight"
        )
        return (
            not_sure,
            AnswerValue(kind=AnswerValueKind.VARIABLES, variable_ids=()),
            AnswerValue(
                kind=AnswerValueKind.VARIABLES,
                variable_ids=(selected_variable,),
            ),
        )
    if fact_address == "study.dependence_structure":
        return (
            not_sure,
            AnswerValue(
                kind=AnswerValueKind.CHOICE,
                choice_value="independent",
            ),
            AnswerValue(
                kind=AnswerValueKind.CHOICE,
                choice_value="paired",
            ),
        )
    raise AssertionError(f"unexpected P1 live clarification: {fact_address}")


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
def test_all_six_profiles_reach_only_the_intended_terminal_within_budget(
    profile: P1TaskProfile,
) -> None:
    service = ResearchOsService()
    transition = ClarificationTransitionService()
    request = _request(profile)
    selected_addresses: list[str] = []
    expected_variant, expected_rounds = EXPECTED_TERMINALS[profile]

    for round_number in range(1, 5):
        resolved = service.resolve_and_plan(
            request,
            _passport_envelope(request, round_number),
        )
        if resolved.decision.action is PrimaryAction.RECOMMEND_LOCAL:
            assert round_number - 1 == expected_rounds
            assert len(resolved.decision.capability_keys) == 1
            assert expected_variant in resolved.decision.capability_keys[0]
            assert request.question_budget_remaining == 3 - expected_rounds
            break
        assert resolved.decision.action is PrimaryAction.CLARIFY
        clarify = resolved.passport.clarify
        assert clarify is not None
        address = clarify.clarification_ref.fact_address
        selected_addresses.append(address)
        answer = _answer_selected(
            request,
            resolved.passport,
            _safe_value(address),
            sequence=round_number,
        )
        candidate = transition.propose(request, resolved.passport, answer)
        assert candidate.requires_acceptance is False
        request = transition.commit_ready(request, candidate)
    else:
        pytest.fail("profile did not terminate inside the frozen question budget")

    assert selected_addresses == (
        ["study.role.cluster", "study.dependence_structure", "study.role.weight"]
        if expected_rounds == 3
        else ["study.role.cluster", "study.role.weight"]
    )


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
def test_every_p1_live_answer_branch_is_ready_without_estimand_acceptance(
    profile: P1TaskProfile,
) -> None:
    service = ResearchOsService()
    transition = ClarificationTransitionService()
    stack = [(_request(profile), 1)]
    terminal_count = 0

    while stack:
        request, next_sequence = stack.pop()
        resolved = service.resolve_and_plan(
            request,
            _passport_envelope(request, next_sequence),
        )
        if resolved.decision.action is not PrimaryAction.CLARIFY:
            assert resolved.decision.action in {
                PrimaryAction.RECOMMEND_LOCAL,
                PrimaryAction.ABSTAIN,
            }
            terminal_count += 1
            continue

        clarify = resolved.passport.clarify
        assert clarify is not None
        fact_address = clarify.clarification_ref.fact_address
        for branch_number, value in enumerate(
            _all_p1_live_branch_values(fact_address),
            start=1,
        ):
            answer = _answer_selected(
                request,
                resolved.passport,
                value,
                sequence=next_sequence,
            )
            answer = replace(
                answer,
                event_id=(
                    f"answer:{profile.value}:{next_sequence}:{branch_number}:"
                    f"{terminal_count}:{len(stack)}"
                ),
            )
            candidate = transition.propose(request, resolved.passport, answer)
            assert candidate.requires_acceptance is False
            stack.append(
                (
                    transition.commit_ready(request, candidate),
                    next_sequence + 1,
                )
            )

    assert terminal_count == P1_LIVE_TERMINAL_PATH_COUNTS[profile]


def test_explicit_none_transition_is_not_the_same_as_an_omitted_study_role() -> None:
    request = _request(P1TaskProfile.NUMERIC_DISTRIBUTION)
    assert request.study.design_roles == ()
    resolved = ResearchOsService().resolve_and_plan(
        request,
        _passport_envelope(request, 1),
    )
    assert resolved.passport.clarify is not None
    assert (
        resolved.passport.clarify.clarification_ref.fact_address
        == "study.role.cluster"
    )

    answer = _answer_selected(
        request,
        resolved.passport,
        AnswerValue(kind=AnswerValueKind.VARIABLES, variable_ids=()),
        sequence=1,
    )
    transition = ClarificationTransitionService()
    committed = transition.commit_ready(
        request,
        transition.propose(request, resolved.passport, answer),
    )
    cluster = next(
        binding
        for binding in committed.study.design_roles
        if binding.role is StudyRole.CLUSTER
    )
    assert cluster.variable_ids.state is FactState.USER_CONFIRMED
    assert cluster.variable_ids.value == ()
    assert cluster.variable_ids.provenance_refs == (answer.event_id,)


@pytest.mark.parametrize(
    "unsafe_value",
    (
        AnswerValue(kind=AnswerValueKind.NOT_SURE),
        AnswerValue(kind=AnswerValueKind.VARIABLES, variable_ids=("cluster",)),
    ),
)
def test_not_sure_and_nonempty_cluster_never_substitute_independence(
    unsafe_value: AnswerValue,
) -> None:
    request = _request(P1TaskProfile.NUMERIC_DISTRIBUTION)
    service = ResearchOsService()
    transition = ClarificationTransitionService()
    resolved = service.resolve_and_plan(request, _passport_envelope(request, 1))
    answer = _answer_selected(
        request,
        resolved.passport,
        unsafe_value,
        sequence=1,
    )
    committed = transition.commit_ready(
        request,
        transition.propose(request, resolved.passport, answer),
    )

    decision = service.resolve(committed)
    assert decision.action is not PrimaryAction.RECOMMEND_LOCAL
    assert all("unweighted_summary" not in key for key in decision.capability_keys)


def test_nonempty_weight_never_substitutes_an_unweighted_capability() -> None:
    request = _request(P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN)
    service = ResearchOsService()
    transition = ClarificationTransitionService()
    first = service.resolve_and_plan(request, _passport_envelope(request, 1))
    request = transition.commit_ready(
        request,
        transition.propose(
            request,
            first.passport,
            _answer_selected(
                request,
                first.passport,
                AnswerValue(kind=AnswerValueKind.VARIABLES, variable_ids=()),
                sequence=1,
            ),
        ),
    )
    second = service.resolve_and_plan(request, _passport_envelope(request, 2))
    assert second.passport.clarify is not None
    assert second.passport.clarify.clarification_ref.fact_address == "study.role.weight"
    request = transition.commit_ready(
        request,
        transition.propose(
            request,
            second.passport,
            _answer_selected(
                request,
                second.passport,
                AnswerValue(
                    kind=AnswerValueKind.VARIABLES,
                    variable_ids=("weight",),
                ),
                sequence=2,
            ),
        ),
    )

    decision = service.resolve(request)
    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.capability_keys == ()


def test_causal_abstention_builder_is_minimal_separate_and_exact() -> None:
    request = build_causal_abstention_request(
        task_project_id=TASK_PROJECT_ID,
        initial_event_id=INITIAL_EVENT_ID,
        dataset_fingerprint=DATASET_FINGERPRINT,
        source_schema_fingerprint=SOURCE_SCHEMA_FINGERPRINT,
        available_variable_ids=VARIABLES,
        language=Language.EN,
    )

    assert request.question.language is Language.EN
    assert request.question.causal_intent.state is FactState.USER_CONFIRMED
    assert request.question.causal_intent.value is CausalIntent.CAUSAL
    assert request.question.research_goal.state is FactState.UNKNOWN
    assert request.estimand.target_roles == ()
    assert request.study.design_roles == ()
    assert request.question_budget_remaining == 3
    declared = (
        request.estimand.template,
        request.estimand.claim_basis,
        request.estimand.contrast,
        request.estimand.effect_scale,
        request.estimand.association_target,
        request.study.dependence_structure,
        request.study.repeated_measure_order,
    )
    assert all(fact.state is FactState.UNKNOWN for fact in declared)

    decision = ResearchOsService().resolve(request)
    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.reason_codes == ("unsupported_causal_target",)
    assert decision.capability_keys == ()


def _advance_safe(request: ResearchRequest, rounds: int) -> ResearchRequest:
    service = ResearchOsService()
    transition = ClarificationTransitionService()
    for round_number in range(1, rounds + 1):
        resolved = service.resolve_and_plan(
            request,
            _passport_envelope(request, round_number),
        )
        assert resolved.passport.clarify is not None
        address = resolved.passport.clarify.clarification_ref.fact_address
        answer = _answer_selected(
            request,
            resolved.passport,
            _safe_value(address),
            sequence=round_number,
        )
        request = transition.commit_ready(
            request,
            transition.propose(request, resolved.passport, answer),
        )
    return request


def test_declared_fact_budget_and_empty_role_authority_mutations_change_result() -> None:
    base = _advance_safe(_request(P1TaskProfile.NUMERIC_DISTRIBUTION), 3)
    service = ResearchOsService()
    assert service.resolve(base).action is PrimaryAction.RECOMMEND_LOCAL

    changed_goal = replace(
        base,
        question=replace(
            base.question,
            research_goal=Fact.user_confirmed(
                ResearchGoal.ASSOCIATE,
                provenance_refs=("mutation:goal",),
            ),
        ),
    )
    exhausted = replace(
        _request(P1TaskProfile.NUMERIC_DISTRIBUTION),
        question_budget_remaining=0,
    )
    by_role = {binding.role: binding for binding in base.study.design_roles}
    by_role[StudyRole.WEIGHT] = StudyRoleBinding(
        role=StudyRole.WEIGHT,
        variable_ids=Fact.inferred((), provenance_refs=("mutation:empty-weight",)),
    )
    downgraded_empty = replace(
        base,
        study=replace(
            base.study,
            design_roles=tuple(
                by_role[key] for key in sorted(by_role, key=lambda item: item.value)
            ),
        ),
    )

    for mutated in (changed_goal, exhausted, downgraded_empty):
        decision = service.resolve(mutated)
        assert decision.action is not PrimaryAction.RECOMMEND_LOCAL
        assert all("unweighted_summary" not in key for key in decision.capability_keys)


def test_swapping_before_after_invalidates_the_paired_capability() -> None:
    ready = _advance_safe(_request(P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE), 2)
    service = ResearchOsService()
    assert service.resolve(ready).action is PrimaryAction.RECOMMEND_LOCAL
    swapped = replace(
        ready,
        study=replace(
            ready.study,
            repeated_measure_order=Fact.user_confirmed(
                ("after", "before"),
                provenance_refs=("mutation:order",),
            ),
        ),
    )

    decision = service.resolve(swapped)
    assert decision.action is not PrimaryAction.RECOMMEND_LOCAL
    assert all("paired_t_mean_change" not in key for key in decision.capability_keys)


@pytest.mark.parametrize(
    "field",
    ("method_space_digest", "clarification_registry_digest"),
)
def test_passport_catalog_identity_mutation_is_rejected_before_transition(
    field: str,
) -> None:
    request = _request(P1TaskProfile.NUMERIC_DISTRIBUTION)
    resolved = ResearchOsService().resolve_and_plan(
        request,
        _passport_envelope(request, 1),
    )
    tampered = replace(resolved.passport, **{field: "0" * 64})
    answer = _answer_selected(
        request,
        tampered,
        AnswerValue(kind=AnswerValueKind.VARIABLES, variable_ids=()),
        sequence=1,
    )

    with pytest.raises(TransitionError, match="method|registry|stale"):
        ClarificationTransitionService().propose(request, tampered, answer)
