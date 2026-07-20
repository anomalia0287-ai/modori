"""Prepare the fixed, attributed Build Week social-science demo CSV offline."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from zipfile import BadZipFile, ZipFile

import pandas as pd
from pandas.api.types import is_integer_dtype
from scipy.stats import pearsonr, spearmanr


SOURCE_ARCHIVE_SHA256 = (
    "82ae9d66437b9808df42e8c89d2bb179c46e9cfbcf06f38abc1d20b3b747e177"
)
INNER_ARCHIVE_SHA256 = (
    "4f671ae4598c20bb4e64de0f65931c98a609a52e383604e2601bd8f7e3822427"
)
SOURCE_MEMBER_SHA256 = (
    "a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f"
)
EXPECTED_ROW_COUNT = 649
EXPECTED_SPEARMAN = 0.2747118483356099

SOURCE_COLUMNS = (
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
    "reason",
    "guardian",
    "traveltime",
    "studytime",
    "failures",
    "schoolsup",
    "famsup",
    "paid",
    "activities",
    "nursery",
    "higher",
    "internet",
    "romantic",
    "famrel",
    "freetime",
    "goout",
    "Dalc",
    "Walc",
    "health",
    "absences",
    "G1",
    "G2",
    "G3",
)
SOURCE_TO_OUTPUT = {
    "studytime": "weekly_study_time_band",
    "failures": "past_class_failures",
    "absences": "school_absences",
    "famsup": "family_educational_support",
    "higher": "plans_higher_education",
    "G3": "final_grade",
}
OUTPUT_COLUMNS = tuple(SOURCE_TO_OUTPUT.values())

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    REPO_ROOT
    / "examples"
    / "build-week-demo"
    / "source"
    / "uci-student-performance.zip"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "examples"
    / "build-week-demo"
    / "student-study-and-grades.csv"
)


class DemoDataError(ValueError):
    """Raised when the frozen public-data preparation contract is not met."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_source_member(source_archive: Path) -> bytes:
    try:
        outer_payload = source_archive.read_bytes()
    except OSError as exc:
        raise DemoDataError(f"source archive could not be read: {source_archive}") from exc
    if _sha256(outer_payload) != SOURCE_ARCHIVE_SHA256:
        raise DemoDataError("source archive SHA-256 mismatch")

    try:
        with ZipFile(BytesIO(outer_payload)) as outer:
            if outer.namelist().count("student.zip") != 1:
                raise DemoDataError("source archive must contain one student.zip")
            inner_payload = outer.read("student.zip")
    except (BadZipFile, KeyError, OSError) as exc:
        raise DemoDataError("source archive structure is invalid") from exc
    if _sha256(inner_payload) != INNER_ARCHIVE_SHA256:
        raise DemoDataError("inner archive SHA-256 mismatch")

    try:
        with ZipFile(BytesIO(inner_payload)) as inner:
            if inner.namelist().count("student-por.csv") != 1:
                raise DemoDataError(
                    "inner archive must contain one student-por.csv"
                )
            member_payload = inner.read("student-por.csv")
    except (BadZipFile, KeyError, OSError) as exc:
        raise DemoDataError("inner archive structure is invalid") from exc
    if _sha256(member_payload) != SOURCE_MEMBER_SHA256:
        raise DemoDataError("source member SHA-256 mismatch")
    return member_payload


def _require_integer_range(
    frame: pd.DataFrame,
    column: str,
    lower: int,
    upper: int,
) -> None:
    values = frame[column]
    if not is_integer_dtype(values.dtype) or not values.between(lower, upper).all():
        raise DemoDataError(
            f"{column} must contain integers from {lower} through {upper}"
        )


def _prepare_frame(member_payload: bytes) -> pd.DataFrame:
    try:
        source = pd.read_csv(BytesIO(member_payload), sep=";")
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise DemoDataError("student-por.csv could not be parsed") from exc
    if tuple(source.columns) != SOURCE_COLUMNS:
        raise DemoDataError("student-por.csv schema mismatch")
    if len(source) != EXPECTED_ROW_COUNT:
        raise DemoDataError("student-por.csv row count mismatch")

    demo = source.loc[:, tuple(SOURCE_TO_OUTPUT)].rename(columns=SOURCE_TO_OUTPUT)
    if demo.isna().any().any():
        raise DemoDataError("chosen demo fields must not contain missing values")

    _require_integer_range(demo, "weekly_study_time_band", 1, 4)
    _require_integer_range(demo, "past_class_failures", 0, 3)
    _require_integer_range(demo, "school_absences", 0, 32)
    _require_integer_range(demo, "final_grade", 0, 20)
    for column in ("family_educational_support", "plans_higher_education"):
        if set(demo[column]) != {"no", "yes"}:
            raise DemoDataError(f"{column} must contain only no and yes")

    statistic = float(
        spearmanr(demo["weekly_study_time_band"], demo["final_grade"]).statistic
    )
    if abs(statistic - EXPECTED_SPEARMAN) > 1e-12:
        raise DemoDataError("weekly-study-time Spearman reference mismatch")
    return demo


def _summary_for(demo: pd.DataFrame, output_payload: bytes) -> dict[str, Any]:
    study_time = demo["weekly_study_time_band"]
    final_grade = demo["final_grade"]
    pearson = pearsonr(study_time, final_grade)
    spearman = spearmanr(study_time, final_grade)
    numeric_columns = (
        "weekly_study_time_band",
        "past_class_failures",
        "school_absences",
        "final_grade",
    )
    return {
        "source": {
            "archive_sha256": SOURCE_ARCHIVE_SHA256,
            "inner_archive_sha256": INNER_ARCHIVE_SHA256,
            "member_sha256": SOURCE_MEMBER_SHA256,
        },
        "output": {
            "sha256": _sha256(output_payload),
            "rows": len(demo),
            "columns": list(demo.columns),
            "missing_counts": {
                column: int(value)
                for column, value in demo.isna().sum().items()
            },
            "ranges": {
                column: {
                    "min": int(demo[column].min()),
                    "max": int(demo[column].max()),
                }
                for column in numeric_columns
            },
        },
        "weekly_study_time_vs_final_grade": {
            "n": len(demo),
            "pearson_r": float(pearson.statistic),
            "pearson_p_two_sided": float(pearson.pvalue),
            "spearman_rho": float(spearman.statistic),
            "spearman_p_two_sided": float(spearman.pvalue),
        },
    }


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary = Path(handle.name)
        os.replace(temporary, path)
    except OSError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def prepare_build_week_demo_data(
    source_archive: Path,
    output_path: Path,
    *,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Validate the frozen UCI source and atomically write the demo view."""

    member_payload = _read_source_member(Path(source_archive))
    demo = _prepare_frame(member_payload)
    output_payload = demo.to_csv(index=False, lineterminator="\n").encode("utf-8")
    summary = _summary_for(demo, output_payload)
    summary_payload = (
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    _write_atomic(Path(output_path), output_payload)
    if summary_path is not None:
        _write_atomic(Path(summary_path), summary_payload)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare the fixed UCI Student Performance demo CSV offline."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--summary",
        dest="summary_path",
        type=Path,
        help="Optional path for deterministic JSON evidence.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        summary = prepare_build_week_demo_data(
            args.source,
            args.output,
            summary_path=args.summary_path,
        )
    except DemoDataError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
