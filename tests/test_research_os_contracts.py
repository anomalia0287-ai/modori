from __future__ import annotations

import pytest

import modori.research_os as research_os
from modori.research_os.contracts import (
    AssignmentMechanism,
    AssociationTarget,
    CaptureMode,
    CausalIntent,
    ClaimBasis,
    ContractError,
    DataLayout,
    DependenceKind,
    DesignFamily,
    EffectScale,
    EstimandSpec,
    EstimandTemplate,
    Fact,
    FactState,
    Language,
    MissingCodeMeaning,
    QuestionSpec,
    ResearchGoal,
    RoleHint,
    RoleHintBinding,
    SamplingDesign,
    SchemaEnvelope,
    StaleSnapshot,
    StudyRole,
    StudyRoleBinding,
    StudySpec,
    TargetRole,
    TargetRoleBinding,
    TemporalStructure,
    UnitKind,
)


def test_observed_fact_requires_value_and_provenance() -> None:
    with pytest.raises(ContractError, match="observed fact requires one value"):
        Fact(state=FactState.OBSERVED)

    with pytest.raises(ContractError, match="observed fact requires provenance"):
        Fact(state=FactState.OBSERVED, value="person")


def test_current_fact_accepts_exactly_one_value_with_provenance() -> None:
    fact = Fact.observed("person", provenance_refs=("profile:unit-v1",))

    assert fact.state is FactState.OBSERVED
    assert fact.value == "person"
    assert fact.alternatives == ()


def test_unknown_fact_rejects_value_alternatives_and_provenance() -> None:
    with pytest.raises(ContractError, match="unknown fact cannot carry"):
        Fact(
            state=FactState.UNKNOWN,
            value="person",
            provenance_refs=("answer:1",),
        )


def test_conflict_requires_distinct_alternatives_and_provenance() -> None:
    with pytest.raises(ContractError, match="at least two distinct alternatives"):
        Fact(
            state=FactState.CONFLICT,
            alternatives=("paired", "paired"),
            provenance_refs=("answer:1", "metadata:1"),
        )

    fact = Fact.conflict(
        ("paired", "independent"),
        provenance_refs=("answer:1", "metadata:1"),
        reason_code="incompatible_dependence_evidence",
    )
    assert fact.value is None
    assert fact.alternatives == ("paired", "independent")


def test_not_applicable_requires_a_reason_and_no_active_value() -> None:
    with pytest.raises(ContractError, match="not_applicable fact requires reason_code"):
        Fact(state=FactState.NOT_APPLICABLE)

    fact = Fact.not_applicable(reason_code="not_an_association_target")
    assert fact.state is FactState.NOT_APPLICABLE
    assert fact.value is None


def test_stale_fact_retains_only_an_inactive_snapshot() -> None:
    snapshot = StaleSnapshot(
        value="paired",
        provenance_refs=("answer:1",),
        invalidation_reason="dataset_replaced",
    )
    fact = Fact.stale(snapshot, reason_code="dataset_fingerprint_changed")

    assert fact.state is FactState.STALE
    assert fact.value is None
    assert fact.stale_snapshot == snapshot

    with pytest.raises(ContractError, match="stale fact requires stale_snapshot"):
        Fact(state=FactState.STALE, reason_code="dataset_changed")


def test_blank_provenance_identifier_is_rejected() -> None:
    with pytest.raises(ContractError, match="provenance reference"):
        Fact.observed("person", provenance_refs=("  ",))


def test_schema_envelope_requires_monotonic_revisions() -> None:
    with pytest.raises(ContractError, match="supersedes_revision"):
        SchemaEnvelope(
            schema_id="modori.study_spec",
            schema_version=1,
            project_id="project-1",
            object_id="study-1",
            revision=2,
            supersedes_revision=2,
            created_event_ref="event:2",
        )


def test_schema_envelope_rejects_blank_identifiers() -> None:
    with pytest.raises(ContractError, match="project_id"):
        SchemaEnvelope(
            schema_id="modori.study_spec",
            schema_version=1,
            project_id="",
            object_id="study-1",
            revision=1,
            supersedes_revision=None,
            created_event_ref="event:1",
        )


def _envelope(schema_id: str, object_id: str) -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id=schema_id,
        schema_version=1,
        project_id="project-1",
        object_id=object_id,
        revision=1,
        supersedes_revision=None,
        created_event_ref=f"event:{object_id}:1",
    )


def _confirmed(value: object) -> Fact[object]:
    return Fact.user_confirmed(value, provenance_refs=("answer:1",))


def _question_spec() -> QuestionSpec:
    return QuestionSpec(
        envelope=_envelope("modori.question_spec", "question-1"),
        capture_mode=CaptureMode.STRUCTURED,
        language=Language.KO,
        local_text=None,
        research_goal=Fact.user_confirmed(
            ResearchGoal.ASSOCIATE,
            provenance_refs=("answer:goal",),
        ),
        causal_intent=Fact.user_confirmed(
            CausalIntent.NONCAUSAL,
            provenance_refs=("answer:causal",),
        ),
        role_hints=(
            RoleHintBinding(concept_id="stress", role=RoleHint.OUTCOME),
            RoleHintBinding(concept_id="sleep", role=RoleHint.PREDICTOR),
        ),
    )


def _estimand_spec(
    association_target: AssociationTarget = AssociationTarget.PRODUCT_MOMENT,
) -> EstimandSpec:
    return EstimandSpec(
        envelope=_envelope("modori.estimand_spec", "estimand-1"),
        template=Fact.user_confirmed(
            EstimandTemplate.ASSOCIATION,
            provenance_refs=("answer:template",),
        ),
        claim_basis=Fact.user_confirmed(
            ClaimBasis.ASSOCIATIONAL,
            provenance_refs=("answer:claim",),
        ),
        target_population=Fact.user_confirmed(
            "조사 대상 대학생",
            provenance_refs=("answer:population",),
        ),
        unit_of_analysis=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:unit",),
        ),
        target_roles=(
            TargetRoleBinding(
                role=TargetRole.OUTCOME,
                variable_ids=Fact.user_confirmed(
                    ("stress",),
                    provenance_refs=("answer:outcome",),
                ),
            ),
            TargetRoleBinding(
                role=TargetRole.FOCAL_PREDICTOR,
                variable_ids=Fact.user_confirmed(
                    ("sleep",),
                    provenance_refs=("answer:predictor",),
                ),
            ),
        ),
        contrast=Fact.not_applicable(reason_code="association_has_no_contrast"),
        time_scope=Fact.user_confirmed(
            "single_wave",
            provenance_refs=("answer:time",),
        ),
        effect_scale=Fact.user_confirmed(
            EffectScale.CORRELATION,
            provenance_refs=("answer:scale",),
        ),
        association_target=Fact.user_confirmed(
            association_target,
            provenance_refs=("answer:association-target",),
        ),
    )


def _study_spec() -> StudySpec:
    return StudySpec(
        envelope=_envelope("modori.study_spec", "study-1"),
        dataset_fingerprint="a" * 64,
        source_schema_fingerprint="b" * 64,
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
            DataLayout.UNIT_ROWS,
            provenance_refs=("profile:layout",),
        ),
        temporal_structure=Fact.user_confirmed(
            TemporalStructure.SINGLE_WAVE,
            provenance_refs=("answer:temporal",),
        ),
        dependence_structure=Fact.user_confirmed(
            DependenceKind.INDEPENDENT,
            provenance_refs=("answer:dependence",),
        ),
        assignment_mechanism=Fact.user_confirmed(
            AssignmentMechanism.NONRANDOMIZED,
            provenance_refs=("answer:assignment",),
        ),
        sampling_design=Fact.user_confirmed(
            SamplingDesign.CONVENIENCE,
            provenance_refs=("answer:sampling",),
        ),
        design_roles=(
            StudyRoleBinding(
                role=StudyRole.WEIGHT,
                variable_ids=Fact.user_confirmed(
                    (),
                    provenance_refs=("answer:no-weight",),
                ),
            ),
            StudyRoleBinding(
                role=StudyRole.CLUSTER,
                variable_ids=Fact.user_confirmed(
                    (),
                    provenance_refs=("answer:no-cluster",),
                ),
            ),
        ),
        repeated_measure_order=Fact.not_applicable(
            reason_code="single_wave_has_no_repeated_order"
        ),
        missing_code_meanings=(
            MissingCodeMeaning(
                variable_id="stress",
                code="999",
                meaning="user_missing",
            ),
        ),
    )


def test_question_spec_strict_roundtrip_preserves_digest() -> None:
    spec = _question_spec()

    restored = QuestionSpec.from_mapping(spec.to_mapping())

    assert restored == spec
    assert restored.digest() == spec.digest()


def test_question_spec_rejects_method_as_unknown_wire_key() -> None:
    payload = _question_spec().to_mapping() | {"method": "anova"}

    with pytest.raises(ContractError, match="unknown field.*method"):
        QuestionSpec.from_mapping(payload)


def test_estimand_spec_distinguishes_product_moment_and_rank_monotonic_targets() -> None:
    pearson = _estimand_spec(AssociationTarget.PRODUCT_MOMENT)
    spearman = _estimand_spec(AssociationTarget.RANK_MONOTONIC)

    assert pearson.digest() != spearman.digest()
    assert EstimandSpec.from_mapping(pearson.to_mapping()) == pearson
    assert EstimandSpec.from_mapping(spearman.to_mapping()) == spearman


def test_nonassociation_estimand_rejects_active_association_target() -> None:
    source = _estimand_spec()

    with pytest.raises(ContractError, match="association_target"):
        EstimandSpec(
            envelope=source.envelope,
            template=Fact.user_confirmed(
                EstimandTemplate.SUMMARY,
                provenance_refs=("answer:template",),
            ),
            claim_basis=Fact.user_confirmed(
                ClaimBasis.DESCRIPTIVE,
                provenance_refs=("answer:claim",),
            ),
            target_population=source.target_population,
            unit_of_analysis=source.unit_of_analysis,
            target_roles=source.target_roles,
            contrast=source.contrast,
            time_scope=source.time_scope,
            effect_scale=Fact.user_confirmed(
                EffectScale.MEAN,
                provenance_refs=("answer:scale",),
            ),
            association_target=source.association_target,
        )


def test_estimand_spec_rejects_duplicate_target_roles() -> None:
    source = _estimand_spec()

    with pytest.raises(ContractError, match="duplicate target role"):
        EstimandSpec(
            envelope=source.envelope,
            template=source.template,
            claim_basis=source.claim_basis,
            target_population=source.target_population,
            unit_of_analysis=source.unit_of_analysis,
            target_roles=(source.target_roles[0], source.target_roles[0]),
            contrast=source.contrast,
            time_scope=source.time_scope,
            effect_scale=source.effect_scale,
            association_target=source.association_target,
        )


def test_study_spec_digest_is_independent_of_mapping_key_order() -> None:
    payload = _study_spec().to_mapping()
    reordered = dict(reversed(tuple(payload.items())))

    assert StudySpec.from_mapping(payload).digest() == StudySpec.from_mapping(
        reordered
    ).digest()


def test_study_spec_rejects_unknown_wire_key() -> None:
    payload = _study_spec().to_mapping() | {"analysis_family": "correlation"}

    with pytest.raises(ContractError, match="unknown field.*analysis_family"):
        StudySpec.from_mapping(payload)


def test_study_spec_rejects_noncanonical_fingerprint() -> None:
    source = _study_spec()

    with pytest.raises(ContractError, match="dataset_fingerprint"):
        StudySpec(
            envelope=source.envelope,
            dataset_fingerprint="SHA256:not-canonical",
            source_schema_fingerprint=source.source_schema_fingerprint,
            unit_of_observation=source.unit_of_observation,
            unit_of_analysis=source.unit_of_analysis,
            design_family=source.design_family,
            data_layout=source.data_layout,
            temporal_structure=source.temporal_structure,
            dependence_structure=source.dependence_structure,
            assignment_mechanism=source.assignment_mechanism,
            sampling_design=source.sampling_design,
            design_roles=source.design_roles,
            repeated_measure_order=source.repeated_measure_order,
            missing_code_meanings=source.missing_code_meanings,
        )


def test_independent_study_rejects_confirmed_pair_identifier() -> None:
    source = _study_spec()

    with pytest.raises(ContractError, match="independent study cannot bind pair_id"):
        StudySpec(
            envelope=source.envelope,
            dataset_fingerprint=source.dataset_fingerprint,
            source_schema_fingerprint=source.source_schema_fingerprint,
            unit_of_observation=source.unit_of_observation,
            unit_of_analysis=source.unit_of_analysis,
            design_family=source.design_family,
            data_layout=source.data_layout,
            temporal_structure=source.temporal_structure,
            dependence_structure=source.dependence_structure,
            assignment_mechanism=source.assignment_mechanism,
            sampling_design=source.sampling_design,
            design_roles=(
                StudyRoleBinding(
                    role=StudyRole.PAIR_ID,
                    variable_ids=Fact.user_confirmed(
                        ("participant_id",),
                        provenance_refs=("answer:pair",),
                    ),
                ),
            ),
            repeated_measure_order=source.repeated_measure_order,
            missing_code_meanings=source.missing_code_meanings,
        )


def test_study_spec_validates_all_bound_variable_ids() -> None:
    spec = _study_spec()

    with pytest.raises(ContractError, match="unknown variable.*stress"):
        spec.validate_variable_references({"sleep"})

    spec.validate_variable_references({"stress", "sleep"})


def test_contracts_are_exposed_from_research_os_package() -> None:
    assert research_os.QuestionSpec is QuestionSpec
    assert research_os.EstimandSpec is EstimandSpec
    assert research_os.StudySpec is StudySpec
    assert research_os.AssociationTarget is AssociationTarget
