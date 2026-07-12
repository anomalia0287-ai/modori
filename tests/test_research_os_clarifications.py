from __future__ import annotations

from dataclasses import replace

import pytest

import modori.research_os as research_os
from modori.research_os.clarification import (
    AnswerChoice,
    AnswerKind,
    BranchMatchKind,
    ClarificationBranch,
    ClarificationError,
    ClarificationLifecycle,
    ClarificationRegistry,
    ClarificationSpec,
    ClarificationTrigger,
)
from modori.research_os.p1_catalog import build_p1_method_space
from modori.research_os.p1_clarifications import build_p1_clarification_registry


def _choice(value: str) -> AnswerChoice:
    return AnswerChoice(
        value=value,
        label_ko=f"한국어 {value}",
        label_en=f"English {value}",
    )


def _branch(value: str) -> ClarificationBranch:
    return ClarificationBranch(
        branch_id=f"choice_{value}",
        match_kind=BranchMatchKind.CHOICE_VALUES,
        choice_values=(value,),
        effects=(ClarificationTrigger.METHOD_IDENTITY_CHANGE,),
    )


def _not_sure_branch() -> ClarificationBranch:
    return ClarificationBranch(
        branch_id="not_sure",
        match_kind=BranchMatchKind.NOT_SURE,
        choice_values=(),
        effects=(ClarificationTrigger.METHOD_IDENTITY_CHANGE,),
    )


def _choice_question() -> ClarificationSpec:
    return ClarificationSpec(
        question_id="confirm_dependence",
        version=1,
        fact_address="study.dependence_structure",
        answer_kind=AnswerKind.SINGLE_CHOICE,
        template_ko="관측값들이 서로 독립입니까?",
        template_en="Are the observations independent?",
        why_ko="자료 사이의 의존성이 허용되는 결론을 바꿉니다.",
        why_en="Dependence changes which conclusions are supported.",
        choices=(_choice("independent"), _choice("paired")),
        triggers=(ClarificationTrigger.METHOD_IDENTITY_CHANGE,),
        not_sure_enabled=True,
        dependencies=("estimand.template",),
        branches=(
            _branch("independent"),
            _branch("paired"),
            _not_sure_branch(),
        ),
        lifecycle=ClarificationLifecycle.ACTIVE,
    )


def test_choice_question_requires_two_distinct_answers_and_not_sure() -> None:
    with pytest.raises(ClarificationError, match="at least two choices"):
        replace(_choice_question(), choices=(_choice("independent"),))

    with pytest.raises(ClarificationError, match="duplicate choice value"):
        replace(
            _choice_question(),
            choices=(_choice("independent"), _choice("independent")),
        )

    with pytest.raises(ClarificationError, match="not_sure_enabled must be true"):
        replace(_choice_question(), not_sure_enabled=False)


@pytest.mark.parametrize(
    "answer_kind",
    [
        AnswerKind.VARIABLE_SINGLE,
        AnswerKind.VARIABLE_MULTI,
        AnswerKind.ORDERED_VARIABLES,
        AnswerKind.BOUNDED_TEXT,
    ],
)
def test_open_answer_kinds_reject_hard_coded_choices(answer_kind: AnswerKind) -> None:
    with pytest.raises(ClarificationError, match="cannot define hard-coded choices"):
        replace(_choice_question(), answer_kind=answer_kind)


def test_clarification_requires_closed_typed_triggers() -> None:
    with pytest.raises(ClarificationError, match="at least one trigger"):
        replace(_choice_question(), triggers=())

    with pytest.raises(ClarificationError, match="duplicate trigger"):
        replace(
            _choice_question(),
            triggers=(
                ClarificationTrigger.METHOD_IDENTITY_CHANGE,
                ClarificationTrigger.METHOD_IDENTITY_CHANGE,
            ),
        )

    with pytest.raises(ClarificationError, match="ClarificationTrigger"):
        replace(_choice_question(), triggers=("method_identity_change",))  # type: ignore[arg-type]


def test_active_choice_question_covers_every_choice_and_not_sure() -> None:
    question = _choice_question()

    with pytest.raises(ClarificationError, match="uncovered choice"):
        replace(
            question,
            branches=(question.branches[0], question.branches[-1]),
        )
    with pytest.raises(ClarificationError, match="not_sure branch"):
        replace(question, branches=question.branches[:-1])


def test_variable_multi_question_requires_empty_nonempty_and_not_sure_branches() -> None:
    branches = (
        ClarificationBranch(
            branch_id="empty",
            match_kind=BranchMatchKind.EMPTY_VARIABLES,
            choice_values=(),
            effects=(ClarificationTrigger.DATA_POLICY_CHANGE,),
        ),
        ClarificationBranch(
            branch_id="nonempty",
            match_kind=BranchMatchKind.NONEMPTY_VARIABLES,
            choice_values=(),
            effects=(ClarificationTrigger.DATA_POLICY_CHANGE,),
        ),
        ClarificationBranch(
            branch_id="not_sure",
            match_kind=BranchMatchKind.NOT_SURE,
            choice_values=(),
            effects=(ClarificationTrigger.DATA_POLICY_CHANGE,),
        ),
    )
    question = replace(
        _choice_question(),
        answer_kind=AnswerKind.VARIABLE_MULTI,
        choices=(),
        triggers=(ClarificationTrigger.DATA_POLICY_CHANGE,),
        branches=branches,
    )

    with pytest.raises(ClarificationError, match="empty_variables branch"):
        replace(question, branches=branches[1:])
    with pytest.raises(ClarificationError, match="nonempty_variables branch"):
        replace(question, branches=(branches[0], branches[2]))
    with pytest.raises(ClarificationError, match="exactly one empty_variables"):
        replace(
            question,
            branches=(branches[0], replace(branches[0], branch_id="empty_again"))
            + branches[1:],
        )


def test_dependencies_are_closed_unique_fact_addresses() -> None:
    with pytest.raises(ClarificationError, match="duplicate dependency"):
        replace(
            _choice_question(),
            dependencies=("estimand.template", "estimand.template"),
        )
    with pytest.raises(ClarificationError, match="dotted lowercase address"):
        replace(_choice_question(), dependencies=("not dotted",))


def test_branch_rejects_choice_values_for_nonchoice_match() -> None:
    with pytest.raises(ClarificationError, match="cannot carry choice_values"):
        ClarificationBranch(
            branch_id="not_sure",
            match_kind=BranchMatchKind.NOT_SURE,
            choice_values=("paired",),
            effects=(ClarificationTrigger.METHOD_IDENTITY_CHANGE,),
        )


@pytest.mark.parametrize(
    "method_name",
    ["Pearson", "Spearman", "Welch", "t-test", "t 검정", "ANOVA"],
)
def test_question_text_cannot_name_a_statistical_method(method_name: str) -> None:
    with pytest.raises(ClarificationError, match="statistical method name"):
        replace(
            _choice_question(),
            template_en=f"Should Modori use {method_name}?",
        )


def test_clarification_strict_roundtrip_preserves_digest() -> None:
    question = _choice_question()

    restored = ClarificationSpec.from_mapping(question.to_mapping())

    assert restored == question
    assert restored.digest() == question.digest()

    with pytest.raises(ClarificationError, match="unknown field.*method"):
        ClarificationSpec.from_mapping(question.to_mapping() | {"method": "hidden"})


def test_p1_registry_exactly_covers_method_space_question_ids() -> None:
    required = {
        rule.clarification_id
        for rule in build_p1_method_space().rules
        if rule.clarification_id is not None
    }
    registry = build_p1_clarification_registry()

    assert set(registry.question_ids) == required
    assert registry.required_question_ids == tuple(sorted(required))


def test_registry_rejects_missing_extra_and_duplicate_questions() -> None:
    registry = build_p1_clarification_registry()

    with pytest.raises(ClarificationError, match="missing question"):
        ClarificationRegistry(
            questions=registry.questions[:-1],
            required_question_ids=registry.required_question_ids,
        )
    with pytest.raises(ClarificationError, match="unused question"):
        ClarificationRegistry(
            questions=registry.questions + (replace(registry.questions[0], question_id="unused"),),
            required_question_ids=registry.required_question_ids,
        )
    with pytest.raises(ClarificationError, match="duplicate question_id"):
        ClarificationRegistry(
            questions=registry.questions + (registry.questions[0],),
            required_question_ids=registry.required_question_ids,
        )


def test_registry_lookup_and_roundtrip_are_stable() -> None:
    registry = build_p1_clarification_registry()

    restored = ClarificationRegistry.from_mapping(registry.to_mapping())

    assert restored == registry
    assert restored.digest() == registry.digest()
    assert restored.get("confirm_dependence").fact_address == "study.dependence_structure"
    with pytest.raises(ClarificationError, match="unknown clarification question"):
        restored.get("not_registered")


def test_p1_questions_are_bilingual_neutral_and_always_offer_not_sure() -> None:
    registry = build_p1_clarification_registry()
    forbidden = ("pearson", "spearman", "welch", "t-test", "t 검정", "anova")

    for question in registry.questions:
        text = " ".join(
            (
                question.template_ko,
                question.template_en,
                question.why_ko,
                question.why_en,
            )
        ).casefold()
        assert question.not_sure_enabled is True
        assert question.lifecycle is ClarificationLifecycle.ACTIVE
        assert any(
            branch.match_kind is BranchMatchKind.NOT_SURE
            for branch in question.branches
        )
        assert question.template_ko.strip()
        assert question.template_en.strip()
        assert not any(token in text for token in forbidden)


def test_p1_registry_is_exposed_from_package() -> None:
    assert research_os.ClarificationSpec is ClarificationSpec
    assert research_os.ClarificationBranch is ClarificationBranch
    assert research_os.ClarificationLifecycle is ClarificationLifecycle
    assert research_os.build_p1_clarification_registry is build_p1_clarification_registry
