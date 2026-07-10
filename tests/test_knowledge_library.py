from pathlib import Path

import pytest

from modori.knowledge import (
    ENGINE_VOCABULARY,
    HELP_KEYS,
    EntryKind,
    Library,
    LibraryEntry,
    LibraryLoadError,
    Reference,
    VerificationStatus,
    load_library,
    validate_citation_honesty,
    validate_coverage,
    validate_link_integrity,
    validate_slug_integrity,
)
from modori.knowledge.registry import USER_FACING_EXCLUDED_KEYS, normalize_help_key
from modori.results import (
    ChartSpec,
    CoefficientRow,
    ComparisonResult,
    GroupDesc,
    RegressionResult,
    ReliabilityResult,
)
from modori.steps.reporting import table_for


def _reference(verified: bool = True) -> Reference:
    return Reference(
        citation="Author, A. (2020). Real source. Publisher.",
        locator=None,
        verified=verified,
    )


def _entry(
    slug: str,
    kind: EntryKind,
    *,
    references: list[Reference] | None = None,
    status: VerificationStatus = VerificationStatus.VERIFIED,
    assumptions: list[str] | None = None,
    alternatives: list[str] | None = None,
    related: list[str] | None = None,
) -> LibraryEntry:
    needs_when_to_use = kind in {EntryKind.METHOD, EntryKind.DIAGNOSTIC}
    needs_interpretation = kind in {
        EntryKind.CONCEPT,
        EntryKind.STATISTIC,
        EntryKind.EFFECT_SIZE,
    }
    return LibraryEntry(
        slug=slug,
        kind=kind,
        title_ko=f"{slug} KO",
        title_en=f"{slug} EN",
        summary_ko=f"{slug} summary KO",
        summary_en=f"{slug} summary EN",
        interpretation_ko=f"{slug} interpretation KO" if needs_interpretation else None,
        interpretation_en=f"{slug} interpretation EN" if needs_interpretation else None,
        when_to_use_ko=f"{slug} use KO" if needs_when_to_use else None,
        when_to_use_en=f"{slug} use EN" if needs_when_to_use else None,
        how_to_report_ko=f"{slug} report KO",
        how_to_report_en=f"{slug} report EN",
        pitfalls_ko=f"{slug} pitfalls KO",
        pitfalls_en=f"{slug} pitfalls EN",
        assumptions=assumptions or [],
        alternatives=alternatives or [],
        related=related or [],
        references=references if references is not None else [_reference()],
        verification_status=status,
    )


def _closed_library() -> Library:
    entries = [
        _entry(
            "welch-t-test",
            EntryKind.METHOD,
            assumptions=["normality"],
            alternatives=["student-t-test"],
            related=["cohens-d", "p-value"],
        ),
        _entry("normality", EntryKind.ASSUMPTION),
        _entry("student-t-test", EntryKind.METHOD),
        _entry("cohens-d", EntryKind.EFFECT_SIZE),
        _entry("p-value", EntryKind.CONCEPT),
        _entry("cronbach-alpha", EntryKind.STATISTIC),
    ]
    return Library(
        entries,
        help_keys={"welch_t": "welch-t-test", "cronbach_alpha": "cronbach-alpha"},
    )


def _dummy_chart(chart_type: str = "horizontal_bar") -> ChartSpec:
    return ChartSpec(
        type=chart_type,
        title="chart",
        data={"values": {"q1": 0.7}},
        x_label="x",
        y_label="y",
    )


def _reliability_result() -> ReliabilityResult:
    return ReliabilityResult(
        scale_name="job_sat",
        n_items=4,
        n_cases=20,
        cronbach_alpha=0.80,
        alpha_ci=(0.70, 0.90),
        mcdonald_omega=0.82,
        item_total_corr={"q1": 0.70},
        alpha_if_deleted={"q1": 0.75},
        apa_template_id="reliability.v1",
        chart_spec=_dummy_chart(),
    )


def _comparison_result(test_name: str, effect_name: str) -> ComparisonResult:
    return ComparisonResult(
        dv="job_sat",
        group_var="group",
        test_name=test_name,
        route_reason="test route",
        groups={
            "1": GroupDesc(n=10, mean=3.0, sd=0.5, median=3.0),
            "2": GroupDesc(n=10, mean=4.0, sd=0.5, median=4.0),
        },
        statistic=-2.0,
        df=12.5,
        p_value=0.03,
        effect_name=effect_name,
        effect_value=-0.70,
        mean_diff_ci=(-1.5, -0.2),
        assumptions={"shapiro_g1_p": 0.20, "shapiro_g2_p": 0.30, "levene_p": 0.01},
        apa_template_id="mwu.v1" if test_name == "mann_whitney" else "ttest.v1",
        chart_spec=_dummy_chart(
            "box" if test_name == "mann_whitney" else "mean_ci_jitter"
        ),
        n_obs=20,
        n_total=20,
        n_dropped=0,
    )


def _paired_comparison_result(test_name: str, effect_name: str) -> ComparisonResult:
    return ComparisonResult(
        dv="post",
        group_var="pre",
        test_name=test_name,
        route_reason="paired route",
        groups={
            "pre": GroupDesc(n=10, mean=3.0, sd=0.5, median=3.0),
            "post": GroupDesc(n=10, mean=4.0, sd=0.5, median=4.0),
        },
        statistic=2.0,
        df=9.0 if test_name == "paired_t" else None,
        p_value=0.03,
        effect_name=effect_name,
        effect_value=0.70,
        mean_diff_ci=(0.2, 1.5) if test_name == "paired_t" else None,
        assumptions={"shapiro_diff_p": 0.20},
        apa_template_id="paired_t.v1" if test_name == "paired_t" else "wilcoxon.v1",
        chart_spec=_dummy_chart("paired_line"),
        n_obs=10,
        n_total=10,
        n_dropped=0,
        dv_label="Post score",
        group_label="Pre score",
        paired=True,
        before_label="Pre score",
        after_label="Post score",
    )


def _regression_result() -> RegressionResult:
    return RegressionResult(
        dv="job_sat",
        predictors=["autonomy"],
        n_obs=30,
        n_total=32,
        n_dropped=2,
        se_type="HC3",
        r_squared=0.40,
        adj_r_squared=0.35,
        f_statistic=5.0,
        df_model=1,
        df_resid=28,
        f_p_value=0.02,
        coefficients=[
            CoefficientRow(
                "(Intercept)", 1.0, 0.2, None, None, 5.0, 0.001, (0.6, 1.4), None
            ),
            CoefficientRow(
                "autonomy", 0.5, 0.1, 0.4, (0.1, 0.7), 4.0, 0.001, (0.3, 0.7), 1.1
            ),
        ],
        diagnostics={
            "breusch_pagan_p": 0.02,
            "bp_p": 0.02,
            "durbin_watson": 2.0,
            "dw": 2.0,
            "shapiro_resid_p": 0.50,
            "shapiro_p": 0.50,
            "max_cooks": 0.10,
            "cook_threshold": 0.13,
            "max_vif": 1.1,
            "model_test": "robust_wald_f",
        },
        warnings=[],
        apa_template_id="regression.v1",
        chart_spec=_dummy_chart("coefficient_forest"),
    )


def _actual_user_facing_terms_from_results() -> set[str]:
    raw_terms: set[str] = set()
    results = [
        _reliability_result(),
        _comparison_result("student_t", "cohen_d"),
        _comparison_result("welch_t", "cohen_d"),
        _comparison_result("mann_whitney", "rank_biserial"),
        _paired_comparison_result("paired_t", "cohen_dz"),
        _paired_comparison_result("wilcoxon", "rank_biserial"),
        _regression_result(),
    ]
    for result in results:
        rows = table_for(result)
        if rows:
            raw_terms.update(rows[0])
        if isinstance(result, ReliabilityResult):
            raw_terms.update({"cronbach_alpha", "mcdonald_omega"})
        if isinstance(result, ComparisonResult):
            raw_terms.update(
                {result.test_name, result.effect_name, "p_value", "df", "mean_diff_ci"}
            )
            raw_terms.update(result.assumptions)
        if isinstance(result, RegressionResult):
            raw_terms.update(
                {
                    "r_squared",
                    "adj_r_squared",
                    "f_statistic",
                    "df_model",
                    "df_resid",
                    "n_dropped",
                }
            )
            raw_terms.update(result.diagnostics)

    normalized_terms: set[str] = set()
    for raw_term in raw_terms:
        normalized = normalize_help_key(raw_term)
        if normalized is not None and normalized not in USER_FACING_EXCLUDED_KEYS:
            normalized_terms.add(normalized)
    return normalized_terms


def test_strict_loader_loads_approved_fixture_shape(tmp_path: Path) -> None:
    entry_path = tmp_path / "cronbach-alpha.yaml"
    entry_path.write_text(
        """
slug: cronbach-alpha
kind: statistic
title_ko: "크론바흐 알파"
title_en: "Cronbach's alpha"
summary_ko: "여러 문항이 같은 것을 재는지 알려 주는 점수."
summary_en: "A score showing whether items measure the same thing."
interpretation_ko: "내적 일관성 신뢰도입니다."
interpretation_en: "This is internal-consistency reliability."
when_to_use_ko: null
when_to_use_en: null
how_to_report_ko: "Cronbach's α = ..."
how_to_report_en: "Cronbach's α = ..."
pitfalls_ko: "문항 수에 영향을 받습니다."
pitfalls_en: "It is affected by item count."
assumptions: []
alternatives: []
related: []
references:
  - citation: "Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests. Psychometrika, 16(3), 297-334."
    locator: "16(3), 297-334"
    verified: true
verification_status: needs_review
""".strip(),
        encoding="utf-8",
    )

    library = load_library(tmp_path)

    entry = library.get("cronbach-alpha")
    assert entry.kind is EntryKind.STATISTIC
    assert entry.when_to_use_ko is None
    assert entry.references[0].verified is True


def test_strict_loader_uses_real_yaml_features(tmp_path: Path) -> None:
    entry_path = tmp_path / "rich-method.yaml"
    entry_path.write_text(
        """
slug: rich-method
kind: method
title_ko: "풍부한 YAML"
title_en: "Rich YAML"
summary_ko: |
  첫 줄입니다.
  두 번째 줄에는 쉼표, 콜론: 값이 함께 있습니다.
summary_en: >
  This folded summary contains commas, colons: and normal prose
  across multiple lines.
interpretation_ko: null
interpretation_en: null
when_to_use_ko: "값에 쉼표, 콜론: 이 있어도 안전해야 합니다."
when_to_use_en: "Use when quoted values contain commas, colons: and punctuation."
how_to_report_ko: "보고: 값, 값, 값"
how_to_report_en: "Report: value, value, value"
pitfalls_ko: "콜론: 쉼표, 따옴표를 손상하면 안 됩니다."
pitfalls_en: "Do not corrupt colons: commas, or quoted text."
assumptions:
  - normality
alternatives: []
related: []
references:
  - citation: "Author, A. (2020). Title with colon: subtitle, and commas. Journal, 1(2), 3-4."
    locator: "section 1: overview, table 2"
    verified: true
verification_status: verified
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "normality.yaml").write_text(
        """
slug: normality
kind: assumption
title_ko: "정규성"
title_en: "Normality"
summary_ko: "분포가 종 모양에 가까운지 보는 가정."
summary_en: "An assumption about a bell-shaped distribution."
verification_status: needs_review
""".strip(),
        encoding="utf-8",
    )

    library = load_library(tmp_path)
    entry = library.get("rich-method")

    assert (
        entry.summary_ko
        == "첫 줄입니다.\n두 번째 줄에는 쉼표, 콜론: 값이 함께 있습니다.\n"
    )
    assert "commas, colons: and normal prose across multiple lines." in entry.summary_en
    assert entry.when_to_use_ko == "값에 쉼표, 콜론: 이 있어도 안전해야 합니다."
    assert (
        entry.references[0].citation
        == "Author, A. (2020). Title with colon: subtitle, and commas. Journal, 1(2), 3-4."
    )
    assert entry.references[0].locator == "section 1: overview, table 2"


def test_strict_loader_rejects_unknown_fields(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text(
        """
slug: bad
kind: concept
title_ko: "bad"
title_en: "bad"
summary_ko: "bad"
summary_en: "bad"
interpretation_ko: "bad"
interpretation_en: "bad"
unknown_field: "must fail"
verification_status: needs_review
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(LibraryLoadError, match="Unknown field"):
        load_library(tmp_path)


def test_required_by_kind_is_enforced_for_method_and_statistic(tmp_path: Path) -> None:
    (tmp_path / "bad-method.yaml").write_text(
        """
slug: bad-method
kind: method
title_ko: "bad"
title_en: "bad"
summary_ko: "bad"
summary_en: "bad"
when_to_use_ko: null
when_to_use_en: "bad"
verification_status: needs_review
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(LibraryLoadError, match="when_to_use_ko"):
        load_library(tmp_path)


def test_library_api_returns_localized_layered_explanation_and_review_queue() -> None:
    needs_review = _entry(
        "welch-t-test",
        EntryKind.METHOD,
        status=VerificationStatus.NEEDS_REVIEW,
        references=[_reference(verified=False)],
        assumptions=["normality"],
    )
    library = Library(
        [needs_review, _entry("normality", EntryKind.ASSUMPTION)],
        help_keys={"welch_t": "welch-t-test"},
    )

    explanation = library.explain("welch-t-test", "ko")

    assert explanation["slug"] == "welch-t-test"
    assert explanation["kind"] == "method"
    assert explanation["title"] == "welch-t-test KO"
    assert explanation["summary"] == "welch-t-test summary KO"
    assert explanation["when_to_use"] == "welch-t-test use KO"
    assert explanation["assumptions"] == ["normality"]
    assert explanation["references"] == [
        {
            "citation": "Author, A. (2020). Real source. Publisher.",
            "locator": None,
            "verified": False,
        }
    ]
    assert library.resolve_help_key("welch_t") == "welch-t-test"
    assert [entry.slug for entry in library.needs_review()] == ["welch-t-test"]


def test_validators_pass_on_closed_controlled_library() -> None:
    library = _closed_library()

    assert validate_slug_integrity(library.entries()).ok
    assert validate_link_integrity(library).ok
    assert validate_coverage(
        {"welch_t", "cronbach_alpha"}, library.help_keys, library
    ).ok
    assert validate_citation_honesty(library).ok


def test_validators_flag_controlled_broken_cases() -> None:
    broken_entries = [
        _entry("BadSlug", EntryKind.CONCEPT),
        _entry("BadSlug", EntryKind.CONCEPT),
        _entry(
            "verified-without-source",
            EntryKind.CONCEPT,
            references=[],
            status=VerificationStatus.VERIFIED,
        ),
        _entry(
            "needs-review-entry",
            EntryKind.CONCEPT,
            references=[_reference(False)],
            status=VerificationStatus.NEEDS_REVIEW,
        ),
    ]
    broken_library = Library(
        [
            _entry(
                "welch-t-test", EntryKind.METHOD, assumptions=["missing-assumption"]
            ),
            _entry("cronbach-alpha", EntryKind.STATISTIC),
        ],
        help_keys={"welch_t": "missing-method"},
    )

    slug_report = validate_slug_integrity(broken_entries)
    link_report = validate_link_integrity(broken_library)
    coverage_report = validate_coverage(
        {"welch_t", "missing_engine_key"}, broken_library.help_keys, broken_library
    )
    citation_report = validate_citation_honesty(Library(broken_entries, help_keys={}))

    assert {issue.code for issue in slug_report.issues} >= {
        "duplicate_slug",
        "invalid_slug",
    }
    assert {issue.code for issue in link_report.issues} >= {
        "missing_entry_link",
        "missing_help_key_target",
    }
    assert {issue.code for issue in coverage_report.issues} >= {
        "missing_vocabulary_key",
        "missing_help_key_target",
    }
    assert {issue.code for issue in citation_report.issues} >= {
        "verified_without_verified_reference"
    }
    assert citation_report.needs_review == ("needs-review-entry",)


def test_engine_vocabulary_is_derived_from_actual_user_facing_outputs() -> None:
    actual_terms = _actual_user_facing_terms_from_results()
    library = load_library()

    assert ENGINE_VOCABULARY == actual_terms
    assert {"b", "se", "t", "df", "alpha_if_deleted"} <= actual_terms
    assert {
        "reliability.v1",
        "ttest.v1",
        "mwu.v1",
        "regression.v1",
        "report.apa.v1",
    } & actual_terms == set()
    assert {
        "stats.reliability",
        "stats.compare_groups",
        "stats.regression_ols",
    } & actual_terms == set()
    assert {
        "model_test",
        "classical_f",
        "robust_wald_f",
        "HC3",
        "classical",
    } & actual_terms == set()
    uncovered = sorted(
        term
        for term in actual_terms
        if library.resolve_help_key(term) not in library.all_slugs()
    )
    assert uncovered == []


def test_real_seed_fixtures_load_cleanly() -> None:
    library = load_library()

    assert {
        "welch-t-test",
        "cronbach-alpha",
        "descriptives-table1",
    } <= library.all_slugs()
    assert (
        library.get("welch-t-test").verification_status
        is VerificationStatus.NEEDS_REVIEW
    )
    assert library.get("welch-t-test").references[0].verified is False
    assert library.resolve_help_key("welch_t") == "welch-t-test"
    assert library.resolve_help_key("cronbach_alpha") == "cronbach-alpha"
    assert library.resolve_help_key("analysis.descriptives_table1") == "descriptives-table1"


def test_descriptives_help_entry_states_scope_and_exclusions() -> None:
    library = load_library()

    entry = library.get("descriptives-table1")
    combined_ko = " ".join(
        text
        for text in (
            entry.summary_ko,
            entry.when_to_use_ko,
            entry.how_to_report_ko,
            entry.pitfalls_ko,
        )
        if text
    )

    assert "기술통계" in entry.title_ko
    assert "차이 검정" in combined_ko
    assert "인과" in combined_ko
    assert "결측" in combined_ko
    assert "가중치" in combined_ko
    assert "복합표본" in combined_ko
    assert "다중대체" in combined_ko
    assert "표준화 평균차" in combined_ko


def test_seed_is_link_complete() -> None:
    library = load_library()

    assert validate_link_integrity(library).ok


def test_engine_vocabulary_fully_covered() -> None:
    library = load_library()

    assert validate_coverage(ENGINE_VOCABULARY, HELP_KEYS, library).ok


def test_logistic_help_entries_state_meaning_direction_and_limits() -> None:
    library = load_library()

    assert library.resolve_help_key("odds_ratio") == "odds-ratio"
    assert (
        library.resolve_help_key("model_likelihood_ratio")
        == "model-likelihood-ratio"
    )
    assert library.resolve_help_key("brier_score") == "brier-score"

    odds_ratio = library.get("odds-ratio")
    odds_ko = " ".join(
        text
        for text in (
            odds_ratio.summary_ko,
            odds_ratio.interpretation_ko,
            odds_ratio.pitfalls_ko,
        )
        if text
    )
    odds_en = " ".join(
        text
        for text in (
            odds_ratio.summary_en,
            odds_ratio.interpretation_en,
            odds_ratio.pitfalls_en,
        )
        if text
    )
    assert "사건" in odds_ko
    assert "기준범주" in odds_ko
    assert "인과" in odds_ko
    assert "event" in odds_en.lower()
    assert "reference" in odds_en.lower()
    assert "caus" in odds_en.lower()

    likelihood_ratio = library.get("model-likelihood-ratio")
    likelihood_ko = " ".join(
        text
        for text in (
            likelihood_ratio.summary_ko,
            likelihood_ratio.interpretation_ko,
            likelihood_ratio.pitfalls_ko,
        )
        if text
    )
    likelihood_en = " ".join(
        text
        for text in (
            likelihood_ratio.summary_en,
            likelihood_ratio.interpretation_en,
            likelihood_ratio.pitfalls_en,
        )
        if text
    )
    assert "절편만" in likelihood_ko
    assert "적합" in likelihood_ko
    assert "intercept-only" in likelihood_en.lower()
    assert "fit" in likelihood_en.lower()

    brier = library.get("brier-score")
    brier_ko = " ".join(
        text
        for text in (
            brier.summary_ko,
            brier.interpretation_ko,
            brier.pitfalls_ko,
        )
        if text
    )
    brier_en = " ".join(
        text
        for text in (
            brier.summary_en,
            brier.interpretation_en,
            brier.pitfalls_en,
        )
        if text
    )
    assert "0" in brier_ko
    assert "보정" in brier_ko
    assert "동일 자료" in brier_ko
    assert "calibration" in brier_en.lower()
    assert "in-sample" in brier_en.lower()


def test_factorial_help_entries_freeze_estimand_and_claim_limits() -> None:
    library = load_library()

    assert library.resolve_help_key("analysis.anova_factorial") == "anova-factorial"
    assert (
        library.resolve_help_key("type_iii_equal_cell_weight")
        == "type-iii-equal-cell-weight"
    )
    assert (
        library.resolve_help_key("interaction_gated_simple_effects")
        == "interaction-gated-simple-effects"
    )

    method = library.get("anova-factorial")
    method_ko = " ".join(
        text
        for text in (
            method.summary_ko,
            method.when_to_use_ko,
            method.how_to_report_ko,
            method.pitfalls_ko,
        )
        if text
    )
    method_en = " ".join(
        text
        for text in (
            method.summary_en,
            method.when_to_use_en,
            method.how_to_report_en,
            method.pitfalls_en,
        )
        if text
    )
    assert "완전 셀" in method_ko
    assert "동일 가중" in method_ko
    assert "빈 셀" in method_ko
    assert "complete-cell" in method_en.lower()
    assert "equal weight" in method_en.lower()
    assert "empty cell" in method_en.lower()

    estimand = library.get("type-iii-equal-cell-weight")
    estimand_ko = " ".join(
        text
        for text in (
            estimand.summary_ko,
            estimand.interpretation_ko,
            estimand.pitfalls_ko,
        )
        if text
    )
    estimand_en = " ".join(
        text
        for text in (
            estimand.summary_en,
            estimand.interpretation_en,
            estimand.pitfalls_en,
        )
        if text
    )
    assert "가산" in estimand_ko
    assert "오메가" in estimand_ko
    assert "점별" in estimand_ko
    assert "additive" in estimand_en.lower()
    assert "omega" in estimand_en.lower()
    assert "pointwise" in estimand_en.lower()
    assert "simultaneous" in estimand_en.lower()

    followups = library.get("interaction-gated-simple-effects")
    followups_ko = " ".join(
        text
        for text in (
            followups.summary_ko,
            followups.interpretation_ko,
            followups.pitfalls_ko,
        )
        if text
    )
    followups_en = " ".join(
        text
        for text in (
            followups.summary_en,
            followups.interpretation_en,
            followups.pitfalls_en,
        )
        if text
    )
    assert "하나의 Holm 가족" in followups_ko
    assert "검정력" in followups_ko
    assert "전체" in followups_ko and "가족오류율" in followups_ko
    assert "one Holm family" in followups_en
    assert "power" in followups_en.lower()
    assert "familywise" in followups_en.lower()
