from __future__ import annotations

import re
from pathlib import Path

from modori.ui.strings import UI_STRINGS_KO


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
    assert UI_STRINGS_KO["entry.guided"] == "CASUAL MODE"
    assert UI_STRINGS_KO["work.guided"] == "CASUAL MODE"
    assert UI_STRINGS_KO["guide.title"] == "분석 후보 안내"
    assert UI_STRINGS_KO["guide.experimental_status"] == "실험적 · 자동 실행 안 함"
    assert UI_STRINGS_KO["guide.candidate_list"] == "분석 후보 목록"
    assert UI_STRINGS_KO["guide.candidate_label"] == "분석 후보"
    assert UI_STRINGS_KO["guide.no_recommendation"] == (
        "현재 규칙으로 표시할 분석 후보가 없습니다. 수동 분석을 사용할 수 있습니다."
    )
    assert "분석 자동 추천" not in UI_STRINGS_KO.values()


def test_research_os_surface_uses_experimental_and_no_auto_run_vocabulary() -> None:
    assert UI_STRINGS_KO["research.panel.title"] == "Research OS"
    assert UI_STRINGS_KO["research.transformation_first"].startswith(
        "역코딩·척도 구성·결측 처리"
    )
    assert UI_STRINGS_KO["research.experimental"] == "실험적 후보"
    assert UI_STRINGS_KO["research.no_auto_run"] == (
        "검증 중인 분석 후보 · 자동 실행 안 함"
    )
    assert UI_STRINGS_KO["research.legacy.title"] == "데이터 모양 기반 빠른 후보"
