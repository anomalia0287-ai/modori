from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from scipy.stats import pearsonr, spearmanr

from scripts.prepare_build_week_demo_data import (
    DemoDataError,
    OUTPUT_COLUMNS,
    SOURCE_ARCHIVE_SHA256,
    prepare_build_week_demo_data,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARCHIVE = (
    ROOT / "examples" / "build-week-demo" / "source" / "uci-student-performance.zip"
)
COMMITTED_OUTPUT = (
    ROOT / "examples" / "build-week-demo" / "student-study-and-grades.csv"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_official_archive_regenerates_committed_demo_byte_for_byte(tmp_path) -> None:
    first_csv = tmp_path / "first.csv"
    first_summary = tmp_path / "first.json"
    second_csv = tmp_path / "second.csv"
    second_summary = tmp_path / "second.json"

    first = prepare_build_week_demo_data(
        SOURCE_ARCHIVE,
        first_csv,
        summary_path=first_summary,
    )
    second = prepare_build_week_demo_data(
        SOURCE_ARCHIVE,
        second_csv,
        summary_path=second_summary,
    )

    assert _sha256(SOURCE_ARCHIVE) == SOURCE_ARCHIVE_SHA256
    assert first_csv.read_bytes() == second_csv.read_bytes()
    assert first_summary.read_bytes() == second_summary.read_bytes()
    assert first_csv.read_bytes() == COMMITTED_OUTPUT.read_bytes()
    assert json.loads(first_summary.read_text(encoding="utf-8")) == first
    assert json.loads(second_summary.read_text(encoding="utf-8")) == second
    assert first == second


def test_committed_demo_is_nonidentifying_and_matches_independent_statistics() -> None:
    frame = pd.read_csv(COMMITTED_OUTPUT)

    assert list(frame.columns) == list(OUTPUT_COLUMNS)
    assert len(frame) == 649
    assert frame.isna().sum().to_dict() == {column: 0 for column in OUTPUT_COLUMNS}
    assert frame["weekly_study_time_band"].between(1, 4).all()
    assert frame["past_class_failures"].between(0, 3).all()
    assert frame["school_absences"].between(0, 32).all()
    assert set(frame["family_educational_support"]) == {"no", "yes"}
    assert set(frame["plans_higher_education"]) == {"no", "yes"}
    assert frame["final_grade"].between(0, 20).all()
    forbidden_source_fields = {
        "school",
        "sex",
        "age",
        "address",
        "famsize",
        "Pstatus",
        "Medu",
        "Fedu",
        "Mjob",
        "Fjob",
        "guardian",
        "romantic",
        "Dalc",
        "Walc",
    }
    assert set(frame.columns).isdisjoint(forbidden_source_fields)
    assert not any(column.lower().endswith("_id") for column in frame.columns)

    spearman = spearmanr(frame["weekly_study_time_band"], frame["final_grade"])
    pearson = pearsonr(frame["weekly_study_time_band"], frame["final_grade"])

    assert float(spearman.statistic) == pytest.approx(
        0.2747118483356099,
        abs=1e-12,
    )
    assert float(spearman.pvalue) == pytest.approx(
        1.060624038270125e-12,
        rel=1e-12,
    )
    assert float(pearson.statistic) == pytest.approx(
        0.24978868999886286,
        abs=1e-12,
    )


def test_hash_failure_is_atomic_and_preserves_existing_outputs(tmp_path) -> None:
    corrupted = tmp_path / "corrupted.zip"
    payload = bytearray(SOURCE_ARCHIVE.read_bytes())
    payload[-1] ^= 0x01
    corrupted.write_bytes(payload)
    output = tmp_path / "demo.csv"
    output.write_bytes(b"preserve me\n")
    summary = tmp_path / "summary.json"

    with pytest.raises(DemoDataError, match="source archive SHA-256 mismatch"):
        prepare_build_week_demo_data(
            corrupted,
            output,
            summary_path=summary,
        )

    assert output.read_bytes() == b"preserve me\n"
    assert not summary.exists()
