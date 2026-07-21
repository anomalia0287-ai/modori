import json
from pathlib import Path

import pandas as pd

from scripts import stress_matrix


def test_generate_synthetic_survey_frame_is_deterministic() -> None:
    first = stress_matrix.generate_synthetic_survey_frame(6)
    second = stress_matrix.generate_synthetic_survey_frame(6)

    assert first.equals(second)
    assert list(first.columns) == [
        "q1",
        "q2",
        "q3",
        "q4",
        "q5",
        "q6",
        "q7",
        "q8",
        "group",
    ]
    assert first.shape == (6, 9)


def test_run_stress_matrix_records_required_operations(tmp_path) -> None:
    results = stress_matrix.run_stress_matrix(
        output_dir=tmp_path,
        cases=[stress_matrix.StressCase(name="tiny-csv", rows=12, file_type="csv")],
    )

    operations = {result["operation"] for result in results}

    assert operations == {"preview", "full_import", "analysis", "report_export"}
    assert all(result["dataset"] == "tiny-csv" for result in results)
    assert all(result["rows"] == 12 for result in results)
    assert all(result["columns"] == 9 for result in results)
    assert all(result["status"] == "pass" for result in results)
    assert all(result["elapsed_seconds"] >= 0 for result in results)
    assert all(result["command"] for result in results)


def test_stress_matrix_main_writes_json_results(tmp_path) -> None:
    output_dir = tmp_path / "stress"
    json_out = tmp_path / "results.json"

    exit_code = stress_matrix.main(
        [
            "--output-dir",
            str(output_dir),
            "--rows",
            "12",
            "--formats",
            "csv",
            "--json-out",
            str(json_out),
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert {row["operation"] for row in payload} == {
        "preview",
        "full_import",
        "analysis",
        "report_export",
    }
    assert pd.read_csv(output_dir / "survey-12.csv").shape == (12, 9)


def test_release_checklist_documents_stress_matrix_gate() -> None:
    text = Path("docs/specs/release-readiness-checklist.md").read_text(
        encoding="utf-8"
    )

    assert "scripts\\stress_matrix.py" in text
    assert "--rows" in text
    assert "preview" in text
    assert "report_export" in text
    assert ".stress-matrix" in text
