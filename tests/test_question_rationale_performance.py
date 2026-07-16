from __future__ import annotations

from statistics import median
import time
import tracemalloc

from modori.research_memory.passport_state import PassportHistory
from modori.research_memory.question_rationale import (
    QuestionRationaleResult,
    QuestionRationaleStatus,
    project_current_question_rationale,
)
from modori.research_os.p1_clarifications import (
    build_p1_clarification_registry,
)
from modori.research_os.passport import ClarifyPayloadV2
from modori.ui.question_rationale_presenter import (
    QuestionRationalePresenter,
    QuestionRationaleView,
)
from tests.research_memory_passport_fixtures import (
    history_with_passport_commit,
)


WARMUP_COUNT = 50
SAMPLE_COUNT = 1_000
P95_LIMIT_NS = 10_000_000
PEAK_LIMIT_BYTES = 512 * 1024


def test_real_p1_question_rationale_resource_bounds() -> None:
    events, artifacts, _request, passport = history_with_passport_commit()
    history = PassportHistory.inspect(events, artifacts)
    registry = build_p1_clarification_registry()
    assert isinstance(passport.clarify, ClarifyPayloadV2)
    assert passport.request_binding_digest is not None
    assert passport.clarification_registry_digest is not None
    assert len(registry.questions) == 15
    assert len(passport.clarify.clarification_plan.evaluations) == 4
    assert registry.digest() == passport.clarification_registry_digest
    presenter = QuestionRationalePresenter()

    def run_once() -> tuple[QuestionRationaleResult, QuestionRationaleView]:
        result = project_current_question_rationale(
            history,
            project_id=passport.envelope.project_id,
            request_binding_digest=passport.request_binding_digest,
            clarification_registry_digest=(
                passport.clarification_registry_digest
            ),
            registry=registry,
        )
        assert result.status is QuestionRationaleStatus.AVAILABLE
        assert result.projection is not None
        assert result.projection.candidate_count == 4
        view = presenter.present(
            result,
            language="ko",
            mode="standard",
        )
        assert view is not None
        return result, view

    for _ in range(WARMUP_COUNT):
        run_once()

    samples: list[int] = []
    for _ in range(SAMPLE_COUNT):
        started = time.perf_counter_ns()
        run_once()
        samples.append(time.perf_counter_ns() - started)

    ordered = sorted(samples)
    median_ns = int(median(ordered))
    p95_ns = ordered[949]
    max_ns = ordered[-1]

    tracemalloc.start()
    tracemalloc.reset_peak()
    run_once()
    _current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    deterministic_representations = {
        repr(run_once()).encode("utf-8") for _ in range(20)
    }

    print(
        "question_rationale_performance",
        "registry_questions=15",
        "evaluated_candidates=4",
        f"warmup={WARMUP_COUNT}",
        f"samples={SAMPLE_COUNT}",
        f"median_ns={median_ns}",
        f"p95_ns={p95_ns}",
        f"max_ns={max_ns}",
        f"peak_bytes={peak_bytes}",
    )
    assert p95_ns <= P95_LIMIT_NS
    assert peak_bytes <= PEAK_LIMIT_BYTES
    assert len(deterministic_representations) == 1
