from __future__ import annotations

from modori.research_os.clarification import (
    AnswerChoice,
    AnswerKind,
    BranchMatchKind,
    ClarificationBranch,
    ClarificationLifecycle,
    ClarificationRegistry,
    ClarificationSpec,
    ClarificationTrigger,
)
from modori.research_os.p1_catalog import build_p1_method_space


def _choice(value: str, label_ko: str, label_en: str) -> AnswerChoice:
    return AnswerChoice(value=value, label_ko=label_ko, label_en=label_en)


def _question(
    question_id: str,
    fact_address: str,
    answer_kind: AnswerKind,
    template_ko: str,
    template_en: str,
    why_ko: str,
    why_en: str,
    *,
    choices: tuple[AnswerChoice, ...] = (),
    triggers: tuple[ClarificationTrigger, ...],
    dependencies: tuple[str, ...] = (),
) -> ClarificationSpec:
    if choices:
        branches = tuple(
            ClarificationBranch(
                branch_id=f"choice_{choice.value}",
                match_kind=BranchMatchKind.CHOICE_VALUES,
                choice_values=(choice.value,),
                effects=triggers,
            )
            for choice in choices
        )
    elif answer_kind is AnswerKind.VARIABLE_MULTI:
        branches = (
            ClarificationBranch(
                branch_id="empty_variables",
                match_kind=BranchMatchKind.EMPTY_VARIABLES,
                choice_values=(),
                effects=triggers,
            ),
            ClarificationBranch(
                branch_id="nonempty_variables",
                match_kind=BranchMatchKind.NONEMPTY_VARIABLES,
                choice_values=(),
                effects=triggers,
            ),
        )
    else:
        branches = (
            ClarificationBranch(
                branch_id="answered",
                match_kind=BranchMatchKind.ANSWERED,
                choice_values=(),
                effects=triggers,
            ),
        )
    branches += (
        ClarificationBranch(
            branch_id="not_sure",
            match_kind=BranchMatchKind.NOT_SURE,
            choice_values=(),
            effects=triggers,
        ),
    )
    return ClarificationSpec(
        question_id=question_id,
        version=1,
        fact_address=fact_address,
        answer_kind=answer_kind,
        template_ko=template_ko,
        template_en=template_en,
        why_ko=why_ko,
        why_en=why_en,
        choices=choices,
        triggers=triggers,
        not_sure_enabled=True,
        dependencies=dependencies,
        branches=branches,
        lifecycle=ClarificationLifecycle.ACTIVE,
    )


def _questions() -> tuple[ClarificationSpec, ...]:
    action_estimand = (
        ClarificationTrigger.ACTION_CHANGE,
        ClarificationTrigger.ESTIMAND_CHANGE,
    )
    method_estimand = (
        ClarificationTrigger.METHOD_IDENTITY_CHANGE,
        ClarificationTrigger.ESTIMAND_CHANGE,
    )
    return (
        _question(
            "confirm_association_target",
            "estimand.association_target",
            AnswerKind.SINGLE_CHOICE,
            "두 수치가 함께 변하는 양상을 어떤 의미로 요약하려 합니까?",
            "What aspect of how two numeric variables move together should be summarized?",
            "값의 간격을 사용할지 순서만 사용할지가 결과의 의미를 바꿉니다.",
            "Using numeric spacing or ranks changes the meaning of the result.",
            choices=(
                _choice(
                    "product_moment",
                    "값의 간격을 유지한 직선적 함께 변함",
                    "Linear co-movement while preserving numeric spacing",
                ),
                _choice(
                    "rank_monotonic",
                    "순서를 기준으로 한 방향의 함께 변함",
                    "One-direction co-movement based on ranks",
                ),
                _choice(
                    "not_applicable",
                    "변수 간 관계를 다루지 않음",
                    "No relationship between variables is being studied",
                ),
            ),
            triggers=method_estimand,
            dependencies=("estimand.template",),
        ),
        _question(
            "confirm_causal_intent",
            "question.causal_intent",
            AnswerKind.YES_NO,
            "관찰된 차이나 관계를 원인에 따른 효과로 해석하려 합니까?",
            "Will the observed difference or relationship be interpreted as an effect of a cause?",
            "인과적 해석은 연구설계에 대한 별도 증거가 필요합니다.",
            "A causal interpretation requires separate design evidence.",
            choices=(
                _choice("causal", "예, 원인에 따른 효과", "Yes, an effect of a cause"),
                _choice(
                    "noncausal",
                    "아니요, 기술·차이·관계만",
                    "No, description, difference, or relationship only",
                ),
            ),
            triggers=(
                ClarificationTrigger.ACTION_CHANGE,
                ClarificationTrigger.CLAIM_BOUNDARY_CHANGE,
            ),
            dependencies=("question.research_goal",),
        ),
        _question(
            "confirm_claim_basis",
            "estimand.claim_basis",
            AnswerKind.SINGLE_CHOICE,
            "결과로 어떤 종류의 주장을 하려 합니까?",
            "What kind of claim should the result support?",
            "같은 수치라도 허용되는 주장의 범위는 연구목적에 따라 달라집니다.",
            "The allowed claim boundary depends on the research purpose.",
            choices=(
                _choice("descriptive", "표본의 상태를 기술", "Describe the sample"),
                _choice(
                    "associational",
                    "집단 차이 또는 변수 관계를 기술",
                    "Describe a group difference or variable relationship",
                ),
                _choice("causal", "원인에 따른 효과를 주장", "Claim an effect of a cause"),
            ),
            triggers=(
                ClarificationTrigger.ACTION_CHANGE,
                ClarificationTrigger.CLAIM_BOUNDARY_CHANGE,
            ),
            dependencies=(
                "question.research_goal",
                "question.causal_intent",
                "estimand.template",
            ),
        ),
        _question(
            "confirm_cluster_use",
            "study.role.cluster",
            AnswerKind.VARIABLE_MULTI,
            "같은 학교·기관·학급처럼 서로 묶인 관측을 식별하는 변수가 있습니까? 있다면 모두 선택하십시오.",
            "Do any variables identify observations grouped in the same school, organization, or class? Select all that apply.",
            "묶음 안의 관측은 서로 독립적이지 않을 수 있어 지원 경계가 달라집니다.",
            "Observations within a group may not be independent, changing the support boundary.",
            triggers=(
                ClarificationTrigger.ACTION_CHANGE,
                ClarificationTrigger.DESIGN_CHANGE,
                ClarificationTrigger.DATA_POLICY_CHANGE,
            ),
            dependencies=(
                "study.design_family",
                "study.sampling_design",
            ),
        ),
        _question(
            "confirm_contrast",
            "estimand.contrast",
            AnswerKind.SINGLE_CHOICE,
            "어떤 비교를 연구 질문의 핵심으로 삼습니까?",
            "Which comparison is central to the research question?",
            "비교의 형태가 목표 수량과 지원 범위를 결정합니다.",
            "The comparison form determines the target quantity and support boundary.",
            choices=(
                _choice("pairwise", "두 조건을 직접 비교", "Directly compare two conditions"),
                _choice("omnibus", "세 조건 이상을 전체 비교", "Compare three or more conditions jointly"),
                _choice("trend", "순서에 따른 추세를 비교", "Compare an ordered trend"),
                _choice("reference_level", "기준 조건과 각각 비교", "Compare each condition with a reference"),
                _choice("user_specified", "직접 정의한 대비", "Use a researcher-defined contrast"),
                _choice("not_applicable", "비교가 연구목적이 아님", "No comparison is intended"),
            ),
            triggers=method_estimand,
            dependencies=("estimand.template",),
        ),
        _question(
            "confirm_dependence",
            "study.dependence_structure",
            AnswerKind.SINGLE_CHOICE,
            "비교하거나 연결할 관측값들이 서로 독립입니까, 같은 대상을 반복 측정한 값입니까?",
            "Are the observations independent, or are they repeated measurements of the same unit?",
            "관측값 사이의 연결 구조가 허용되는 분석 경로를 바꿉니다.",
            "The connection structure between observations changes the supported route.",
            choices=(
                _choice("independent", "서로 다른 독립 관측", "Different independent observations"),
                _choice("paired", "같은 대상의 짝지어진 관측", "Paired observations from the same unit"),
            ),
            triggers=(
                ClarificationTrigger.METHOD_IDENTITY_CHANGE,
                ClarificationTrigger.DESIGN_CHANGE,
            ),
            dependencies=(
                "study.data_layout",
                "study.temporal_structure",
            ),
        ),
        _question(
            "confirm_effect_scale",
            "estimand.effect_scale",
            AnswerKind.SINGLE_CHOICE,
            "연구 질문에 답할 핵심 수량은 무엇입니까?",
            "What target quantity answers the research question?",
            "목표 수량을 먼저 고정해야 결과의 의미가 뒤바뀌지 않습니다.",
            "Fixing the target quantity prevents the result's meaning from shifting.",
            choices=(
                _choice("distribution", "값의 분포와 요약", "Distribution and summary of values"),
                _choice("difference", "조건 또는 집단 사이의 차이", "Difference between conditions or groups"),
                _choice("correlation", "두 수치가 함께 변하는 정도", "Degree to which two numeric variables co-vary"),
            ),
            triggers=method_estimand,
            dependencies=("estimand.template",),
        ),
        _question(
            "confirm_estimand_template",
            "estimand.template",
            AnswerKind.SINGLE_CHOICE,
            "자료에서 정확히 무엇을 알아내려 합니까?",
            "What exactly should be learned from the data?",
            "질문의 대상 수량이 정해져야 분석 경로와 결론의 범위를 고정할 수 있습니다.",
            "The target quantity must be defined before the route and claim boundary can be fixed.",
            choices=(
                _choice("summary", "수치의 전반적 분포를 요약", "Summarize a numeric distribution"),
                _choice("frequency_distribution", "범주의 빈도·비율을 요약", "Summarize category counts or proportions"),
                _choice("group_contrast", "서로 다른 집단을 비교", "Compare different groups"),
                _choice("within_unit_change", "같은 대상의 변화를 비교", "Compare change within the same unit"),
                _choice("association", "두 변수의 관계를 요약", "Summarize a relationship between two variables"),
            ),
            triggers=action_estimand,
            dependencies=("question.research_goal",),
        ),
        _question(
            "confirm_focal_predictor_role",
            "estimand.role.focal_predictor",
            AnswerKind.VARIABLE_SINGLE,
            "관계를 살필 때 설명 쪽에 놓을 핵심 변수는 무엇입니까?",
            "Which focal variable is on the explanatory side of the relationship?",
            "변수의 역할을 명시해야 결과의 방향과 문장이 모호해지지 않습니다.",
            "Explicit roles keep the direction and wording of the result unambiguous.",
            triggers=(
                ClarificationTrigger.METHOD_IDENTITY_CHANGE,
                ClarificationTrigger.ROLE_CHANGE,
            ),
            dependencies=("estimand.template",),
        ),
        _question(
            "confirm_group_role",
            "estimand.role.group",
            AnswerKind.VARIABLE_SINGLE,
            "관측값을 비교할 조건이나 집단을 나타내는 변수는 무엇입니까?",
            "Which variable identifies the conditions or groups to compare?",
            "집단 역할이 고정되어야 비교 대상이 명확해집니다.",
            "The group role must be fixed to identify what is being compared.",
            triggers=(
                ClarificationTrigger.METHOD_IDENTITY_CHANGE,
                ClarificationTrigger.ROLE_CHANGE,
            ),
            dependencies=("estimand.template",),
        ),
        _question(
            "confirm_outcome_role",
            "estimand.role.outcome",
            AnswerKind.VARIABLE_SINGLE,
            "요약하거나 비교하거나 관계를 살필 핵심 결과 변수는 무엇입니까?",
            "Which focal outcome variable should be summarized, compared, or related?",
            "결과 역할이 정해져야 분석 대상과 보고 문장을 고정할 수 있습니다.",
            "The outcome role fixes the analysis target and reporting language.",
            triggers=(
                ClarificationTrigger.METHOD_IDENTITY_CHANGE,
                ClarificationTrigger.ROLE_CHANGE,
            ),
            dependencies=("estimand.template",),
        ),
        _question(
            "confirm_repeated_measure_order",
            "study.repeated_measure_order",
            AnswerKind.ORDERED_VARIABLES,
            "같은 대상을 반복 측정한 변수들을 실제 측정 순서대로 배열하십시오.",
            "Place the repeated-measure variables in their actual measurement order.",
            "순서가 뒤바뀌면 변화량의 방향과 해석도 뒤바뀝니다.",
            "Reversing the order reverses the direction and interpretation of change.",
            triggers=(
                ClarificationTrigger.METHOD_IDENTITY_CHANGE,
                ClarificationTrigger.DESIGN_CHANGE,
            ),
            dependencies=(
                "study.dependence_structure",
                "estimand.role.repeated_measure",
            ),
        ),
        _question(
            "confirm_repeated_measure_role",
            "estimand.role.repeated_measure",
            AnswerKind.VARIABLE_MULTI,
            "같은 대상을 반복 측정한 변수들은 무엇입니까?",
            "Which variables are repeated measurements of the same unit?",
            "반복 측정 변수의 묶음을 알아야 동일 대상 안의 변화를 정의할 수 있습니다.",
            "The repeated-measure set is needed to define change within a unit.",
            triggers=(
                ClarificationTrigger.METHOD_IDENTITY_CHANGE,
                ClarificationTrigger.ROLE_CHANGE,
                ClarificationTrigger.DESIGN_CHANGE,
            ),
            dependencies=(
                "estimand.template",
                "study.dependence_structure",
            ),
        ),
        _question(
            "confirm_research_goal",
            "question.research_goal",
            AnswerKind.SINGLE_CHOICE,
            "이 연구 질문의 주된 목적은 무엇입니까?",
            "What is the primary purpose of this research question?",
            "목적이 달라지면 필요한 목표 수량과 허용되는 결론이 달라집니다.",
            "A different purpose changes the target quantity and allowed conclusion.",
            choices=(
                _choice("describe", "한 표본의 상태를 기술", "Describe one sample"),
                _choice("compare", "조건이나 집단을 비교", "Compare conditions or groups"),
                _choice("associate", "변수 사이의 관계를 파악", "Examine a relationship between variables"),
                _choice("estimate_effect", "효과의 크기를 추정", "Estimate the size of an effect"),
            ),
            triggers=action_estimand,
        ),
        _question(
            "confirm_weight_use",
            "study.role.weight",
            AnswerKind.VARIABLE_MULTI,
            "표본의 대표성이나 선택확률을 보정하는 가중치 변수가 있습니까? 있다면 모두 선택하십시오.",
            "Are there weight variables that adjust representation or selection probability? Select all that apply.",
            "가중치를 무시하면 목표 모집단에 대한 해석이 달라질 수 있습니다.",
            "Ignoring weights can change interpretation for the target population.",
            triggers=(
                ClarificationTrigger.ACTION_CHANGE,
                ClarificationTrigger.DESIGN_CHANGE,
                ClarificationTrigger.DATA_POLICY_CHANGE,
            ),
            dependencies=("study.sampling_design",),
        ),
    )


def build_p1_clarification_registry() -> ClarificationRegistry:
    """Return the exact neutral question registry required by frozen P1 rules."""

    required = tuple(
        sorted(
            {
                rule.clarification_id
                for rule in build_p1_method_space().rules
                if rule.clarification_id is not None
            }
        )
    )
    questions = tuple(sorted(_questions(), key=lambda question: question.question_id))
    return ClarificationRegistry(
        questions=questions,
        required_question_ids=required,
    )
