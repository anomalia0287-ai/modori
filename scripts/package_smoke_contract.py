from __future__ import annotations

from pathlib import Path


REQUIRED_HARDENED_PUBLIC_DATA_CASE_NAMES = frozenset(
    {
        "kosis-two-row-csv",
        "kosis-two-row-drop",
        "cp949-public-csv",
        "notice-only-xlsx-reject",
    }
)


def engine_payload_has_contract(
    payload: object,
    *,
    expected_cache_dir: str | Path | None = None,
) -> bool:
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return False
    statistics = payload.get("v1_statistics_smoke")
    if not isinstance(statistics, dict) or statistics.get("ok") is not True:
        return False
    if expected_cache_dir is not None and payload.get("cache_dir") != str(
        expected_cache_dir
    ):
        return False
    return True


def public_data_payload_has_contract(payload: object) -> bool:
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return False
    cases = payload.get("cases")
    case_count = payload.get("case_count")
    if not isinstance(cases, list) or not cases or case_count != len(cases):
        return False
    if any(not isinstance(case, dict) or case.get("ok") is not True for case in cases):
        return False
    names = {str(case.get("name")) for case in cases}
    if not REQUIRED_HARDENED_PUBLIC_DATA_CASE_NAMES.issubset(names):
        return False
    by_name = {str(case.get("name")): case for case in cases}
    if not _has_warning(
        by_name["kosis-two-row-csv"],
        "집계/합계 행 1개를 감지했습니다.",
    ):
        return False
    if _full_import_sample_contains(
        by_name["kosis-two-row-drop"],
        "행정구역별(1)",
        "전국",
    ):
        return False
    if not _has_full_import_warning(
        by_name["cp949-public-csv"],
        "CSV 인코딩: cp949",
    ):
        return False
    for case in cases:
        if case.get("status") == "expected_reject":
            if not case.get("preview_error") or not case.get("full_import_error"):
                return False
            continue
        if not isinstance(case.get("full_import"), dict):
            return False
    return True


def _has_warning(case: dict[str, object], expected: str) -> bool:
    warnings = case.get("warnings")
    if not isinstance(warnings, list):
        return False
    return any(expected in str(warning) for warning in warnings)


def _has_full_import_warning(case: dict[str, object], expected: str) -> bool:
    full_import = case.get("full_import")
    if not isinstance(full_import, dict):
        return False
    warnings = full_import.get("warnings")
    if not isinstance(warnings, list):
        return False
    return any(expected in str(warning) for warning in warnings)


def _full_import_sample_contains(
    case: dict[str, object],
    column: str,
    value: object,
) -> bool:
    full_import = case.get("full_import")
    if not isinstance(full_import, dict):
        return False
    sample_rows = full_import.get("sample_rows")
    if not isinstance(sample_rows, list):
        return False
    return any(
        isinstance(row, dict) and row.get(column) == value for row in sample_rows
    )
