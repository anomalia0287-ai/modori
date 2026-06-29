from __future__ import annotations

from pathlib import Path

from modori.ui.settings import UiSettingsStore


class UiSessionState:
    def __init__(
        self,
        settings_store: UiSettingsStore,
        *,
        reduce_effects_override: bool | None = None,
    ) -> None:
        self._settings_store = settings_store
        settings = settings_store.load()
        self._reduce_effects = (
            bool(reduce_effects_override)
            if reduce_effects_override is not None
            else bool(settings.get("reduce_effects", False))
        )
        self._recent_files_enabled = bool(settings.get("recent_files_enabled", True))
        self._recent_files = list(settings.get("recent_files", []))[:5]
        self._explain_mode_enabled = bool(settings.get("explain_mode_enabled", True))

    @property
    def reduce_effects(self) -> bool:
        return self._reduce_effects

    @property
    def recent_files_enabled(self) -> bool:
        return self._recent_files_enabled

    @property
    def recent_files(self) -> list[str]:
        return list(self._recent_files)

    @property
    def explain_mode_enabled(self) -> bool:
        return self._explain_mode_enabled

    @property
    def recent_files_text(self) -> str:
        names = [Path(path).name for path in self._recent_files]
        duplicate_names = {name for name in names if names.count(name) > 1}
        labels = []
        for path in self._recent_files:
            recent_path = Path(path)
            if recent_path.name in duplicate_names:
                labels.append(f"{recent_path.name} - {self._compact_parent_hint(recent_path)}")
            else:
                labels.append(recent_path.name)
        return "\n".join(labels)

    @staticmethod
    def _compact_parent_hint(path: Path, *, max_chars: int = 42) -> str:
        parts = [part for part in path.parent.parts if part != path.anchor]
        if not parts:
            hint = str(path.parent)
        else:
            hint = "\\".join(parts[-2:])
        if len(hint) <= max_chars:
            return hint
        return "..." + hint[-(max_chars - 3) :]

    def set_reduce_effects(self, enabled: bool) -> None:
        self._reduce_effects = bool(enabled)
        self.save()

    def set_recent_files_enabled(self, enabled: bool) -> None:
        self._recent_files_enabled = bool(enabled)
        if not self._recent_files_enabled:
            self._recent_files = []
        self.save()

    def set_explain_mode_enabled(self, enabled: bool) -> None:
        self._explain_mode_enabled = bool(enabled)
        self.save()

    def remember_recent_file(self, path: Path) -> None:
        if not self._recent_files_enabled:
            return
        text = str(path.resolve())
        self._recent_files = [existing for existing in self._recent_files if existing != text]
        self._recent_files.insert(0, text)
        self._recent_files = self._recent_files[:5]
        self.save()

    def save(self) -> None:
        self._settings_store.save(
            {
                "explain_mode_enabled": self._explain_mode_enabled,
                "recent_files_enabled": self._recent_files_enabled,
                "recent_files": list(self._recent_files),
                "reduce_effects": self._reduce_effects,
            }
        )
