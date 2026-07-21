from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from modori.ui.contracts import (
    ComparisonPatch,
    DataCellPatch,
    RegressionPatch,
    ReliabilityPatch,
    ReportPatch,
    VariableMetadataPatch,
)


class PatchValidationError(ValueError):
    def __init__(self, message_ko: str, *, error_code: str = "invalid_step_patch") -> None:
        super().__init__(message_ko)
        self.message_ko = message_ko
        self.error_code = error_code


def parse_step_patch(
    kind: str,
    payload: Mapping[str, Any],
    *,
    variable_keys: set[str] | None = None,
) -> object:
    if not isinstance(payload, Mapping):
        raise PatchValidationError("패치는 객체여야 합니다.")
    clean = dict(payload)
    transport_kind = clean.pop("kind", kind)
    if transport_kind != kind:
        raise PatchValidationError(f"패치 종류가 일치하지 않습니다: {transport_kind}")

    if kind == "reliability":
        _reject_unknown(kind, clean, {"item_keys", "language"})
        item_keys = _required_string_list(clean, "item_keys")
        _require_non_empty(item_keys, "item_keys")
        _require_known_variables(item_keys, variable_keys)
        return ReliabilityPatch(item_keys=item_keys, language=_required_language(clean, "language"))

    if kind == "comparison":
        _reject_unknown(kind, clean, {"outcome_key", "group_key", "group_a", "group_b", "language"})
        outcome_key = _required_string(clean, "outcome_key")
        group_key = _required_string(clean, "group_key")
        _require_known_variables([outcome_key, group_key], variable_keys)
        group_a = _required_scalar(clean, "group_a")
        group_b = _required_scalar(clean, "group_b")
        if group_a == group_b:
            raise PatchValidationError("서로 다른 두 집단을 선택해야 합니다.")
        return ComparisonPatch(
            outcome_key=outcome_key,
            group_key=group_key,
            group_a=group_a,
            group_b=group_b,
            language=_required_language(clean, "language"),
        )

    if kind == "regression":
        _reject_unknown(kind, clean, {"outcome_key", "predictor_keys", "include_intercept", "language"})
        outcome_key = _required_string(clean, "outcome_key")
        predictor_keys = _required_string_list(clean, "predictor_keys")
        _require_non_empty(predictor_keys, "predictor_keys")
        _require_known_variables([outcome_key, *predictor_keys], variable_keys)
        include_intercept = _required_bool(clean, "include_intercept")
        return RegressionPatch(
            outcome_key=outcome_key,
            predictor_keys=predictor_keys,
            include_intercept=include_intercept,
            language=_required_language(clean, "language"),
        )

    if kind == "report":
        _reject_unknown(
            kind,
            clean,
            {
                "language",
                "include_descriptives",
                "include_reliability",
                "include_comparison",
                "include_association",
                "include_group_models",
                "include_dimension_reduction",
                "include_regression",
                "include_figures",
            },
        )
        return ReportPatch(
            language=_required_language(clean, "language"),
            include_descriptives=_optional_bool(clean, "include_descriptives", True),
            include_reliability=_required_bool(clean, "include_reliability"),
            include_comparison=_required_bool(clean, "include_comparison"),
            include_association=_optional_bool(clean, "include_association", True),
            include_group_models=_optional_bool(clean, "include_group_models", True),
            include_dimension_reduction=_optional_bool(
                clean,
                "include_dimension_reduction",
                True,
            ),
            include_regression=_required_bool(clean, "include_regression"),
            include_figures=_required_bool(clean, "include_figures"),
        )

    if kind == "variable_metadata":
        _reject_unknown(
            kind,
            clean,
            {
                "variable_key",
                "label",
                "measure",
                "value_labels",
                "missing_codes",
                "missing_values",
                "display_type",
            },
        )
        if "display_type" in clean:
            raise PatchValidationError(
                "display_type 메타데이터 변경은 아직 지원하지 않습니다.",
                error_code="unsupported_metadata_patch",
            )
        if "missing_codes" in clean and "missing_values" in clean:
            raise PatchValidationError(
                "missing_codes와 missing_values를 동시에 보낼 수 없습니다.",
                error_code="invalid_metadata_patch",
            )
        variable_key = _required_string(clean, "variable_key")
        _require_known_variables([variable_key], variable_keys)
        measure = clean.get("measure")
        if measure is not None and measure not in {"scale", "ordinal", "nominal"}:
            raise PatchValidationError("측정수준은 scale, ordinal, nominal 중 하나여야 합니다.")
        missing_codes = clean.get("missing_codes", clean.get("missing_values"))
        if missing_codes is not None and not isinstance(missing_codes, list):
            raise PatchValidationError(
                "missing_codes 필드는 목록이어야 합니다.",
                error_code="invalid_metadata_patch",
            )
        return VariableMetadataPatch(
            variable_key=variable_key,
            label=_optional_string(clean, "label"),
            measure=measure,
            value_labels=clean.get("value_labels"),
            missing_codes=missing_codes,
            display_type=None,
        )

    if kind == "data_cell":
        _reject_unknown(kind, clean, {"row_id", "variable_key", "new_value"})
        variable_key = _required_string(clean, "variable_key")
        _require_known_variables([variable_key], variable_keys)
        if "new_value" not in clean:
            raise PatchValidationError("new_value 필드가 필요합니다.")
        return DataCellPatch(
            row_id=_required_string(clean, "row_id"),
            variable_key=variable_key,
            new_value=clean["new_value"],
        )

    raise PatchValidationError(f"지원하지 않는 패치 종류입니다: {kind}")


def _reject_unknown(kind: str, payload: Mapping[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise PatchValidationError(f"{kind} 패치에 알 수 없는 필드가 있습니다: {', '.join(unknown)}")


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise PatchValidationError(f"{key} 필드는 비어 있지 않은 문자열이어야 합니다.")
    return value


def _optional_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise PatchValidationError(f"{key} 필드는 문자열이어야 합니다.")
    return value


def _required_string_list(payload: Mapping[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise PatchValidationError(f"{key} 필드는 문자열 목록이어야 합니다.")
    return list(value)


def _required_language(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if value not in {"ko", "en"}:
        raise PatchValidationError(f"{key} 필드는 ko 또는 en이어야 합니다.")
    return value


def _required_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise PatchValidationError(f"{key} 필드는 boolean이어야 합니다.")
    return value


def _optional_bool(payload: Mapping[str, Any], key: str, default: bool) -> bool:
    if key not in payload:
        return default
    return _required_bool(payload, key)


def _required_scalar(payload: Mapping[str, Any], key: str) -> str | int | float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise PatchValidationError(f"{key} 필드는 문자열 또는 숫자여야 합니다.")
    return value


def _require_non_empty(values: list[str], key: str) -> None:
    if not values:
        raise PatchValidationError(f"{key} 필드는 비어 있을 수 없습니다.")


def _require_known_variables(values: list[str], variable_keys: set[str] | None) -> None:
    if variable_keys is None:
        return
    missing = sorted(set(values) - variable_keys)
    if missing:
        raise PatchValidationError(f"알 수 없는 변수입니다: {', '.join(missing)}")
