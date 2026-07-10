# Semantic Profiling and Project-Local Recommendation Memory Design

Date: 2026-07-10

Status: Approved in design review; written specification awaiting owner review

## 1. Purpose

Modori currently recommends analyses using deterministic heuristics over variable
metadata, column names, cardinality, repeated-measure naming patterns, and safe data
shape checks. That is useful, but it cannot reliably distinguish administrative
columns from research variables, infer survey-item relationships from table context,
or remember a user's confirmed study facts inside a project.

This design adds a semantic evidence layer between `Dataset` and
`RecommendationService`. Its purpose is to improve recommendation validity without
weakening calculation correctness, silently curating data, or requiring a novice user
to make statistical decisions.

The feature is valuable only if a locked benchmark demonstrates material improvement.
If the semantic layer or an optional local SLM does not improve the pre-registered
metrics, that layer is not shipped.

## 2. Current Product Baseline

Verified current behavior:

- `src/modori/table_io.py` detects table layout, fingerprints schemas, bounds previews,
  and supports explicit import-time column selection.
- `src/modori/core/model.py::Dataset` contains the pandas frame and aligned variable
  metadata.
- `src/modori/recommendations.py::RecommendationService` is deterministic and has no
  project memory or model dependency.
- `src/modori/analysis_catalog.py` caps each module at strong, candidate, caution-only,
  manual-only, or never-recommend status.
- `src/modori/ui/recommendation_controller.py` requires an explicit user run action.
- The statistics pipeline remains deterministic and independently validated. R,
  jamovi, and reference fixtures are QA anchors, not runtime engines.
- `src/modori/ui/security.py` and `tests/ui/test_security_privacy.py` enforce the
  current local-only UI boundary and reject runtime network imports or remote QML
  assets.

The current recommendation layer can propose executable candidates. It does not prove
research-design validity, infer intent reliably from data alone, or achieve a measured
80 percent recommendation-accuracy claim.

## 3. Product Decision

Adopt a hybrid, evidence-gated architecture:

1. Deterministic profiling produces reproducible observations.
2. Deterministic context rules produce explainable hypotheses.
3. An optional local SLM may produce additional typed hypotheses.
4. A resolver preserves evidence, counterevidence, conflict, and uncertainty.
5. A novice-facing clarification planner asks only decision-changing questions.
6. Project-local memory stores confirmed facts and reversible decisions.
7. The existing analysis catalog and run validators retain final authority.

The SLM is neither required nor assumed to be beneficial. It is a separately gated
research track. Modori ships the deterministic semantic layer without an SLM if that
is the best validated product.

### Rejected alternatives

#### Deterministic rules only as the permanent endpoint

This is safe and reproducible but has limited ability to understand mixed-language
labels, unusual item naming, or relationships whose meaning depends on neighboring
columns.

#### Model-first semantic interpretation

This offers broader language coverage but makes uncalibrated, version-dependent model
output the system's source of truth. It also creates unnecessary prompt-injection,
privacy, supply-chain, and resource risks. It is rejected.

#### Cross-project or account-level learning

This can propagate a wrong decision or sensitive study concept into unrelated work. It
is outside V1. V1 memory is project-local only.

## 4. Hard Invariants

These rules are release-blocking:

1. Recommendation generation never mutates the dataset or starts an analysis.
2. Inference never removes a row or column. It can only propose a curation action.
3. Only a user-confirmed, replayable import or transformation policy can change data.
4. Model output is always untrusted and cannot write memory, choose a final analysis,
   access files, access the network, or call product tools.
5. The semantic layer never computes statistics for result reporting.
6. The analysis catalog and existing run validators cannot be bypassed.
7. Unknown, conflicting, stale, unsupported, or out-of-distribution cases abstain.
8. Original free text, model prompts, and representative text samples are not stored in
   semantic memory or diagnostics.
9. No semantic fact is reused across projects.
10. A damaged semantic context cannot prevent the calculation pipeline from opening.
11. Every active claim has a source, version, scope, and invalidation rule.
12. A novice user confirms domain facts and research intent, not statistical jargon.

## 5. Architecture

```mermaid
flowchart TD
    A["Local CSV Excel SAV or project"] --> B["Existing import and project loader"]
    B --> C["Read-only Dataset"]
    C --> D["Deterministic structural profiler"]
    C --> E["Bounded context observer"]
    D --> F["Semantic evidence profile"]
    E --> F
    F --> G["Deterministic context rules"]
    F --> H["Optional local SLM adapter"]
    G --> I["Evidence resolver"]
    H --> I
    J["Project-local decision log"] --> I
    I --> K{"Decision-changing ambiguity"}
    K -->|yes| L["Plain-language clarification"]
    L --> J
    K -->|no| M["Recommendation candidates"]
    J --> M
    M --> N["Catalog and safety gate"]
    N -->|reject| O["Question caution or abstention"]
    N -->|pass| P["Recommendation and reason"]
    P --> Q["Explicit user run action"]
    Q --> R["Existing validated statistics pipeline"]
```

### Authority matrix

| Component | May observe | May infer | May persist | May mutate data | May execute analysis |
| --- | --- | --- | --- | --- | --- |
| Structural profiler | Yes | No | Reproducible observations | No | No |
| Context rules | Yes | Yes | Versioned hypotheses | No | No |
| Local SLM | Bounded input only | Yes | No direct persistence | No | No |
| Evidence resolver | Claims and conflicts | Resolve status | Materialized claim view | No | No |
| Clarification planner | Unresolved claims | Question priority | No | No | No |
| Decision log | User answer | No | Append-only events | No | No |
| Recommendation service | Resolved context | Candidate ranking | No | No | No |
| Import/transform command | Confirmed policy | No | Pipeline step | Yes, transactionally | No |
| Run validator and pipeline | Current dataset/config | Eligibility only | Results/provenance | Existing step semantics | Yes |

## 6. Project and Data Contracts

### ProjectDocument

Semantic memory does not belong in `Dataset`, `Variable`, or analysis `Step.params`.
Introduce a project-level wrapper above `Pipeline`:

```json
{
  "project_schema_version": 2,
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "pipeline": {
    "source_dataset": {},
    "steps": []
  },
  "semantic_context": {
    "schema_version": 1,
    "source_schema_fingerprint": "sha256:64-hex-digest",
    "dataset_fingerprint": "sha256:64-hex-digest",
    "profile_version": "profile-v1",
    "rule_version": "rules-v1",
    "model_version": null,
    "claims": [],
    "decision_events": []
  }
}
```

Compatibility rules:

- Existing `{source_dataset, steps}` pipeline JSON loads as a legacy project with an
  empty semantic context.
- Invalid or unsupported semantic context is quarantined while the pipeline opens in
  no-memory mode with a visible warning.
- Third-party project claims do not arrive with local `user_confirmed` authority. They
  are imported as untrusted assertions pending explicit review.
- Semantic schemas contain no filesystem paths, URLs, commands, executable actions, or
  arbitrary extension objects.
- Limits apply before object creation: 16 MiB semantic-context JSON, 10,000 claims,
  10,000 decision events, 20 evidence/counterevidence entries per claim, 512 Unicode
  characters per ordinary string, and maximum nesting depth 8. Exceeding a limit
  quarantines the semantic context; the loader does not truncate it into a potentially
  different meaning.

### Identity and fingerprints

The design uses separate identities for source layout and current analytical data:

- `source_schema_fingerprint` reuses the existing import contract over source type,
  selected sheet/layout, canonical source columns, and their order.
- `dataset_fingerprint` binds the profile to `Pipeline.current_dataset`, not only the
  imported source. It hashes the ordered schema, row count, variable metadata,
  normalized missing masks, and typed values in row order.
- Canonical hashing normalizes text to Unicode NFC, represents missing values with one
  explicit marker, and uses stable typed numeric/date encodings rather than locale
  formatting.
- A source column identity includes project ID, source schema fingerprint, canonical
  key, ordinal position, and source-label hash.
- A derived column identity additionally includes its `origin_step_id` and the
  deterministic transformation provenance.

Any row reorder changes `dataset_fingerprint` and forces regeneration. If row order is
irrelevant, the regenerated semantic claims should be equivalent; metamorphic tests
verify that property. Distribution signatures may diagnose drift but are never used to
fuzzily reattach memory.

User-confirmed facts do not automatically transfer from a source column to a derived
column. A transformation may emit a new semantic claim only when its contract proves
the relationship, such as an explicitly composed scale. Otherwise the derived column
requires independent profiling or confirmation.

### Semantic evidence model

```mermaid
classDiagram
    class ProjectSemanticContext {
        schema_version
        project_id
        source_schema_fingerprint
        dataset_fingerprint
        profile_version
        rule_version
        model_version
    }
    class DatasetProfile {
        row_count
        column_count
        layout_observations
        row_profiles
        column_profiles
        relation_profiles
        study_facts
    }
    class ColumnProfile {
        column_identity
        physical_observations
        measurement_evidence
        missingness
        cardinality
        distribution_summary
        privacy_flags
    }
    class SemanticClaim {
        claim_id
        subject
        predicate
        value
        status
        origin
        evidence
        counterevidence
        scope
        invalidation_rule
    }
    class DecisionEvent {
        event_id
        question_id
        answer
        affected_claims
        actor
        timestamp
        reverses_event_id
    }
    ProjectSemanticContext *-- DatasetProfile
    ProjectSemanticContext *-- SemanticClaim
    ProjectSemanticContext *-- DecisionEvent
    DatasetProfile *-- ColumnProfile
```

### Claim statuses

Only these statuses are valid:

- `observed`: a reproducible physical or statistical observation.
- `inferred`: a rule or model hypothesis.
- `user_confirmed`: a user-confirmed study fact or intent.
- `rejected`: explicitly rejected or contradicted.
- `stale`: no longer applicable after source, schema, rule, or version change.

Origin and status are separate. For example, an SAV file declaring a variable ordinal
is recorded as the observation "source metadata declares ordinal," not as an
unconditionally true ordinal classification. A user correction can therefore coexist
with the source declaration without rewriting history.

### Example claim

```json
{
  "claim_id": "claim-js3-item-group",
  "subject": "column:JS3",
  "predicate": "member_of_item_group",
  "value": "group:JS",
  "status": "inferred",
  "origin": "deterministic_rule:item-prefix-v1",
  "evidence": [
    "numeric values in range 1..5",
    "JS1 through JS5 share prefix and response domain"
  ],
  "counterevidence": [
    "reverse-scoring status is unknown"
  ],
  "scope": "project",
  "invalidation_rule": "stale_on_schema_or_response_domain_change"
}
```

## 7. Profiling and Semantic Compression

The product does not generate a prose summary as its primary memory. It creates a
typed evidence profile that keeps facts, hypotheses, counterevidence, and user
confirmation separate.

### Full deterministic observations

For every imported column, compute reproducible features as applicable:

- physical dtype and parseability;
- row count, non-missing count, missing ratio, and declared missing codes;
- unique count, dominant-value ratio, and constant/near-constant status;
- finite-value status and numeric range/quantiles;
- integer-like, binary, bounded ordinal, date-like, identifier-like, and free-text
  indicators;
- source name, source label, value-label availability, and source-declared measure;
- normalized-name tokens and adjacent-column position;
- response-domain compatibility with neighboring columns;
- repeated prefix/suffix, numbered item, timepoint, code-label, and derived-column
  relationships.

Row observations include blank, repeated-header, metadata, aggregate/subtotal,
duplicate, malformed-width, and ordinary observation candidates. Detection never
implies deletion.

### Semantic role vocabulary

V1 supports a bounded product vocabulary rather than arbitrary ontology generation:

- identifier;
- grouping variable;
- outcome candidate;
- predictor candidate;
- covariate candidate;
- survey item;
- item group;
- timepoint/repeated measure;
- weight;
- cluster/stratum identifier;
- date/time;
- code column and label companion;
- administrative note;
- free text;
- missing-value marker;
- unknown.

Survey question intent, response domain, valid versus missing values, measurement
level, and item grouping follow a deliberately small subset of DDI concepts. Modori
does not implement the full DDI standard.

### Bounded context input

- Column names and source labels are always available to deterministic rules.
- Numeric columns provide summaries, not raw value lists, to the model adapter.
- A non-free-text column is low-cardinality for model input only when it has at most 20
  distinct non-missing values. It may provide the eight most frequent ephemeral labels,
  ordered by descending frequency and canonical text, after identifier/name-like and
  PII-pattern screening.
- Each ephemeral label is capped at 80 Unicode characters.
- Free-text columns provide only language, length, repetition, format, and privacy-risk
  features by default; their raw cell contents are not sent to the model adapter.
- PII-like values are never passed to the model adapter.
- The adapter receives no source path, project path, row index, user name, report path,
  or object capable of reading additional data.
- Ephemeral samples are discarded after inference and never enter the project file,
  logs, exception text, or diagnostic bundles.

The model adapter processes bounded column batches. Exact token, memory, and wall-time
limits are declared by the selected runtime's release-controlled capability manifest,
which pins the runtime and weight hashes. The SLM feature remains disabled until that
runtime-specific manifest and resource test pass. This gate intentionally prevents an
adapter from acquiring implicit resource defaults during implementation.

## 8. Optional Local SLM Contract

The SLM receives a typed `SemanticInferenceInput` and may return only a typed
`SemanticInferenceOutput`.

Allowed output:

- proposed semantic role claims;
- proposed inter-column relationship claims;
- evidence references to supplied profile fields;
- counterevidence and an explicit unknown state;
- candidate clarification facts, not final user-facing wording.

Forbidden output or behavior:

- analysis recommendation or execution command;
- row/column exclusion command;
- direct decision-log or project write;
- filesystem path, URL, shell command, code, or arbitrary nested payload;
- network access, telemetry, model download, plugin call, or product tool call;
- unbounded natural-language reasoning stored as project state.

Controls:

- strict schema validation and unknown-key rejection;
- input/output byte and item-count limits;
- timeout and cancellation;
- runtime and weight version/hash in provenance;
- malformed, conflicting, or unsupported output discarded as a whole transaction;
- deterministic semantic fallback when unavailable or rejected;
- no automatic retry loop that can freeze the UI;
- no raw prompt or completion logging.

Indirect prompt injection remains possible at the model-output level. The design
contains its impact by ensuring that a compromised model can emit only an untrusted
hypothesis that still faces schema, evidence, conflict, policy, and run validation.

## 9. Evidence Resolution and Memory

### Resolution rules

1. Reproducible physical observations cannot be overwritten.
2. Source metadata, rules, models, and users can make conflicting semantic claims; the
   resolver preserves all origins.
3. A current user-confirmed domain fact outranks a model or rule hypothesis, but cannot
   override a contradictory physical observation.
4. Imported third-party confirmations are untrusted until locally reviewed.
5. Stale claims never participate in recommendation ranking.
6. Unresolved conflicts block strong recommendation and can trigger one clarification.
7. No confidence number combines incomparable evidence sources before calibration.

### Decision log

- User decisions are append-only events.
- Undo creates a reversal event instead of deleting history.
- The active claim set is a materialized view rebuilt from valid events.
- A user-authored concept or scale label of at most 120 Unicode characters may be
  stored as explicit project metadata after a PII-pattern warning; it is marked
  user-authored and is never confused with source text or model output.
- New project/session creation clears the active project context.
- No global cache may contain semantic claims or user answers.
- Cache keys include project ID, source schema fingerprint, current dataset
  fingerprint, profile version, rule version, and model version.

### Invalidation matrix

| Change | Required action |
| --- | --- |
| Cell values change | Recompute distribution, row, and relationship observations; stale dependent hypotheses |
| Included rows/columns change | Recompute dataset fingerprint and all affected claims |
| Column rename or reorder | No fuzzy remap; exact identity review required |
| Source label/value labels change | Recompute semantic and response-domain claims |
| Missing codes or measure metadata change | Recompute all affected eligibility and recommendations |
| Rule/profile version changes | Stale and regenerate inferred claims only |
| Model version or weights change | Stale and regenerate model-origin claims only |
| Analysis catalog changes | Re-run candidate policy and safety evaluation |
| Semantic context is corrupt | Quarantine context; open pipeline in deterministic no-memory mode |

## 10. Curation State Model

"Unnecessary" is analysis-dependent and cannot be a single destructive flag. Every
row and column has three separate states:

1. Retained in the original dataset.
2. Ineligible for automatic recommendation roles.
3. Explicitly excluded by a user-confirmed replayable policy.

An identifier or free-text note is usually state 2, not state 3. An aggregate row is an
exclusion candidate, not an automatic deletion. Existing `ImportSelection` and row
policy remain the authoritative mutation path.

Regression tests must prove that profiling, inference, clarification, memory replay,
and recommendation leave the dataset fingerprint unchanged.

## 11. Novice Clarification Design

The user is not expected to know statistical terminology. The user is authoritative
for study facts and intent; Modori is responsible for mapping them to statistical
roles and checking compatibility.

### Question planner

For each unresolved fact, simulate the permitted answer branches and recompute the
candidate set. Ask only when an answer changes at least one of:

- top recommendation family;
- strong/candidate/caution/abstain status;
- paired versus independent design;
- repeated-measure eligibility;
- data-exclusion decision requiring confirmation;
- causal-language permission.

Rank qualifying questions by risk reduction, then user burden. Ask at most three.
Every question supports `yes`, `no`, and `not sure`; `not sure` never triggers a guessed
answer.

Examples:

- "Does each row describe one person or one observation?"
- "Were the before and after values measured from the same people?"
- "Is 99 a real response, or does it mean no answer?"
- "Are these columns answers to different items from the same questionnaire scale?"
- "Is your main goal to compare groups, describe the data, or examine a relationship?"

Do not ask users to judge normality, homoscedasticity, rank deficiency, numeric
stability, or other conditions the engine can evaluate.

If an answer conflicts with observable data, retain both, explain the conflict in
plain language, and abstain until resolved.

## 12. Recommendation Policy

### Lexicographic decision order

1. The analysis module must be executable and recommendation-eligible.
2. Required roles, measures, and sample/data-shape checks must pass.
3. Required study facts must be observed or confirmed.
4. No blocking conflict or stale dependency may remain.
5. The catalog policy ceiling must permit the proposed level.
6. The analysis family's locked benchmark evidence must permit that level.

A weighted score cannot compensate for a failed earlier condition.

### Recommendation levels

`Strong recommendation` requires all mandatory role/design facts, no blocking
conflicts, a successful run-validator dry check, catalog permission, and a lower 95
percent confidence bound of at least 90 percent precision for that strong family.

`Possible candidate` means the configuration is executable but intent or one important
fact remains uncertain.

`Caution required` applies to high-judgment analyses or explicit catalog limits.
ANCOVA, mediation, and moderated mediation remain caution-only even if a model is
confident.

`Abstain` applies to unsupported, ambiguous, stale, conflicting, out-of-distribution,
or inadequately benchmarked cases.

Tied candidates are shown as alternatives. A default is selected only when the policy
produces a meaningful ordering; arbitrary tie-breaking cannot create apparent Top-1
accuracy.

Internal model probabilities are not shown to users. If a future model emits scores,
they are calibrated per version on the calibration set and used only as one input to
abstention policy.

## 13. Benchmark and Gold Standard

### Case contract

Every benchmark case contains:

- a data file and source-format metadata;
- a study card describing the research question, unit of observation, sampling,
  grouping, time/repetition structure, weights/clusters, variable meanings, and known
  missing codes;
- facts visible from data versus facts available only through clarification;
- one or more acceptable analysis families;
- preferred analysis when preference is methodologically defensible;
- prohibited analyses and the reason;
- required clarification questions;
- expected abstention when the available information is insufficient.

Multiple valid analyses remain multiple gold labels. R and jamovi validate numerical
outputs after selection; they do not define the recommendation gold label.

### Corpus stages

- 150-case pilot corpus: discover taxonomy, ambiguity, and question wording.
- 200-case calibration corpus: set evidence, abstention, and confidence policies.
- At least 800 locked release cases: final evaluation only.

The locked corpus includes clean and messy CSV/XLSX/SAV, Korean/English/mixed labels,
Likert ties, missing codes, wide/long repeated measures, IDs, weights, clusters,
aggregate/footnote rows, multi-row headers, numeric-coded categories, reverse-item
ambiguity, small/imbalanced groups, misleading names, unsupported designs, prompt
injection, PII-like text, schema drift, and same-data/different-question pairs.

Gold labels require two independent statistically qualified reviews followed by
documented adjudication. Published methods and documented public-study designs anchor
the review. Model reviewers may criticize cases but cannot be the sole gold authority.
Until this review exists, Modori may run internal experiments but cannot publish the
80 percent recommendation claim.

### Evaluation tracks

- `cold_start`: data only; evaluate profiling, safe questions, and abstention.
- `clarified`: provide domain answers; evaluate final recommendation.
- `memory_replay`: reopen unchanged and changed projects; evaluate reuse and staleness.
- `adversarial`: evaluate injection, poisoning, privacy, resource, and malformed-output
  containment.

### Ablations

- A: current recommendation rules.
- B: deterministic structural profile.
- C1: B plus deterministic table-context rules.
- C2: C1 plus optional local SLM hypotheses.
- D: the best validated semantic configuration plus confirmed project memory.

All variants run against the same cases and scorer.

### Absolute release gates

- Top-1 accuracy one-sided 95 percent Wilson lower bound >= 0.80.
- Strong-recommendation precision one-sided 95 percent Wilson lower bound >= 0.90.
- Top-3 recall one-sided 95 percent Wilson lower bound >= 0.90.
- Coverage on answerable, supported cases >= 0.70.
- Wrong strong recommendation for a high-risk analysis: zero.
- Unauthorized data mutation, raw-text persistence, stale-memory auto-application, or
  cross-project memory reuse: zero.
- Questions per case: at most three.
- Questions that cannot change recommendation, safety level, or curation decision:
  zero.

With 400 evaluated recommendation decisions, 334 correct decisions (83.5 percent) are
needed for a one-sided 95 percent Wilson lower bound just above 80 percent. With 400
strong decisions, 370 correct decisions (92.5 percent) are needed for the lower bound
to exceed 90 percent.

### Material-benefit gates

The complete semantic configuration must improve Top-1 point accuracy over A by at
least five percentage points with a paired two-sided 95 percent confidence interval
excluding zero, or reduce severity E3/E4 recommendation errors by at least 30 percent
while not reducing Top-1 accuracy, strong precision, or coverage. These criteria are
frozen before the locked set is opened.

C2 is adopted only if it improves C1 by at least three Top-1 percentage points with a
paired two-sided 95 percent confidence interval excluding zero, or reduces E3/E4 errors
by at least 30 percent while Top-1 accuracy and strong precision do not decrease and
coverage decreases by no more than five percentage points. Every absolute release gate
must still pass. If not, the SLM is omitted.

D is adopted only if unchanged-project replay reproduces recommendations exactly,
reduces repeated clarification questions by at least 70 percent, applies stale memory
zero times, and does not reduce any accuracy or safety metric.

Per-family strong recommendation remains disabled when that family lacks enough locked
examples to satisfy its confidence-bound gate, even if the overall system passes.

## 14. Error Cost Policy

| Severity | Example | Release policy |
| --- | --- | --- |
| E1 usability | Unnecessary but safe abstention or extra question | Measured and bounded |
| E2 recoverable | Non-preferred but acceptable candidate shown as possible | Bounded by Top-1/Top-3 metrics |
| E3 major | Wrong role, paired/independent confusion, or stale fact used | Release-blocking until corrected |
| E4 severe | Wrong strong recommendation or high-risk automatic promotion | Zero allowed in locked high-risk cases |
| E5 boundary failure | Silent data mutation, raw-data leak, or cross-project memory | Zero allowed |

Average accuracy or a weighted score cannot compensate for E4 or E5.

## 15. Security and Privacy

The repository-grounded threat model is
`docs/security/TongTong-threat-model.md`.

Primary threat classes:

- indirect prompt injection through table cells;
- imported-project memory poisoning;
- stale/fuzzy memory remapping;
- raw text copied into prompts, logs, or support bundles;
- profiler/model resource exhaustion;
- model runtime or weight tampering;
- inference triggering silent curation;
- project cache isolation failure;
- uncalibrated model or data drift.

Mandatory controls:

- local-only, single-user V1 boundary;
- no cloud call, telemetry, dynamic model download, or shared memory;
- extend no-network architecture tests to the semantic runtime boundary;
- no tools, paths, commands, or direct persistence exposed to the SLM;
- strict input/output schemas and resource budgets;
- pinned runtime and weights with cryptographic hash verification;
- project ID and dataset fingerprint on every cache/memory operation;
- untrusted status for imported semantic claims;
- redacted counters only, never raw prompts/completions in diagnostics;
- adversarial tests mapped to TM-001 through TM-010.

The concrete local model runtime is selected only after C1 exists. The selection must
produce a release-controlled capability manifest covering artifact hashes, license,
supported CPU, RAM/disk requirements, input/output budgets, cancellation, and offline
behavior. The manifest ships inside the release-controlled package; normal application
code cannot replace or download it. C2 remains disabled until this focused
model-runtime review passes.

## 16. Performance, Availability, and Recovery

### Execution model

- Deterministic profiling runs in the existing serialized worker boundary, never on the
  QML/UI thread.
- Profiling covers the full dataset up to the existing untrusted-project limits of
  100,000 rows, 1,000 columns, and 5,000,000 cells.
- A larger trusted dataset may receive a partial profile, but partial status prohibits
  strong recommendation.
- Semantic model inference is asynchronous, cancellable, and bound to the dataset
  fingerprint present when it started.
- Results arriving after a dataset change are discarded.
- Model timeout, resource refusal, missing runtime, or invalid output falls back to the
  deterministic configuration without changing data or memory.
- No automatic retry loop is permitted.

### Transaction and recovery

- Decision events and materialized context are saved atomically.
- A failed write preserves the prior valid project state.
- Corrupt semantic context is quarantined rather than repaired heuristically.
- The project opens with the calculation pipeline and deterministic current-data
  recommendations when memory is unavailable.
- The UI offers undo for the latest decision and clear-project-memory with explicit
  confirmation.
- Clearing semantic memory never removes source data, pipeline steps, or results.

## 17. User Experience Contract

Guided mode displays:

- one recommendation or an explicit abstention;
- recommendation level;
- short plain-language reason;
- unresolved fact when one blocks stronger guidance;
- at most three plain-language questions;
- a visible indication when a project-confirmed fact is being reused;
- controls to inspect, undo, or clear remembered decisions;
- explicit run action.

It does not display model names, token counts, raw probabilities, internal evidence
weights, prompt text, or statistical jargon as a substitute for explanation.

Standard mode may expose a compact evidence trail: observed facts, user-confirmed
facts, unresolved claims, and policy limits. It still cannot bypass safety gates.

No recommendation panel change may automatically alter `ImportSelection`, insert a
transform step, or call `rerun`.

## 18. Component Boundaries

Proposed modules:

- `src/modori/semantic/contracts.py`: immutable typed profile, claim, event, and model
  input/output contracts.
- `src/modori/semantic/profiler.py`: deterministic row, column, relation, and privacy
  observations.
- `src/modori/semantic/context_rules.py`: deterministic semantic hypotheses.
- `src/modori/semantic/resolver.py`: conflict, authority, staleness, and active-claim
  resolution.
- `src/modori/semantic/questions.py`: decision-impact simulation and plain-language
  question templates.
- `src/modori/semantic/memory.py`: project-local append-only events and materialized
  context.
- `src/modori/semantic/model_adapter.py`: optional local SLM boundary; disabled by
  default until its separate gate passes.
- `src/modori/project_document.py`: versioned wrapper and legacy migration above
  `Pipeline`.
- `src/modori/recommendations.py`: consume an optional resolved recommendation context
  while preserving the current dataset-only path.

`Dataset`, statistical `Step` implementations, and result DTOs remain free of model
dependencies. UI code orchestrates services but performs no profiling or statistical
reduction.

## 19. Verification Strategy

### Unit and contract tests

- Every observation is deterministic and serializable.
- Claim schemas reject unknown versions, keys, paths, commands, and oversized values.
- Resolver authority and conflict rules cover every origin/status combination.
- Decision reversal reconstructs the prior active claim set.
- Invalid semantic context leaves pipeline loading available.
- Model adapter malformed output is discarded transactionally.
- Recommendation policies cannot exceed catalog ceilings.

### Metamorphic tests

- Row reorder does not change column semantics where order is irrelevant.
- Column reorder changes physical identity and requires review rather than fuzzy remap.
- Harmless formatting changes preserve normalized evidence while source fingerprints
  record the change.
- Renaming, response-domain change, missing-code change, or column replacement stales
  dependent claims.
- Profiling/recommendation never changes the dataset fingerprint.
- Same data plus different research question can yield different valid recommendations.
- Different projects with identical column names never share confirmations.

### Security and robustness tests

- Direct and indirect prompt-injection strings in names, labels, and cells.
- PII sentinels absent from model input logs, project semantic context, and diagnostics.
- Resource limits for high cardinality, long strings, many columns, and malformed model
  payloads.
- Imported project cannot assert local confirmation, paths, or actions.
- Model hash/version change invalidates model-origin claims.
- No-network architecture scan covers UI and semantic runtime code.

### Benchmark and release tests

- A/B/C1/C2/D paired evaluation on pilot, calibration, then locked corpus.
- Per-analysis-family and per-data-slice metrics, not only aggregate scores.
- Wilson confidence bounds and paired improvement intervals.
- Risk-coverage curve, abstention correctness, question efficiency, and replay benefit.
- Full regular quality gate, slow statistics gate, package checks, packaged launch,
  clean-Windows VM smoke, and external design/code review before release promotion.

## 20. Delivery Sequence

1. Build the case schema, scorer, pilot corpus, and current A baseline before changing
   product recommendations.
2. Implement immutable contracts and B deterministic profiling headlessly.
3. Add resolver, invalidation, question planner, and project document/memory with no
   model dependency.
4. Add C1 deterministic table-context rules and run ablations.
5. Integrate the best deterministic configuration into an experimental UI path.
6. Research and select a local SLM runtime only after C1 is measured.
7. Implement C2 behind a disabled-by-default adapter and security/resource gates.
8. Keep or delete C2 according to the frozen material-benefit criteria.
9. Complete the 800-case locked evaluation and independent statistical review.
10. Run full quality, package, clean-VM, privacy, and threat-model gates.
11. Promote the feature and its public claim only when every absolute gate passes.

No later phase is authorized merely because the earlier code exists. Each phase must
produce its required evidence before the next product exposure.

## 21. Acceptance Criteria

The design is implemented only when all of the following are true:

- Facts, hypotheses, user confirmations, rejection, and staleness are distinct and
  traceable.
- Project memory is local, reversible, isolated, and correctly invalidated.
- No semantic action silently changes data or executes analysis.
- Novice questions ask domain facts in plain language and are limited to three.
- Recommendation ranking obeys hard eligibility and catalog ceilings.
- Model absence or failure preserves deterministic function and project integrity.
- Corrupt memory cannot prevent pipeline access.
- Privacy and prompt-injection controls pass adversarial tests.
- A/B/C1/C2/D evidence identifies which layers actually add value.
- Absolute accuracy, precision, recall, coverage, severe-error, and boundary-failure
  gates pass on the locked corpus.
- Any layer without material measured benefit is removed from the product.
- Public wording remains "analysis candidates based on verified data and study facts"
  until the locked evidence supports a stronger claim.

## 22. References

- DDI Alliance, Variable Value Representation and Question Response Domain:
  https://ddi-lifecycle-documentation.readthedocs.io/en/latest/TechnicalGuide/Value%20Representation%20and%20Response%20Domain.html
- W3C, Model for Tabular Data and Metadata on the Web:
  https://www.w3.org/TR/tabular-data-model/
- W3C, PROV-DM: The PROV Data Model:
  https://www.w3.org/TR/prov-dm/
- Hulsebos et al., Sherlock: A Deep Learning Approach to Semantic Data Type Detection:
  https://arxiv.org/abs/1905.10688
- Zhang et al., SATO: Contextual Semantic Type Detection in Tables:
  https://www.vldb.org/pvldb/vol13/p1835-zhang.pdf
- Suhara et al., Annotating Columns with Pre-trained Language Models (Doduo):
  https://arxiv.org/abs/2104.01785
- El-Yaniv and Wiener, On the Foundations of Noise-Free Selective Classification:
  https://jmlr.csail.mit.edu/papers/v11/el-yaniv10a.html
- Guo et al., On Calibration of Modern Neural Networks:
  https://proceedings.mlr.press/v70/guo17a
- Rabanser et al., Failing Loudly: Detecting Dataset Shift:
  https://papers.neurips.cc/paper/by-source-2019-805
- Gebru et al., Datasheets for Datasets:
  https://arxiv.org/abs/1803.09010
- Pushkarna et al., Data Cards:
  https://arxiv.org/abs/2204.01075
- NIST, AI Risk Management Framework 1.0:
  https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10
- NIST, Generative AI Profile:
  https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- NIST, Privacy Framework:
  https://www.nist.gov/privacy-framework
- Greshake et al., Indirect Prompt Injection in LLM-Integrated Applications:
  https://arxiv.org/abs/2302.12173
- OWASP, LLM Prompt Injection Prevention Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
