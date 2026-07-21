from pathlib import Path


MANUAL_QA_DOC = Path("docs/specs/release-manual-qa.md")


def test_release_manual_qa_doc_covers_required_matrix_items() -> None:
    text = MANUAL_QA_DOC.read_text(encoding="utf-8")

    required_terms = [
        "Korean Windows path",
        "long filename",
        "high DPI",
        "low GPU",
        "reduce-effects",
        "broken input file",
        "report export failure",
        "accessibility smoke",
        "screenshot evidence",
    ]

    missing = [term for term in required_terms if term not in text]

    assert missing == []
