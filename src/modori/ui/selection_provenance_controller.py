from __future__ import annotations

from PySide6.QtCore import Slot


class SelectionProvenanceControllerMixin:
    @property
    def selectionProvenance(self) -> str:
        return self._session.selection_provenance

    @Slot(result=bool)
    def markExperimentalCandidateAssisted(self) -> bool:
        self._session.mark_experimental_candidate_assisted()
        self.stateChanged.emit()
        return True

    @Slot(result=bool)
    def clearSelectionProvenance(self) -> bool:
        self._session.clear_selection_provenance()
        self.stateChanged.emit()
        return True
