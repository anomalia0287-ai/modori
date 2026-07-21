# Royal Blue workspace design QA

**Comparison Target**

- Source visual truth, structure: `docs/design-audit/2026-07-17-aurora-glass-final/work-manual-top.png`
- Source visual truth, palette: `docs/design-audit/2026-07-19-royal-blue-entry/ko-casual.png`
- Primary implementation screenshot: `docs/design-audit/2026-07-19-royal-blue-workspace/en-casual.png`
- Viewport: 1366 x 768 logical pixels, native Windows/D3D11 rendering
- States: Korean and English; Casual and Pro; keyboard focus in both languages
- State constraint: the work-screen source supplies the three-column structural truth, while the entry-screen source supplies the approved Royal Blue and ivory token truth. They are different routes and data states, so content-row identity and route-specific composition were not treated as pixel-matching targets.

**Full-view Comparison Evidence**

- `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-ko-casual.png`
- `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-ko-pro.png`
- `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-en-casual.png`
- `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-en-pro.png`
- `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-ko-focus.png`
- `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-en-focus.png`

**Focused Region Comparison Evidence**

- Header and mode selection: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-header-mode.png`
- Guide rail and English wrapping: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-guide-rail.png`
- Tabs, data selection, and result surface: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-tabs-actions.png`
- Bottom pipeline rail: `docs/design-audit/2026-07-19-royal-blue-workspace/comparison-pipeline.png`

**Findings**

- No actionable P0, P1, or P2 mismatch remains.
- The existing three-column order, panel hierarchy, command routing, data grid, results panel, and bottom pipeline rail remain intact.
- English Casual guidance is fully visible at 1366 x 768. `Other experimental candidates` remains on one line, while the candidate status and reason wrap without clipping.
- Selected modes and tabs use both a Royal Blue tint and a bottom indicator. Keyboard focus on the unselected Variables tab is separately visible while the selected Data tab remains marked.
- The bottom pastel Aurora treatment is absent. The pipeline is flat ivory with a Royal Blue top divider and primary action treatment.

**Required Fidelity Surfaces**

- Fonts and typography: existing Segoe UI hierarchy and uppercase MODORI wordmark are preserved. Native captures show no label truncation, accidental elision, or clipped English guidance at the target viewport.
- Spacing and layout rhythm: the work screen retains header, guide/center/results columns, and bottom pipeline order. English guidance uses a 300 px preferred rail while Korean retains 260 px; this resolves wrapping without changing the 1366 x 768 frame or panel sequence.
- Colors and visual tokens: the workspace maps to `#173B7A`, `#F7F3EA`, `#FFFDF8`, `#2F5DA8`, and `#17233A`. Active tabs, buttons, selections, focus, grid current-cell borders, and running/latest state treatments use Royal Blue roles. Warning and error colors remain unchanged.
- Image quality and asset fidelity: no new bitmap, generated, inline-SVG, or placeholder artwork was introduced. Existing wordmark and icon resources remain sharp in native Windows/D3D11 captures.
- Copy and content: Korean copy is unchanged. English retains the experimental-candidate and no-automatic-execution contract; the only density edit is `Other experimental candidates`, which preserves the action meaning without the redundant `View` prefix.

**Primary Interactions and Runtime Checks**

- Loaded the checked-in `tests/fixtures/psych_bfi.csv` through the real `UiController` data path.
- Switched the real session language state between Korean and English.
- Switched the real mode state between guided/Casual and standard/Pro.
- Applied keyboard focus to the inactive Variables tab and verified a non-color focus indicator.
- Significant QML diagnostics were checked during capture; none were emitted. The known native-style customization message is handled with the same allowlist contract used by the runtime QML suite.

**Comparison History**

- Pass 1 finding [P2 evidence quality]: the focus-state capture targeted the already selected Data tab, so the screenshot did not visibly distinguish focus from selection.
- Fix: changed the deterministic capture target to the inactive Variables tab while keeping Data selected.
- Post-fix evidence: `docs/design-audit/2026-07-19-royal-blue-workspace/ko-focus.png` and `docs/design-audit/2026-07-19-royal-blue-workspace/en-focus.png` show separate Royal Blue underlines for selection and keyboard focus.
- Pass 2 result: no remaining P0/P1/P2 visual, density, copy, or accessibility-state issue at 1366 x 768.

**Implementation Checklist**

- [x] Preserve three-column work structure and route signals.
- [x] Apply ivory canvas/cards and Royal Blue active, primary, selected, and focused states.
- [x] Remove work-screen peach accents and bottom pastel gradient.
- [x] Preserve warning and error semantic colors.
- [x] Resolve English guide wrapping and candidate action clipping.
- [x] Capture Korean/English, Casual/Pro, and keyboard-focus states.
- [x] Compare full views and focused regions against both approved sources.

**Follow-up Polish**

- No P3 polish item is required for this scope.

final result: passed
