from __future__ import annotations

import pandas as pd

from modori.ui.importing import ImportPreviewService


def test_import_preview_service_returns_variable_summary(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    pd.DataFrame({"group": [1, 2], "score": [3.5, 4.5]}).to_csv(data_path, index=False)

    preview = ImportPreviewService().preview(data_path)

    assert preview.ok is True
    assert preview.pending_path == data_path
    assert "2 cases" in preview.text
    assert "2 variables" in preview.text
    assert "group" in preview.text
    assert "score" in preview.text


def test_import_preview_service_surfaces_xlsx_source_context_and_sample(tmp_path) -> None:
    data_path = tmp_path / "survey.xlsx"
    with pd.ExcelWriter(data_path) as writer:
        pd.DataFrame({"group": [1, 2], "score": [3.5, 4.5]}).to_excel(
            writer,
            sheet_name="Responses",
            index=False,
        )
        pd.DataFrame({"code": [1], "label": ["control"]}).to_excel(
            writer,
            sheet_name="Codebook",
            index=False,
        )

    preview = ImportPreviewService().preview(data_path)

    assert preview.ok is True
    assert preview.pending_path == data_path
    assert "파일: survey.xlsx" in preview.text
    assert "시트: Responses" in preview.text
    assert "전체 시트: Responses, Codebook" in preview.text
    assert "미리보기: 앞 30행 중 2행" in preview.text
    assert "샘플 행" in preview.text
    assert "group=1" in preview.text
    assert "score=3.5" in preview.text


def test_import_preview_service_surfaces_preview_limit_warning(tmp_path) -> None:
    data_path = tmp_path / "wide-survey.csv"
    frame = pd.DataFrame({f"v{index}": [index] for index in range(51)})
    frame.to_csv(data_path, index=False)

    preview = ImportPreviewService().preview(data_path)

    assert preview.ok is True
    assert "미리보기 열 제한: 51개 중 50개 열만 표시합니다." in preview.text


def test_import_preview_service_surfaces_public_data_header_warning(tmp_path) -> None:
    data_path = tmp_path / "public-with-preamble.csv"
    data_path.write_text(
        "\n".join(
            [
                "서울시 인구 현황",
                "자료기준일: 2024-12-31",
                "단위: 명",
                "자치구,연도,인구",
                "종로구,2024,140000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    preview = ImportPreviewService().preview(data_path)

    assert preview.ok is True
    assert "추론: 헤더 1행, 데이터 시작 5행, 확신 high" in preview.text
    assert "근거: 표 헤더 앞의 안내 행 3개를 건너뛰었습니다." in preview.text
    assert "표 헤더 앞의 안내 행 3개를 건너뛰었습니다." in preview.text
    assert "자치구" in preview.text
    assert "종로구" in preview.text


def test_import_preview_service_accepts_text_xls_public_data(tmp_path) -> None:
    data_path = tmp_path / "weather.xls"
    text = "지점\t지점명\t일시\t기온(°C)\n108\t서울\t2026-07-06 01:00\t25.1\n"
    data_path.write_bytes(text.encode("cp949"))

    preview = ImportPreviewService().preview(data_path)

    assert preview.ok is True
    assert "4 variables" in preview.text
    assert "XLS 확장자이지만 텍스트 표로 읽었습니다." in preview.text
    assert "근거: XLS 확장자이지만 텍스트 표로 읽었습니다." in preview.text
    assert "지점명=서울" in preview.text


def test_import_preview_service_rejects_notice_only_xlsx_with_specific_error(tmp_path) -> None:
    from openpyxl import Workbook

    data_path = tmp_path / "notice-only.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["□ 본 서비스에서 제공하는 정보는 참고용으로만 활용하시기 바랍니다."])
    workbook.save(data_path)
    workbook.close()

    preview = ImportPreviewService().preview(data_path)

    assert preview.ok is False
    assert preview.text == "표 데이터가 없습니다. 원본 포털에서 CSV 파일을 다시 받거나 표가 있는 시트를 선택해 주세요."


def test_import_preview_service_reads_bounded_csv_preview(tmp_path, monkeypatch) -> None:
    data_path = tmp_path / "large-survey.csv"
    data_path.write_text("score\n1\n2\n", encoding="utf-8")
    calls = []

    def read_csv_spy(path_arg, *args, **kwargs):
        calls.append(kwargs)
        return pd.DataFrame({"score": [1, 2, 3]})

    monkeypatch.setattr("modori.table_io.pd.read_csv", read_csv_spy)

    preview = ImportPreviewService().preview(data_path)

    assert preview.ok is True
    assert calls == [{"nrows": 0}, {"nrows": 30}]
