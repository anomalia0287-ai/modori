# Category Value Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect categorical values that differ only by formatting (`서울` / `서울시 ` / `서울특별시`? — no: only formatting variants; see scope) and offer a one-click, user-accepted unification recorded as a replayable pipeline step. This is item 3 of the semi-automation adoption survey (OpenRefine facet/cluster pattern).

**Architecture:** Deterministic fingerprint clustering in the engine (`src/modori/value_clustering.py`), a new `recode.unify_values` Step with an explicit `{column, mapping}` parameter, and a thin UI surface that shows suggestions and lets the user accept or ignore them. No value is ever changed without explicit acceptance; acceptance adds a Step so the operation is visible, editable, and replayable. No AI/SLM runtime is involved — the project's determinism constraint holds.

**Tech Stack:** Python 3.11+ (stdlib `unicodedata` only for the fingerprint), PySide6/QML, pytest.

---

## Scope Rules (fail-conservative)

V1 clusters only values that are **formatting variants of each other**:

- Fingerprint = NFKC normalize → strip → collapse all internal whitespace → casefold.
- Two values belong to one cluster iff their fingerprints are equal.
- `서울` vs `서울시` vs `서울특별시` are **not** clustered in V1 — they differ semantically, not by formatting. Alias/abbreviation unification requires a curated mapping and is out of scope.
- No phonetic, no edit-distance, no token-reorder pass in V1. Each of those adds false-positive risk; they may come later as clearly-labeled lower-confidence tiers.
- Suggested canonical value = the most frequent variant (ties: first by data order).
- Columns considered: nominal/ordinal (string-typed) columns only, unique-value count ≤ 200.

## Task 1: Engine — fingerprint clustering

**Files:** create `src/modori/value_clustering.py`, `tests/test_value_clustering.py`

- [x] `fingerprint(value: str) -> str` per scope rules.
- [x] `value_clusters(series) -> list[ValueCluster]` where `ValueCluster` has `canonical`, `variants` (with counts), `column`-agnostic; only clusters with ≥ 2 distinct raw variants are returned.
- [x] Deterministic ordering (by total count desc, then canonical).
- [x] Tests: whitespace/width/case variants cluster; semantically distinct values do not; empty/NaN excluded; 200-unique cap respected.

## Task 2: Pipeline — unify step

**Files:** `src/modori/steps/data_prep.py` (or new module), `tests/test_data_prep_steps.py`

- [x] `UnifyValuesStep` (`step_type = "recode.unify_values"`), params `{column: str, mapping: {raw: canonical}, suffix}`.
- [x] Architecture note: the pipeline enforces unique writes across steps, so unification writes a new `{column}{suffix}` column (default `_정리`) like `RecodeReverseStep` — the original column is never mutated.
- [x] Applies exact-match replacement only; unknown raw values pass through unchanged; note records replaced counts.
- [x] Replay-safe: same params on same data → same result; covered by a reproducibility test.

## Task 3: UI service + controller

**Files:** `src/modori/ui/…`, `tests/ui/…`

- [x] Engine-side suggestion payload for the active dataset's eligible columns (thin shell: UI receives plain dicts).
- [x] Controller: `valueUnificationSuggestions` property + `acceptValueUnification(column)` slot that appends the Step and reruns.
- [x] Tests: suggestion surfaces after import; accept adds exactly one step; ignore leaves data untouched.

## Task 4: QML surface

- [x] Suggestion chip/panel in the data/variable view: "'지역' 열에서 표기만 다른 값 2묶음 감지 — 통일할 수 있습니다", with variant preview before accepting.
- [x] String catalog + visual contract guards green.

## Task 5: Gate and evidence

- [x] Full default gate green; update `docs/qa/public-data-format-coverage.md` if aggregate/unification interplay changes warnings.

## Explicit Non-Goals

- Automatic application of any unification.
- Alias/abbreviation dictionaries (시도명 축약 등) — separate, curated-data decision.
- Edit-distance or phonetic clustering.
