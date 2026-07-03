from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_DISPLAY_ERROR_MESSAGE_KO = "결과를 표시하지 못했습니다."
_DISPLAY_ERROR_CODE = "result_display_error"


@dataclass(frozen=True)
class ResultPayloadValidation:
    ok: bool
    message_ko: str = ""
    error_code: str | None = None


class ResultPayloadValidator:
    def validate(self, payload: Any) -> ResultPayloadValidation:
        if not isinstance(payload, list) or not payload:
            return self._display_error()
        if any(not getattr(item, "result_id", None) for item in payload):
            return self._display_error()
        if any(
            not getattr(item, "title_ko", None) and not getattr(item, "prose_ko", None)
            for item in payload
        ):
            return self._display_error()
        return ResultPayloadValidation(ok=True)

    @staticmethod
    def _display_error() -> ResultPayloadValidation:
        return ResultPayloadValidation(
            ok=False,
            message_ko=_DISPLAY_ERROR_MESSAGE_KO,
            error_code=_DISPLAY_ERROR_CODE,
        )
