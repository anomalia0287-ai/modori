from __future__ import annotations

import re
from pathlib import Path

from modori.ui.strings import UI_STRINGS_KO
from modori.ui.strings_en import UI_STRINGS_EN


QML_ROOT = Path("src/modori/ui/qml")
USER_VISIBLE_PROPERTY = re.compile(
    r"\b(text|placeholderText|title|Accessible\.name)\s*:\s*(?P<expression>.+)$"
)
STRING_LITERAL = re.compile(r'"(?P<value>[^"]*[A-Za-z가-힣][^"]*)"')
CATALOG_CALL = re.compile(
    r'appBootstrap\.text\("(?P<key>[^"]+)",\s*appBootstrap\.language\)'
)
NON_REACTIVE_CATALOG_CALL = re.compile(r'appBootstrap\.text\("[^"]+"\)')
CATALOG_MODEL_KEY = re.compile(r'"label"\s*:\s*"(?P<key>guide\.[^"]+)"')
COMPARISON_LITERAL = re.compile(r'(===|!==|==|!=)\s*"[^"]*"')
QSTR_LITERAL = re.compile(r'qsTr\("(?P<value>[^"]*[A-Za-z가-힣][^"]*)"\)')


def _catalog_keys_used_by_qml() -> set[str]:
    keys: set[str] = set()
    for path in sorted(QML_ROOT.rglob("*.qml")):
        text = path.read_text(encoding="utf-8")
        keys.update(CATALOG_CALL.findall(text))
        keys.update(CATALOG_MODEL_KEY.findall(text))
    return keys


def _raw_user_visible_literals(line: str) -> list[str]:
    violations = [match.group("value") for match in QSTR_LITERAL.finditer(line)]
    property_match = USER_VISIBLE_PROPERTY.search(line)
    if property_match is None:
        return violations
    expression = property_match.group("expression")
    expression = CATALOG_CALL.sub("appBootstrap.text()", expression)
    expression = COMPARISON_LITERAL.sub("", expression)
    violations.extend(match.group("value") for match in STRING_LITERAL.finditer(expression))
    return violations


def test_qml_static_user_visible_strings_use_catalog() -> None:
    violations: list[str] = []
    for path in sorted(QML_ROOT.rglob("*.qml")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            raw_literals = _raw_user_visible_literals(line)
            if raw_literals:
                violations.append(f"{path}:{line_number}:{', '.join(raw_literals)}")

    assert violations == []


def test_qml_catalog_bindings_observe_session_language() -> None:
    violations: list[str] = []
    for path in sorted(QML_ROOT.rglob("*.qml")):
        source = path.read_text(encoding="utf-8")
        if NON_REACTIVE_CATALOG_CALL.search(source):
            violations.append(str(path))

    assert violations == []


def test_qml_string_catalog_is_complete_and_used() -> None:
    used_keys = _catalog_keys_used_by_qml()

    missing_keys = sorted(used_keys - set(UI_STRINGS_KO))
    unused_keys = sorted(set(UI_STRINGS_KO) - used_keys)

    assert missing_keys == []
    assert unused_keys == []


def test_recommendation_surface_uses_one_persistent_experimental_status() -> None:
    assert UI_STRINGS_KO["entry.guided"] == "GUIDED MODE"
    assert UI_STRINGS_KO["work.guided"] == "GUIDED MODE"
    assert UI_STRINGS_EN["entry.guided"] == "GUIDED MODE"
    assert UI_STRINGS_EN["work.guided"] == "GUIDED MODE"
    assert "CASUAL MODE" not in UI_STRINGS_KO.values()
    assert "CASUAL MODE" not in UI_STRINGS_EN.values()
    assert UI_STRINGS_KO["entry.guided_description"] == (
        "연구 질문과 데이터 구조를 따라 분석 후보와 필요한 확인을 단계별로 안내합니다.\n"
        "실험적 연구 가이드 · 설정과 실행은 직접 확인"
    )
    assert UI_STRINGS_EN["entry.guided_description"] == (
        "Follow guided steps from your research question and data structure to a "
        "reviewable analysis candidate.\n"
        "Experimental research guide · You review the setup and start the run"
    )
    assert "entry.guided_badge" not in UI_STRINGS_KO
    assert "entry.guided_badge" not in UI_STRINGS_EN
    assert UI_STRINGS_KO["guide.title"] == "분석 후보 안내"
    assert UI_STRINGS_KO["guide.experimental_status"] == "실험적 가이드"
    assert UI_STRINGS_EN["guide.experimental_status"] == "Experimental guide"
    assert "guide.experimental_badge" not in UI_STRINGS_KO
    assert "guide.experimental_badge" not in UI_STRINGS_EN
    assert "research.legacy.experimental_status" not in UI_STRINGS_KO
    assert "research.legacy.experimental_status" not in UI_STRINGS_EN
    assert "research.experimental" not in UI_STRINGS_KO
    assert "research.experimental" not in UI_STRINGS_EN
    assert "research.no_auto_run" not in UI_STRINGS_KO
    assert "research.no_auto_run" not in UI_STRINGS_EN
    assert "research.confirmed_run_hint" not in UI_STRINGS_KO
    assert "research.confirmed_run_hint" not in UI_STRINGS_EN
    assert UI_STRINGS_KO["guide.candidate_list"] == "분석 후보 목록"
    assert UI_STRINGS_KO["guide.candidate_label"] == "분석 후보"
    assert UI_STRINGS_KO["guide.no_recommendation"] == (
        "현재 규칙으로 표시할 분석 후보가 없습니다. 수동 분석을 사용할 수 있습니다."
    )
    assert "분석 자동 추천" not in UI_STRINGS_KO.values()


def test_report_replacement_copy_names_the_destructive_action() -> None:
    assert UI_STRINGS_KO["dialog.report.conflict_title"] == (
        "같은 이름의 보고서가 있습니다"
    )
    assert UI_STRINGS_KO["dialog.report.keep_existing"] == "기존 파일 유지"
    assert UI_STRINGS_KO["dialog.report.replace_existing"] == "기존 파일 바꾸기"
    assert UI_STRINGS_EN["dialog.report.conflict_title"] == (
        "A report with this name already exists"
    )
    assert UI_STRINGS_EN["dialog.report.keep_existing"] == "Keep existing file"
    assert UI_STRINGS_EN["dialog.report.replace_existing"] == "Replace existing file"


def test_excel_sheet_recovery_copy_names_the_required_action() -> None:
    assert UI_STRINGS_KO["dialog.import.sheet_recovery"] == (
        "기본 시트에서 표를 찾지 못했습니다. 표가 있는 시트를 선택하고 "
        "미리보기를 새로 고치세요."
    )
    assert UI_STRINGS_EN["dialog.import.sheet_recovery"] == (
        "No table was found on the default sheet. Select the sheet that contains "
        "the table and refresh the preview."
    )


def test_research_os_surface_uses_experimental_and_no_auto_run_vocabulary() -> None:
    assert UI_STRINGS_KO["research.panel.title"] == "Research OS"
    assert UI_STRINGS_KO["research.transformation_first"].startswith(
        "역코딩·척도 구성·결측 처리"
    )
    assert UI_STRINGS_KO["research.preparation.review_badge"] == "설정 검토"
    assert UI_STRINGS_KO["research.preparation.confirmed_badge"] == "설정 확인됨"
    assert UI_STRINGS_KO["research.confirm_description"] == (
        "표시된 설정만 확인합니다."
    )
    assert UI_STRINGS_EN["research.preparation.review_badge"] == "Setup review"
    assert UI_STRINGS_EN["research.preparation.confirmed_badge"] == "Setup confirmed"
    assert UI_STRINGS_EN["research.confirm_description"] == (
        "Confirms only the displayed setup."
    )
    assert UI_STRINGS_KO["research.open_description"] == "로컬 연구과업 안내를 엽니다."
    assert UI_STRINGS_KO["research.close_description"] == "로컬 연구과업 안내를 닫습니다."
    assert UI_STRINGS_EN["research.open_description"] == (
        "Opens the local research-task guide."
    )
    assert UI_STRINGS_EN["research.close_description"] == (
        "Closes the local research-task guide."
    )
    assert UI_STRINGS_KO["research.legacy.title"] == "데이터 모양 기반 빠른 후보"
