from pathlib import Path

from modori.workflow import AnalysisPreferences, build_reference_slice_pipeline


def write_reference_slice_csv(path: Path, *, separated_groups: bool) -> None:
    group1_scores = [
        [3, 2, 3, 2, 4, 4, 4, 4],
        [3, 2, 4, 2, 4, 4, 2, 4],
        [3, 3, 2, 3, 2, 2, 2, 2],
        [4, 3, 4, 2, 3, 4, 4, 3],
        [3, 3, 3, 4, 3, 2, 4, 2],
        [3, 3, 2, 3, 4, 3, 3, 3],
        [4, 4, 2, 4, 3, 4, 4, 3],
        [3, 3, 2, 4, 2, 3, 4, 3],
        [4, 2, 4, 2, 3, 4, 3, 3],
        [3, 2, 3, 3, 4, 3, 3, 4],
    ]
    group2_scores = [
        [4, 4, 5, 3, 4, 4, 4, 5],
        [4, 4, 5, 3, 4, 4, 4, 3],
        [5, 4, 4, 5, 4, 4, 5, 5],
        [4, 3, 5, 5, 4, 4, 3, 4],
        [4, 5, 5, 4, 5, 3, 5, 5],
        [3, 5, 4, 3, 4, 3, 4, 4],
        [3, 4, 4, 3, 5, 4, 4, 3],
        [4, 5, 4, 5, 4, 5, 4, 4],
        [3, 3, 3, 3, 4, 5, 3, 5],
        [4, 4, 4, 5, 4, 3, 4, 4],
    ]
    if not separated_groups:
        group2_scores = group1_scores

    lines = ["q1,q2,q3,q4,q5,q6,q7,q8,group"]
    for group, rows in [(1, group1_scores), (2, group2_scores)]:
        for scores in rows:
            raw = list(scores)
            raw[2] = 6 - raw[2]
            raw[6] = 6 - raw[6]
            lines.append(",".join([*(str(value) for value in raw), str(group)]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def pipeline_signature(pipeline):
    return [
        (step.__class__.__name__, step.params)
        for step in pipeline.steps
    ]


def test_guided_and_standard_modes_create_the_same_engine_steps(tmp_path) -> None:
    prefs = AnalysisPreferences()
    guided = build_reference_slice_pipeline(
        data_path=tmp_path / "survey.csv",
        output_dir=tmp_path,
        mode="guided",
        preferences=prefs,
    )
    standard = build_reference_slice_pipeline(
        data_path=tmp_path / "survey.csv",
        output_dir=tmp_path,
        mode="standard",
        preferences=prefs,
    )

    assert pipeline_signature(guided) == pipeline_signature(standard)


def test_step_params_snapshot_preferences_at_creation_time(tmp_path) -> None:
    prefs = AnalysisPreferences(
        routing_policy="always_welch",
        missing_policy={"preset": "custom", "min_valid": 0.75},
        default_compose_method="sum",
        report_language="en",
    )
    pipeline = build_reference_slice_pipeline(
        data_path=tmp_path / "survey.csv",
        output_dir=tmp_path,
        mode="guided",
        preferences=prefs,
    )

    prefs.routing_policy = "classic"
    prefs.missing_policy = {"preset": "conservative"}
    prefs.default_compose_method = "mean"
    prefs.report_language = "ko"

    compose = next(step for step in pipeline.steps if step.id == "compose-job-sat")
    compare = next(step for step in pipeline.steps if step.id == "compare-groups")
    report = next(step for step in pipeline.steps if step.id == "report")

    assert compose.params["method"] == "sum"
    assert compose.params["missing_policy"] == {"preset": "custom", "min_valid": 0.75}
    assert compare.params["routing_policy"] == {"preset": "always_welch"}
    assert report.params["language"] == "en"


def test_reference_slice_runs_end_to_end_in_guided_and_standard_modes(tmp_path) -> None:
    for mode in ["guided", "standard"]:
        data_path = tmp_path / f"{mode}.csv"
        output_dir = tmp_path / mode
        write_reference_slice_csv(data_path, separated_groups=True)
        pipeline = build_reference_slice_pipeline(
            data_path=data_path,
            output_dir=output_dir,
            mode=mode,
            preferences=AnalysisPreferences(),
        )

        pipeline.recompute(dirty_from=None)

        report = pipeline.analysis_objects["report"]
        assert Path(report.docx_path).exists()
        assert "reliability:job_sat" in pipeline.analysis_objects
        assert "comparison:job_sat:group" in pipeline.analysis_objects
        assert pipeline.current_dataset.df["job_sat"].notna().all()
        assert report.prose


def test_reference_slice_one_click_rerun_updates_final_report(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    output_dir = tmp_path / "report"
    write_reference_slice_csv(data_path, separated_groups=True)
    pipeline = build_reference_slice_pipeline(
        data_path=data_path,
        output_dir=output_dir,
        mode="guided",
        preferences=AnalysisPreferences(),
    )
    pipeline.recompute(dirty_from=None)
    first_report = pipeline.analysis_objects["report"]
    first_prose = list(first_report.prose)

    write_reference_slice_csv(data_path, separated_groups=False)
    pipeline.recompute(dirty_from="import")
    second_report = pipeline.analysis_objects["report"]

    assert first_prose != second_report.prose
    assert Path(second_report.docx_path).exists()
    assert any("통계적으로 유의하였다" in sentence for sentence in first_prose)
    assert any("통계적으로 유의하지 않았다" in sentence for sentence in second_report.prose)


def test_reference_slice_reverse_code_param_change_updates_downstream_report(
    tmp_path,
) -> None:
    data_path = tmp_path / "survey.csv"
    output_dir = tmp_path / "report"
    write_reference_slice_csv(data_path, separated_groups=True)
    pipeline = build_reference_slice_pipeline(
        data_path=data_path,
        output_dir=output_dir,
        mode="standard",
        preferences=AnalysisPreferences(),
    )
    pipeline.recompute(dirty_from=None)
    first_score = pipeline.current_dataset.df["job_sat"].copy()
    first_reliability = pipeline.analysis_objects["reliability:job_sat"]
    first_comparison = pipeline.analysis_objects["comparison:job_sat:group"]
    first_report = pipeline.analysis_objects["report"]

    pipeline.edit_params(
        "reverse-negative-items",
        {"columns": ["q3", "q7"], "scale_min": 1, "scale_max": 7},
    )

    second_score = pipeline.current_dataset.df["job_sat"]
    second_reliability = pipeline.analysis_objects["reliability:job_sat"]
    second_comparison = pipeline.analysis_objects["comparison:job_sat:group"]
    second_report = pipeline.analysis_objects["report"]

    assert not first_score.equals(second_score)
    assert first_reliability.mcdonald_omega != second_reliability.mcdonald_omega
    assert first_comparison is not second_comparison
    first_group_label = next(iter(first_comparison.groups))
    assert (
        first_comparison.groups[first_group_label].mean
        != second_comparison.groups[first_group_label].mean
    )
    assert first_report.prose != second_report.prose


def test_pyside_app_module_exposes_qml_main_entrypoint() -> None:
    from modori.app import main

    assert callable(main)
