from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from modori.table_io import (
    ImportSelection,
    TableLayoutOverride,
    TablePreviewResult,
    TableReadError,
    TableSchema,
    read_schema,
)
from modori.ui.importing import ImportPreviewService
from modori.ui.localization import localize_message


class UiImportFlow:
    def __init__(self, preview_service: object | None = None) -> None:
        self._preview_service = preview_service or ImportPreviewService()
        self.preview_text = ""
        self.pending_path: Path | None = None
        self.table_preview: TablePreviewResult | None = None
        self.table_layout: dict[str, object] | None = None
        self.drop_aggregate_rows = False
        self.drop_duplicate_rows = False
        self.source_columns: tuple[str, ...] = ()
        self.import_selection: dict[str, object] | None = None
        self.recovery_available = False
        self.sheet_names: tuple[str, ...] = ()
        self.selected_sheet_name = ""
        self.language = "ko"
        self._preview_error_ko = ""

    def set_language(self, language: str) -> bool:
        selected = "en" if language == "en" else "ko" if language == "ko" else ""
        if not selected:
            return False
        self.language = selected
        if self.table_preview is not None:
            self.preview_text = self._preview_service.format_preview(
                self.table_preview,
                language=selected,
            )
        elif self._preview_error_ko:
            self.preview_text = localize_message(self._preview_error_ko, selected)
        return True

    def preview(
        self,
        path: Path,
        layout: TableLayoutOverride | None = None,
        *,
        drop_aggregate_rows: bool = False,
        drop_duplicate_rows: bool = False,
        included_columns: Sequence[object] | None = None,
    ) -> bool:
        previous_pending_path = self.pending_path
        previous_sheet_names = self.sheet_names
        previous_selected_sheet = self.selected_sheet_name
        schema: TableSchema | None = None
        selection: ImportSelection | None = None
        if included_columns is not None:
            try:
                schema = read_schema(path, layout=layout)
            except TableReadError as exc:
                self._record_preview_failure(
                    exc.message_ko,
                    layout=layout,
                    pending_path=path,
                    previous_pending_path=previous_pending_path,
                    previous_sheet_names=previous_sheet_names,
                    previous_selected_sheet=previous_selected_sheet,
                )
                return False
            except Exception:
                self._record_preview_failure(
                    "파일 미리보기를 만들지 못했습니다.",
                    layout=layout,
                    pending_path=path,
                    previous_pending_path=previous_pending_path,
                    previous_sheet_names=previous_sheet_names,
                    previous_selected_sheet=previous_selected_sheet,
                )
                return False
            selection = _selection_from_schema(schema, included_columns)
        preview_kwargs: dict[str, object] = {}
        if layout is not None:
            preview_kwargs["layout"] = layout
        if selection is not None:
            preview_kwargs["selection"] = selection
        if drop_aggregate_rows:
            preview_kwargs["drop_aggregate_rows"] = True
        if drop_duplicate_rows:
            preview_kwargs["drop_duplicate_rows"] = True
        preview = self._preview_service.preview(path, **preview_kwargs)
        self.preview_text = preview.text
        if preview.ok:
            table_preview = getattr(preview, "table_preview", None)
            if table_preview is not None:
                if schema is None:
                    try:
                        schema = read_schema(path, layout=layout)
                    except TableReadError as exc:
                        self._record_preview_failure(
                            exc.message_ko,
                            layout=layout,
                            pending_path=path,
                            previous_pending_path=previous_pending_path,
                            previous_sheet_names=previous_sheet_names,
                            previous_selected_sheet=previous_selected_sheet,
                        )
                        return False
                    except Exception:
                        self._record_preview_failure(
                            "파일 미리보기를 만들지 못했습니다.",
                            layout=layout,
                            pending_path=path,
                            previous_pending_path=previous_pending_path,
                            previous_sheet_names=previous_sheet_names,
                            previous_selected_sheet=previous_selected_sheet,
                        )
                        return False
                if selection is None:
                    selection = _selection_from_schema(schema, schema.columns)
            self.pending_path = preview.pending_path
            self.table_preview = table_preview
            self.table_layout = _table_layout_params(layout)
            self.drop_aggregate_rows = bool(drop_aggregate_rows)
            self.drop_duplicate_rows = bool(drop_duplicate_rows)
            self.source_columns = schema.columns if schema is not None else ()
            self.import_selection = _selection_payload(selection) if selection is not None else None
            self.recovery_available = False
            self.sheet_names = tuple(getattr(preview, "sheet_names", ()) or ())
            self.selected_sheet_name = str(
                getattr(preview, "sheet_name", None) or ""
            )
            self._preview_error_ko = ""
            if self.table_preview is not None:
                self.preview_text = self._preview_service.format_preview(
                    self.table_preview,
                    language=self.language,
                )
        else:
            self._record_preview_failure(
                preview.text,
                layout=layout,
                pending_path=preview.pending_path,
                previous_pending_path=previous_pending_path,
                schema=schema,
                selection=selection,
                recovery_available=bool(
                    getattr(preview, "recovery_available", False)
                ),
                sheet_name=getattr(preview, "sheet_name", None),
                sheet_names=tuple(getattr(preview, "sheet_names", ()) or ()),
                previous_sheet_names=previous_sheet_names,
                previous_selected_sheet=previous_selected_sheet,
            )
        return bool(preview.ok)

    def column_rows(self) -> list[dict[str, object]]:
        if not self.source_columns:
            return []
        included_columns = _included_columns_from_payload(self.import_selection)
        included = set(included_columns or self.source_columns)
        return [
            {"name": column, "included": column in included}
            for column in self.source_columns
        ]

    def require_pending_path(self) -> Path | None:
        if self.pending_path is None:
            self._set_preview_error("가져올 파일이 선택되지 않았습니다.")
            return None
        if self.table_preview is None:
            return None
        return self.pending_path

    def require_pending_file_path(self) -> Path | None:
        if self.pending_path is None:
            self._set_preview_error("가져올 파일이 선택되지 않았습니다.")
            return None
        return self.pending_path

    def _set_preview_error(self, message_ko: str) -> None:
        self._preview_error_ko = message_ko
        self.preview_text = localize_message(message_ko, self.language)

    def _record_preview_failure(
        self,
        message: str,
        *,
        layout: TableLayoutOverride | None,
        pending_path: Path | None,
        previous_pending_path: Path | None,
        schema: TableSchema | None = None,
        selection: ImportSelection | None = None,
        recovery_available: bool = False,
        sheet_name: str | None = None,
        sheet_names: tuple[str, ...] = (),
        previous_sheet_names: tuple[str, ...] = (),
        previous_selected_sheet: str = "",
    ) -> None:
        self._set_preview_error(message)
        if layout is not None:
            self.pending_path = previous_pending_path
            self.sheet_names = sheet_names or previous_sheet_names
            self.selected_sheet_name = previous_selected_sheet
            self.recovery_available = bool(self.sheet_names)
        else:
            self.pending_path = pending_path
            self.sheet_names = sheet_names
            self.selected_sheet_name = str(sheet_name or "")
            self.recovery_available = bool(recovery_available and sheet_names)
        self.table_preview = None
        self.table_layout = None
        self.drop_aggregate_rows = False
        self.drop_duplicate_rows = False
        self.source_columns = schema.columns if schema is not None else ()
        self.import_selection = _selection_payload(selection) if selection is not None else None


def _selection_from_schema(
    schema: TableSchema,
    included_columns: Sequence[object],
) -> ImportSelection:
    return ImportSelection(
        source_columns=schema.columns,
        included_columns=tuple(str(column) for column in included_columns),
        schema_fingerprint=schema.fingerprint,
    )


def _selection_payload(selection: ImportSelection) -> dict[str, object]:
    return {
        "schema_version": selection.schema_version,
        "source_columns": list(selection.source_columns),
        "included_columns": list(selection.included_columns),
        "schema_fingerprint": selection.schema_fingerprint,
        "created_from": selection.created_from,
    }


def _included_columns_from_payload(payload: dict[str, object] | None) -> tuple[str, ...] | None:
    if not payload:
        return None
    included = payload.get("included_columns")
    if included is None:
        return None
    return tuple(str(column) for column in included)


def _table_layout_params(layout: TableLayoutOverride | None) -> dict[str, object] | None:
    if layout is None:
        return None
    params: dict[str, object] = {}
    if layout.sheet_name:
        params["sheet_name"] = layout.sheet_name
    if layout.header_row_index is not None:
        params["header_row_index"] = layout.header_row_index
    if layout.header_row_count is not None:
        params["header_row_count"] = layout.header_row_count
    if layout.data_start_row_index is not None:
        params["data_start_row_index"] = layout.data_start_row_index
    return params or None
