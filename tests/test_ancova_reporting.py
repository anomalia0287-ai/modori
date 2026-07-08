from __future__ import annotations

import importlib

import pytest


def _modules():
    try:
        reporting = importlib.import_module("modori.ancova_reporting")
        results = importlib.import_module("modori.ancova_results")
    except ModuleNotFoundError as exc:
        if exc.name in {"modori.ancova_reporting", "modori.ancova_results"}:
            pytest.fail(f"{exc.name} is not implemented")
        raise
    return reporting, results


def _result(is_interpretable: bool = True):
    _, results = _modules()
    return results.AncovaResult(
        analysis_key="ancova",
        title_ko="공분산분석",
        dv="outcome",
        dv_label="결과점수",
        group="group",
        group_label="배정군",
        covariates=("pretest",),
        covariate_labels=("사전점수",),
        homogeneity_alpha=0.05,
        n_total=10,
        n_used=8,
        n_excluded=2,
        groups=(
            results.AncovaGroupSummary(
                group_value="A",
                group_label="대조군",
                n=4,
                raw_mean=11.2345,
                raw_sd=1.5,
                adjusted_mean=11.9876 if is_interpretable else None,
            ),
            results.AncovaGroupSummary(
                group_value="B",
                group_label="중재군",
                n=4,
                raw_mean=15.4321,
                raw_sd=2.0,
                adjusted_mean=14.8765 if is_interpretable else None,
            ),
        ),
        homogeneity_check=results.AncovaEffectResult(
            term="group:covariates",
            label_ko="회귀기울기 동질성",
            f_statistic=1.2 if is_interpretable else 8.4,
            df_num=1,
            df_den=4,
            p_value=0.33 if is_interpretable else 0.04,
            effect_size_name="partial_eta_squared",
            effect_size=0.23,
        ),
        group_effect=(
            results.AncovaEffectResult(
                term="group",
                label_ko="집단 효과",
                f_statistic=5.25,
                df_num=1,
                df_den=5,
                p_value=0.041,
                effect_size_name="partial_eta_squared",
                effect_size=0.5123,
            )
            if is_interpretable
            else None
        ),
        covariate_effects=(),
        is_interpretable=is_interpretable,
        warnings_ko=()
        if is_interpretable
        else (
            "회귀기울기 동질성 검정이 기준을 넘겨 표준 ANCOVA 집단 효과를 해석하지 않습니다.",
        ),
        notes_ko=("집단 소속이 결과를 원인적으로 변화시킨다는 뜻은 아니다.",),
        no_canonical_chart_reason_ko="중앙 차트 렌더링 훅이 아직 연결되지 않아 차트를 생성하지 않는다.",
    )


def test_ancova_reporting_formats_verified_noncausal_korean_output() -> None:
    reporting, _ = _modules()
    result = _result(is_interpretable=True)

    prose = reporting.prose_for_ancova(result, language="ko")
    rows = reporting.table_for_ancova_groups(result)

    assert "공분산분석" in prose
    assert "원인" not in prose
    assert "영향" not in prose
    assert "affect" not in prose.lower()
    assert "회귀기울기 동질성" in prose
    assert "F(1, 5) = 5.250" in prose
    assert rows == [
        {
            "group": "대조군",
            "n": "4",
            "raw_mean": "11.235",
            "raw_sd": "1.500",
            "adjusted_mean": "11.988",
        },
        {
            "group": "중재군",
            "n": "4",
            "raw_mean": "15.432",
            "raw_sd": "2.000",
            "adjusted_mean": "14.877",
        },
    ]


def test_ancova_reporting_warns_when_homogeneity_check_fails_closed() -> None:
    reporting, _ = _modules()
    result = _result(is_interpretable=False)

    prose = reporting.prose_for_ancova(result, language="ko")
    rows = reporting.table_for_ancova_groups(result)

    assert "해석하지 않습니다" in prose
    assert "표준 ANCOVA 집단 효과" in prose
    assert "F(" not in prose
    assert all(row["adjusted_mean"] == "" for row in rows)
