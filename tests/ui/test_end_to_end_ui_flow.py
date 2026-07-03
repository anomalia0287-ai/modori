from pathlib import Path


def write_reference_csv(path: Path) -> None:
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
    lines = ["q1,q2,q3,q4,q5,q6,q7,q8,group"]
    for group, rows in [(1, group1_scores), (2, group2_scores)]:
        for scores in rows:
            raw = list(scores)
            raw[2] = 6 - raw[2]
            raw[6] = 6 - raw[6]
            lines.append(",".join([*(str(value) for value in raw), str(group)]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_default_controller_reference_flow_runs_to_report(tmp_path) -> None:
    from modori.ui.contracts import ImportOptions, ReportExportOptions
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    opened = controller.openDataFile(data_path, ImportOptions(confirm_new_session=True))
    assert opened.ok is True

    rerun = controller.runPreparedRecommendation()
    assert rerun.ok is True
    assert controller.waitForLastRun(timeout=10) is True

    result_ids = [result.result_id for result in controller.resultsModel]
    assert "reliability:selected_scale" in result_ids
    assert controller.stale is False

    exported = controller.exportReport(ReportExportOptions(language="ko"))
    assert exported.ok is True
    assert Path(exported.result_ids[0]).exists()


def test_app_launcher_exposes_ui_controller_context() -> None:
    source = Path("src/modori/app.py").read_text(encoding="utf-8")

    assert "UiController" in source
    assert "uiController" in source


def test_commercial_v1_qa_document_exists() -> None:
    qa = Path("docs/specs/04-ui-shell-commercial-v1-qa.md")

    assert qa.is_file()
    text = qa.read_text(encoding="utf-8")
    assert "Gate evidence" in text
    assert "Known release-scope limitations" in text
    assert "Commercial v1 verdict" in text
