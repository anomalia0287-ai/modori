from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from importlib import metadata
from pathlib import Path

from modori.recommendation_baseline import load_case_dataset, predict_current_baseline
from modori.recommendation_benchmark import (
    BenchmarkContractError,
    LabelingRates,
    PredictionRecord,
    ScorerConfig,
    canonical_json,
    project_labeling_cost,
    reviewer_agreement,
    score_predictions,
    scorer_fingerprint,
)
from modori.recommendation_benchmark_io import (
    PilotCaseSummary,
    load_adjudication_workbook,
    load_reviewer_workbook,
    read_jsonl,
    workbook_schema_fingerprint,
    write_jsonl,
)

if __package__:
    from scripts.build_recommendation_pilot import validate_pilot_pack
else:
    from build_recommendation_pilot import validate_pilot_pack


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_SCORER_IMPLEMENTATION_PATHS = (
    (
        "src/modori/recommendation_benchmark.py",
        _REPOSITORY_ROOT / "src" / "modori" / "recommendation_benchmark.py",
    ),
    (
        "src/modori/recommendation_benchmark_io.py",
        _REPOSITORY_ROOT / "src" / "modori" / "recommendation_benchmark_io.py",
    ),
    (
        "scripts/recommendation_benchmark.py",
        _REPOSITORY_ROOT / "scripts" / "recommendation_benchmark.py",
    ),
)


def scorer_runtime_identity() -> dict[str, str]:
    return {
        "defusedxml_version": metadata.version("defusedxml"),
        "machine": platform.machine(),
        "openpyxl_version": metadata.version("openpyxl"),
        "os_release": platform.release(),
        "os_system": platform.system(),
        "os_version": platform.version(),
        "python_compiler": platform.python_compiler(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
    }


def scorer_implementation_digest() -> str:
    manifest: list[dict[str, str]] = []
    for logical_path, source_path in _SCORER_IMPLEMENTATION_PATHS:
        if not source_path.is_file():
            raise BenchmarkContractError(
                f"scorer implementation source is missing: {logical_path}"
            )
        source = source_path.read_text(encoding="utf-8")
        manifest.append(
            {
                "path": logical_path,
                "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            }
        )
    payload = canonical_json(
        {
            "runtime": scorer_runtime_identity(),
            "sources": manifest,
        }
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _as_mapping(value: Mapping[str, object]) -> dict[str, object]:
    return dict(value)


def _load_cases(
    pack_root: Path,
) -> tuple[tuple[dict[str, object], ...], tuple[PilotCaseSummary, ...]]:
    cases = read_jsonl(
        pack_root / "public" / "pilot" / "cases.jsonl",
        _as_mapping,
    )
    summaries = tuple(PilotCaseSummary.from_case_mapping(case) for case in cases)
    return cases, summaries


def _write_json_output(
    path: Path,
    payload: Mapping[str, object],
    *,
    force: bool,
) -> None:
    write_jsonl(path, (payload,), overwrite=force)


def _load_reviewers(args: argparse.Namespace, summaries: tuple[PilotCaseSummary, ...]):
    reviewer_a = load_reviewer_workbook(args.reviewer_a, summaries)
    reviewer_b = load_reviewer_workbook(args.reviewer_b, summaries)
    return reviewer_a, reviewer_b


def _run_validate_pack(args: argparse.Namespace) -> dict[str, object]:
    report = validate_pilot_pack(args.pack_root)
    scorer_config = ScorerConfig()
    runtime_identity = scorer_runtime_identity()
    implementation_digest = scorer_implementation_digest()
    return {
        "ok": True,
        "case_count": report.case_count,
        "manifest_count": report.manifest_count,
        "unique_data_file_count": report.unique_data_file_count,
        "scorer_config": asdict(scorer_config),
        "scorer_runtime_identity": runtime_identity,
        "scorer_implementation_digest": implementation_digest,
        "scorer_fingerprint": scorer_fingerprint(scorer_config, implementation_digest),
    }


def _run_predict_a(args: argparse.Namespace) -> None:
    cases, _summaries = _load_cases(args.pack_root)
    pilot_root = args.pack_root / "public" / "pilot"
    predictions = tuple(
        predict_current_baseline(case, load_case_dataset(case, pilot_root))
        for case in cases
    )
    write_jsonl(args.output, predictions, overwrite=args.force)


def _run_validate_submissions(args: argparse.Namespace) -> dict[str, object]:
    _cases, summaries = _load_cases(args.pack_root)
    reviewer_a, reviewer_b = _load_reviewers(args, summaries)
    adjudicated = load_adjudication_workbook(args.adjudication, summaries)
    return {
        "ok": True,
        "case_count": len(summaries),
        "reviewer_ids": [reviewer_a.reviewer_id, reviewer_b.reviewer_id],
        "adjudicator_id": adjudicated.adjudicator_id,
        "reviewer_schema_fingerprints": [
            workbook_schema_fingerprint(args.reviewer_a),
            workbook_schema_fingerprint(args.reviewer_b),
        ],
        "adjudication_schema_fingerprint": workbook_schema_fingerprint(
            args.adjudication
        ),
    }


def _run_agreement(args: argparse.Namespace) -> dict[str, object]:
    _cases, summaries = _load_cases(args.pack_root)
    reviewer_a, reviewer_b = _load_reviewers(args, summaries)
    return asdict(reviewer_agreement(reviewer_a, reviewer_b))


def _run_cost(args: argparse.Namespace) -> dict[str, object]:
    _cases, summaries = _load_cases(args.pack_root)
    reviewers = _load_reviewers(args, summaries)
    adjudicated = load_adjudication_workbook(args.adjudication, summaries)
    projection = project_labeling_cost(
        reviewers,
        adjudicated.adjudications,
        stage_case_count=args.stage_cases,
        rates=LabelingRates(
            reviewer_hourly=args.reviewer_rate,
            adjudicator_hourly=args.adjudicator_rate,
            setup_cost=args.setup_cost,
            recruitment_cost=args.recruitment_cost,
            data_steward_cost=args.data_steward_cost,
            project_management_cost=args.project_management_cost,
        ),
    )
    return asdict(projection)


def _run_score(args: argparse.Namespace) -> dict[str, object]:
    config = ScorerConfig()
    implementation_digest = scorer_implementation_digest()
    expected_fingerprint = scorer_fingerprint(config, implementation_digest)
    if args.scorer_fingerprint != expected_fingerprint:
        raise BenchmarkContractError(
            "scorer fingerprint mismatch: "
            f"expected {expected_fingerprint}, received {args.scorer_fingerprint}"
        )
    _cases, summaries = _load_cases(args.pack_root)
    adjudicated = load_adjudication_workbook(args.adjudication, summaries)
    predictions = read_jsonl(args.predictions, PredictionRecord.from_mapping)
    return asdict(
        score_predictions(
            adjudicated.gold_records,
            predictions,
            config,
            implementation_digest=implementation_digest,
        )
    )


def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")


def _add_pack_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pack-root", type=Path, required=True)


def _add_reviewers(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and evaluate Modori's local recommendation benchmark."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    validate_pack = commands.add_parser("validate-pack")
    _add_pack_root(validate_pack)
    _add_output_arguments(validate_pack)

    predict_a = commands.add_parser("predict-a")
    _add_pack_root(predict_a)
    _add_output_arguments(predict_a)

    validate_submissions = commands.add_parser("validate-submissions")
    _add_pack_root(validate_submissions)
    _add_reviewers(validate_submissions)
    validate_submissions.add_argument("--adjudication", type=Path, required=True)
    _add_output_arguments(validate_submissions)

    agreement = commands.add_parser("agreement")
    _add_pack_root(agreement)
    _add_reviewers(agreement)
    _add_output_arguments(agreement)

    cost = commands.add_parser("cost")
    _add_pack_root(cost)
    _add_reviewers(cost)
    cost.add_argument("--adjudication", type=Path, required=True)
    cost.add_argument("--stage-cases", type=int, choices=(150, 200, 800), required=True)
    cost.add_argument("--reviewer-rate", type=float, required=True)
    cost.add_argument("--adjudicator-rate", type=float, required=True)
    cost.add_argument("--setup-cost", type=float, default=0.0)
    cost.add_argument("--recruitment-cost", type=float, default=0.0)
    cost.add_argument("--data-steward-cost", type=float, default=0.0)
    cost.add_argument("--project-management-cost", type=float, default=0.0)
    _add_output_arguments(cost)

    score = commands.add_parser("score")
    _add_pack_root(score)
    score.add_argument("--adjudication", type=Path, required=True)
    score.add_argument("--predictions", type=Path, required=True)
    score.add_argument("--scorer-fingerprint", required=True)
    _add_output_arguments(score)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "predict-a":
            _run_predict_a(args)
            return 0
        runners = {
            "validate-pack": _run_validate_pack,
            "validate-submissions": _run_validate_submissions,
            "agreement": _run_agreement,
            "cost": _run_cost,
            "score": _run_score,
        }
        payload = runners[args.command](args)
        _write_json_output(args.output, payload, force=args.force)
        return 0
    except (BenchmarkContractError, OSError, ValueError) as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
