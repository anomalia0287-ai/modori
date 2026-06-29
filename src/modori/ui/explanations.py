from __future__ import annotations

from collections.abc import Mapping


class ExplanationPresenter:
    def plain_text(self, *, title: str, content: Mapping[str, object], fallback: str) -> str:
        summary = str(content.get("summary", ""))
        text = f"{title}\n{summary}".strip()
        return text or fallback

    def rich_text(
        self,
        *,
        title: str,
        content: Mapping[str, object],
        language: str,
        fallback: str = "",
    ) -> str:
        labels = self.labels(language)
        sections = [title]
        for key in (
            "summary",
            "when_to_use",
            "interpretation",
            "how_to_report",
            "pitfalls",
        ):
            value = content.get(key)
            if value:
                sections.append(f"{labels[key]}\n{value}")
        for key in ("assumptions", "alternatives", "related"):
            values = content.get(key)
            if isinstance(values, list) and values:
                sections.append(f"{labels[key]}\n" + "\n".join(f"- {value}" for value in values))
        references = content.get("references")
        if isinstance(references, list) and references:
            lines = []
            for reference in references:
                if not isinstance(reference, Mapping):
                    continue
                status = labels["verified"] if reference.get("verified") else labels["needs_review"]
                locator = reference.get("locator")
                locator_text = f" ({locator})" if locator else ""
                lines.append(f"- [{status}] {reference.get('citation', '')}{locator_text}")
            if lines:
                sections.append(f"{labels['references']}\n" + "\n".join(lines))
        text = "\n\n".join(sections).strip()
        return text or fallback

    @staticmethod
    def labels(language: str) -> dict[str, str]:
        if language.lower().startswith("en"):
            return {
                "summary": "Summary",
                "when_to_use": "When to use",
                "interpretation": "Interpretation",
                "how_to_report": "How to report",
                "pitfalls": "Pitfalls",
                "assumptions": "Assumptions",
                "alternatives": "Alternatives",
                "related": "Related",
                "references": "References",
                "verified": "verified",
                "needs_review": "needs review",
            }
        return {
            "summary": "요약",
            "when_to_use": "사용 시점",
            "interpretation": "해석",
            "how_to_report": "보고 방법",
            "pitfalls": "주의점",
            "assumptions": "가정",
            "alternatives": "대안",
            "related": "관련 항목",
            "references": "참고문헌",
            "verified": "검증됨",
            "needs_review": "검토 필요",
        }
