from __future__ import annotations

from modori.ui.explanations import ExplanationPresenter


def test_explanation_presenter_formats_layered_korean_content() -> None:
    presenter = ExplanationPresenter()

    text = presenter.rich_text(
        title="Cronbach alpha",
        content={
            "summary": "내적 일관성 지표입니다.",
            "interpretation": "값이 클수록 일관성이 높습니다.",
            "references": [
                {"citation": "Cronbach (1951)", "verified": True},
                {"citation": "Pending source", "verified": False, "locator": "p. 10"},
            ],
        },
        language="ko",
    )

    assert "Cronbach alpha" in text
    assert "요약\n내적 일관성 지표입니다." in text
    assert "해석\n값이 클수록 일관성이 높습니다." in text
    assert "[검증됨] Cronbach (1951)" in text
    assert "[검토 필요] Pending source (p. 10)" in text

