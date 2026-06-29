from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from modori.ui.service_contracts import PipelineStateOps


RunStatusValue = Literal["empty", "ready", "running", "error"]


@dataclass
class UiPipelineState:
    pipeline_version: int = 0
    status: RunStatusValue = "empty"
    stale: bool = False
    steps_model: list[object] = field(default_factory=list)
    step_chain_text: str = ""

    @classmethod
    def initial(
        cls,
        pipeline_ops: PipelineStateOps,
        *,
        status: RunStatusValue,
    ) -> UiPipelineState:
        state = cls(status=status)
        state.sync_steps(pipeline_ops)
        return state

    def sync_steps(
        self,
        pipeline_ops: PipelineStateOps,
        fallback: list[object] | None = None,
    ) -> None:
        self.steps_model = pipeline_ops.steps(fallback)
        self.step_chain_text = pipeline_ops.step_chain_text(self.steps_model)

    def mark_step_changed(
        self,
        pipeline_ops: PipelineStateOps,
        *,
        fallback: list[object] | None = None,
    ) -> None:
        self.pipeline_version += 1
        self.stale = True
        self.status = "ready"
        self.sync_steps(pipeline_ops, fallback)

    def mark_pipeline_replaced(self, pipeline_ops: PipelineStateOps) -> None:
        self.pipeline_version += 1
        self.stale = True
        self.status = "ready"
        self.sync_steps(pipeline_ops)

    def mark_running(self) -> None:
        self.status = "running"

    def mark_error(self) -> None:
        self.status = "error"
        self.stale = True

    def mark_ready_fresh(self) -> None:
        self.status = "ready"
        self.stale = False

    def mark_ready_unless_empty(self) -> None:
        if self.status != "empty":
            self.status = "ready"
