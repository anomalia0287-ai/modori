# Research OS × Royal Blue Functional Integration Design

**Date:** 2026-07-19

**Status:** Approved for implementation under the delegated fixed scope

**Working branch:** `codex/research-os-functional-usability`

**Research OS baseline:** `eaa0e802a0c64f6619297432f129be4d198a79ea`

**Royal Blue tip:** `7a1ec2fd79ec4b8cf81c9d9008f7699a98124e2e`

**Shared ancestor:** `ca40471297da5f69e90c4519a28ecf0864fd1c08`

## 1. Decision

Integrate the seven Royal Blue commits in their original order with `cherry-pick
-x`. Resolve every overlap as a semantic union whose authority order is:

1. current Research OS safety, provenance, and manual-execution contracts;
2. Royal Blue bilingual entry/workspace presentation contracts;
3. the pre-existing legacy manual-analysis surface, kept separate from Research OS.

No blanket `ours`/`theirs`, whole-file replacement, or deletion of current
Research OS behavior is permitted. UI-only paths may retain their source blob when
the path is genuinely absent from the Research OS delta, but shared paths require
path-specific review recorded in the conflict ledger.

## 2. Independently Verified Baseline

- The working tree started clean at the exact required baseline.
- `src/modori/research_os/` and `src/modori/research_memory/` exist.
- The handoff file on disk and at handoff commit `46686563...` have the same blob,
  `158beb0ca8d2ec02c439f7c3ca5d09ae82dc34af`.
- The seven Royal Blue commits are a linear chain.
- The Research OS/Memory focused baseline passed: `521 passed`.
- The live Research UI focused baseline passed its non-gallery run: `191 passed`.
- The complete production QML research-flow gallery passed outside the sandbox ACL
  boundary: `10 passed`.
- The Research OS and Royal Blue branches both changed 25 paths from their shared
  ancestor. Twelve produce textual conflicts in a three-way preview; thirteen merge
  textually but still require semantic review.

The machine-readable path ledger is
`docs/qa/research-os-royal-blue-functional-integration-ledger.json`.

## 3. Non-Negotiable Product Invariants

### 3.1 Recommendation and calculation are different authorities

- Calculation executability cannot upgrade recommendation validity.
- Every Research OS candidate remains `EXPERIMENTAL`.
- Clarification and abstention remain reachable outcomes.
- Legacy heuristic candidates remain visibly and structurally separate from
  passport-backed Research OS candidates.
- A recommendation string alone is never provenance.

### 3.2 Manual execution boundary

The only accepted Research OS execution sequence is:

`Select task → clarify/abstain → select candidate → Prepare → review exact roles and parameters → Confirm configuration → separate Run`

Prepare and Confirm may mutate configuration only through the passport-bound
preparation path. Neither operation may run statistics. Run remains an explicit,
separate action.

### 3.3 Durable evidence boundary

- The initial request and each clarification answer are committed before any
  durable successor is displayed.
- Displayed Research OS candidates must descend from the active committed V2
  passport and the exact planner trace.
- Imported assertions cannot become local user authority without a local event.
- Dataset or schema fingerprint drift forces replan; fuzzy reuse is forbidden.
- Retraction and recovery states cannot silently regain authority.

### 3.4 Local-only and deterministic boundary

- No generative model, SLM, cloud transfer, telemetry, or remote route is added.
- Validation and preflight remain deterministic and fail closed.
- Raw source cells remain immutable through the research flow. Metadata and
  transformations remain explicit Step-backed operations.

## 4. Commit Integration Order

1. `55fe9791d2b38de6b1de93ba99ad8f0b417015fc` — bilingual entry design
2. `11a1280fa0d4ef9063401a3d9b25e814d81a2708` — bilingual entry plan
3. `64801e66cce82063f0cc68c978c27e4b6fa80ac6` — bilingual entry implementation
4. `847c09505c655a4b36bf5e36af511a7f1fac4413` — Royal Blue workspace design
5. `bca88558818096ef258a635146e920633a6dff7a` — Royal Blue workspace plan
6. `9db213cf8c13713608fb8e98aabb44447057be50` — Royal Blue workspace implementation
7. `7a1ec2fd79ec4b8cf81c9d9008f7699a98124e2e` — variable editor/entry refinement

Documentation commits are preserved in sequence. Each implementation commit gets
its own semantic conflict resolution and focused verification so failures retain a
specific source.

## 5. Shared-Path Resolution Design

### 5.1 Python authority paths

#### `src/modori/app.py`

Keep the current engine-smoke success predicate, including the rerun result and
`.ok` check. Add the Royal Blue application language property, text lookup, and
localization bootstrap without weakening startup or smoke behavior.

#### `src/modori/ui/controller.py`

Retain the current ResearchFlow controller, passport-bound preparation editor,
report-export mixin, shared worker, pipeline-version invalidation, mode adoption,
and selection provenance. Add the Royal Blue localization mixin and localized
models/results/import feedback. A UI language change must also re-present the live
Research OS state in the selected language without writing a new ledger event or
changing passport content.

#### `src/modori/ui/recommendation_controller.py`

The current explicit recommendation-preparation state is authoritative. The Royal
Blue English title/reason formatting may be ported onto the current DTO. The removed
`default_candidate`, `level`, automatic default selection, and immediate execution
APIs must not return.

#### String and localization modules

Royal Blue may split the general Korean/English catalog into `strings.py` and
`strings_en.py`. The existing Research OS KO/EN catalog remains complete. Catalog
tests must prove key parity. A language toggle changes presentation only; it does
not rewrite a committed request's language or create false provenance.

### 5.2 QML authority paths

#### `GuideRail.qml`

Preserve the live `ResearchFlowPanel` and the separate collapsed legacy candidate
surface. Port Royal Blue labels, spacing, typography, colors, and locale bindings
around that structure. Never replace the file with the Royal Blue ancestor, because
that would remove live multi-round Research OS.

#### `PipelineRail.qml` and `WorkScreen.qml`

Preserve the current pipeline/run/report command topology and Research OS mode
links. Apply Royal Blue workspace hierarchy and bilingual presentation without
coalescing Prepare, Confirm, and Run.

#### `Theme.qml` and `AppButton.qml`

Apply Royal Blue tokens and control states while preserving the later Research OS
accessibility fixes:

- warning role `#865F1B` unless fresh measured contrast evidence proves a change;
- primary active-focus border uses `onBrand`;
- non-primary active focus uses `focusRing`;
- warning and danger remain distinct semantic roles;
- accessible names, keyboard focus, hover, disabled, pressed, and reduced-motion
  contracts remain test-covered.

#### Data grid and variable editor

Apply Royal Blue visual refinements while retaining variable keys and measurement
values as machine roles. Metadata changes remain Step-backed and cannot become
unlimited direct cell editing.

### 5.3 Test paths

Shared tests are assertion unions. A passing merge cannot be obtained by deleting
current Research OS assertions or by weakening exact strings, state reachability,
focus, provenance, or manual-run boundaries. Conflicting assertions must be
resolved by identifying the product contract they represent and recording the
decision in the ledger.

## 6. Language Re-Presentation Contract

The UI has two kinds of language-bearing data:

1. shell and legacy UI strings, selected by `uiLanguage`;
2. Research OS view models derived from either transient state or a durable record.

The integration adds a closed `ko|en` presentation switch for the second kind.
Changing language:

- rebuilds transient or durable view models from already-held typed state;
- preserves the active passport digest, task/project identity, committed sequence,
  candidate capability, selected question, and preparation digest;
- emits UI state change signals;
- does not call the coordinator, append an event, rerun planning, or mutate the
  pipeline;
- is rejected while an unsafe or unrepresentable state would be fabricated rather
  than translated.

## 7. Provenance Audit Model

The post-integration audit must distinguish two sources.

### Passport-backed Research OS

`ResearchFlowPanel → ResearchFlowController → ResearchFlowRuntime → task session/coordinator → committed DurableDecision/V2 passport → presenter → candidate card`

The audit must inspect the task-local ledger and assert the displayed passport
digest and committed sequence match the active record.

### Legacy heuristic guidance

`RecommendationControllerMixin → deterministic heuristic recommendation state → collapsed legacy candidate UI`

This path may be useful guidance, but it cannot display passport/ledger evidence or
be treated as a Research OS decision.

## 8. End-to-End Novice Audit

Use one synthetic, local, noncausal task whose expected P1 route is known. Exercise
the production UI and controller path:

1. open/import data;
2. inspect variable metadata and meaning;
3. select a research task;
4. answer bounded clarification, including not-sure where relevant;
5. observe recommend, clarify, or abstain without hidden promotion;
6. review exact roles and parameters;
7. Prepare;
8. Confirm configuration;
9. invoke separate Run;
10. inspect result and evidence/provenance;
11. export Word;
12. provoke and recover from at least one stale-data or invalid-input condition.

Evidence must include controller/QML assertions, task-ledger inspection, pipeline
step/run counts, output-file existence and content checks, and recovery state.

## 9. Minimal Missing-Gate Decision Rule

Do not select a feature because it was named in the handoff. After the audit, rank
gaps by whether they permit a novice to create false authority, run the wrong
configuration, or lose recovery.

A gate is implemented only if all are true:

1. the audit reproduces the gap through the production path;
2. an existing deterministic contract cannot already block it;
3. the fix is smaller than expanding the analysis method space;
4. the fix preserves abstention and manual Run;
5. authority is tied to an explicit local user action and exact current dataset
   identity;
6. RED tests fail for the missing behavior before production code changes.

The current leading hypothesis is a Variable Meaning Gate because free-text role
IDs become `Fact.user_confirmed` without a separate visible meaning review. This is
an audit hypothesis, not an implementation decision.

## 10. Verification and Stop Conditions

After each implementation cherry-pick, run its focused UI tests plus Research OS
boundary tests. After all seven commits, run:

- localization/catalog tests;
- current and Royal Blue QML contract tests;
- Research OS controller/presenter/preparation/ledger tests;
- real QML runtime and visual-gallery tests;
- end-to-end novice audit tests;
- full repository test suite;
- clean-status and commit/order/hash checks.

Stop and diagnose before continuing if any change:

- makes Run reachable from Prepare/Confirm without a separate user action;
- introduces a default/strong recommendation or hides abstention;
- displays uncommitted or legacy evidence as passport-backed;
- changes the dataset fingerprint without replan;
- requires cloud/model/telemetry behavior;
- removes a current Research OS test to make Royal Blue pass.

No push, merge, release artifact replacement, license/README/Devpost change, or
release decision belongs to this work.
