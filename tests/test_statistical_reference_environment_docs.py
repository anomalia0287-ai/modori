from pathlib import Path


REFERENCE_ENV_DOC = Path("docs/specs/statistical-reference-environment.md")


def test_statistical_reference_environment_doc_records_r_prerequisites() -> None:
    text = REFERENCE_ENV_DOC.read_text(encoding="utf-8")

    assert "MODORI_RSCRIPT" in text
    assert "psych" in text
    assert "sandwich" in text
    assert "tests\\test_reliability_step.py::test_mcdonald_omega_matches_r_psych_when_r_is_available" in text
    assert "tests\\test_regression_step.py::test_regression_matches_committed_r_reference_when_r_is_available" in text
