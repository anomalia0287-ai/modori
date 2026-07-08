# Modori Analysis Module Contract Design

Date: 2026-07-07

Status: design draft for owner review.

## Purpose

Modori needs a stable contract for independently produced analysis modules.
Future work may happen in separate sessions and worktrees, but every module
must integrate through the same statistical, reporting, recommendation, and UI
boundaries.

This design fixes that boundary before adding more analysis menus. The goal is
not a dynamic third-party plugin system. The goal is a strict internal module
contract that lets separate implementation sessions produce analysis modules
without weakening the replayable pipeline architecture or turning QML into a
statistics layer.

## Current Project Facts

The repository already has the core pieces, but they are spread across several
files:

- `src/modori/core/model.py`: `Step`, `Dataset`, `Variable`, `StepResult`,
  `PipelineContext`.
- `src/modori/results.py`: analysis result dataclasses and `ChartSpec`.
- `src/modori/steps/reporting.py`: `table_for`, `prose_for`, chart rendering,
  and `ReportStep`.
- `src/modori/analysis_catalog.py`: executable/deferred analysis capability
  registry.
- `src/modori/recommendations.py`: current recommendation candidates for
  reliability, comparison, and cautious regression.
- `src/modori/ui/pipeline_ops.py` and `src/modori/ui/results.py`: conversion of
  engine results into UI `DisplayResult` objects.

The contract exists as practice, not as a single module acceptance gate. That is
not strong enough for parallel module production.

## Design Decision

Create a documented and testable Analysis Module Contract v1.

Every new analysis module must ship as a vertical contract bundle:

1. Capability declaration.
2. Step implementation contract.
3. Result DTO contract.
4. Reporting contract.
5. Chart contract.
6. Knowledge/help-key contract.
7. Recommendation contract.
8. UI adapter contract.
9. Verification contract.
10. Release evidence contract, when the module affects packaged or manual QA.

The first pilot module for proving the contract should be `descriptives_table1`.
It is common in social-science reports, relatively low statistical risk, and it
forces the contract to handle mixed variable roles, grouped summaries, missing
case counts, report tables, and safe recommendation behavior.

The pilot must also prove the contract mechanically, not only by reviewer
inspection. Its implementation plan must include a parameterized contract test
harness that inspects registered modules and fails on incomplete specs, missing
schema-version handling, missing reporting/help-key coverage, and missing
verification markers.

## Non-Negotiable Principles

- QML remains a thin shell. QML may collect user intent and render DTOs, but it
  must not calculate statistics, choose a statistical method from raw numbers,
  parse source data, or reformat report numbers.
- Every analysis is a replayable `Step`. No analysis module may mutate the
  source dataset in place.
- Every reported statistic needs a named verification path. Golden/reference
  tests are required before a statistic enters `prose_for`, `table_for`, chart
  data, or Word export.
- Unsupported scope must be explicit. A module that cannot safely handle a
  case must fail closed with a visible reason rather than returning partial
  results.
- Recommendation is stricter than execution. A module may be executable by
  manual selection while still being forbidden for automatic "recommended run".
- Schema evolution is part of replayability. A saved project created with an
  older parameter schema must either migrate through an explicit module-owned
  migration function or fail with an explicit unsupported-version error. Silent
  best-effort loading is not allowed.

## Language Boundary

- Engineering identifiers, module keys, spec labels, code, comments, tests, and
  commit messages are English.
- Product-facing UI strings, report prose, recommendation reasons, and user
  error text are Korean-first.
- English report/prose output may be supported as a secondary language.
- Help-key identifiers are English stable ids; help content is Korean-first
  with English secondary fields where available.

## Capability Contract

Each module declares an `AnalysisModuleSpec` in the capability registry.

The current `AnalysisCapability` registry is not replaced wholesale before the
pilot. The pilot includes the minimum registry evolution needed to support
`AnalysisModuleSpec` fields, including `experimental` status and a migration
path from the current lightweight capability rows. Existing entries may remain
lightweight during the pilot, but the pilot module itself must use the new
spec. Filling every existing module's full spec is a post-pilot migration task,
not a prerequisite for the pilot.

Required fields:

- `key`: stable module key, for example `descriptives_table1`.
- `label`: concise English engineering label.
- `status`: `executable`, `deferred`, or `experimental`.
- `step_type`: producing Step type when executable.
- `result_type`: Result DTO class name when executable.
- `variable_roles`: accepted roles such as outcome, group, item set,
  predictor, within-subject measure, or table variable.
- `supported_measures`: allowed `Measure` values per role.
- `required_preprocessing`: explicit prerequisite steps, if any.
- `unsupported_cases`: fail-closed cases and user-visible reasons.
- `reference_sources`: SPSS, R package/script, published dataset, PROCESS,
  lavaan, or other named reference.
- `recommendation_policy`: `strong`, `candidate`, `caution_only`,
  `manual_only`, or `never`.
- `release_evidence_required`: whether package/VM/manual evidence is required
  before release claims.
- `contract_tests`: names or markers for the tests that prove the module's
  numeric, reporting, recommendation, and UI contract.

Rules:

- `deferred` modules must include an actionable reason and, where appropriate,
  external paths.
- `experimental` modules cannot appear in ordinary UI menus or recommendation
  output.
- `executable` modules cannot be registered without verification tests for all
  reportable statistics.
- The registry must expose an iterable view of module specs so contract tests
  can inspect every registered executable module.

## Step Contract

Every executable module exposes one or more `Step` classes.

Required:

- `step_type`: stable string namespace, for example `stats.descriptives_table1`.
- `params`: JSON-serializable, versioned schema.
- `input_step_ids`: used only for true dependency ordering, not as a hidden
  data channel.
- `reads()`: every dataset column key read by the step.
- `writes()`: `analysis:<step_id>` for analysis steps.
- `metadata_writes()`: only for metadata-editing modules, not ordinary
  analyses.
- `produces_analysis = True` for analysis steps.
- `safe_for_untrusted_project_json`: false unless parameters can be safely
  loaded from an untrusted project file.
- `compute()`: validates all inputs before returning a result.
- `provenance()`: plain audit line suitable for the pipeline rail and release
  evidence.

Parameter schema and migration rules:

- Unknown params are errors, not ignored.
- Required params are explicit.
- Every Step params object must include a schema-version field named
  `schema_version`.
- The Step class owns `CURRENT_SCHEMA_VERSION`.
- The Step class owns `migrate_params(params)` or an equivalent module-owned
  migration hook.
- Loading older params is allowed only through explicit migrations that return
  the current schema shape.
- Loading newer params is rejected with a clear unsupported-version error.
- Loading params without `schema_version` is allowed only for legacy steps that
  the module explicitly recognizes and migrates. New modules may not omit it.
- Defaults are snapshotted into the step at creation time.
- Any policy value that can change a statistic must live in `params`, not global
  mutable settings.
- Variable names are untrusted. Do not build identity or parse formulas by
  concatenating variable names.
- Unknown params remain errors after migration. A migration may consume old
  fields, but the current-version validator must reject unknown current fields.

Failure rules:

- Invalid input raises a clear `ValueError` or returns a controller error before
  computation starts.
- Non-finite numeric output is a failure unless the statistic explicitly
  defines a missing/unavailable state.
- A failed analysis must not return a partially valid result object.

## Result DTO Contract

Each new module result is a frozen dataclass in a module-specific result file.
`src/modori/results.py` may re-export stable public result classes, but new
modules should not add large result definitions directly to that shared file.
This prevents parallel sessions from colliding on the same DTO file.

Required fields:

- Stable identifiers for the analysis variables and role labels.
- `n_total`, `n_obs`, and `n_dropped` whenever missing/exclusion can affect the
  result.
- All reportable statistics as typed fields, not formatted strings.
- `warnings`: user-visible diagnostic warnings.
- `notes` or educational interpretation fields where the result needs
  plain-language explanation.
- `apa_template_id`: stable prose template id, or `None` when the module
  explicitly has no manuscript-style prose.
- `chart_spec`: primary chart, or `None` only if the module explicitly has no
  canonical chart.

Rules:

- Numbers in result DTOs are raw numeric values. Formatting belongs in
  `prose_for`, `table_for`, and report rendering.
- Result DTOs must not contain pandas dataframes, numpy arrays, open file
  handles, or UI objects.
- Ordering must be deterministic. Tables, rows, coefficients, factors, and
  warnings must not depend on dict iteration or source-file incidental order
  unless that order is part of the params.

## Reporting Contract

Every executable module that produces user-facing results must extend:

- `table_for(result)`.
- `prose_for(result, language)`.
- Word export through `ReportStep` when included.

Rules:

- Korean output is primary; English output is secondary when supported.
- Prose pulls every number directly from the result DTO.
- Report text must include the method name, sample size, exclusions, statistic,
  p-value where applicable, effect size or equivalent practical statistic, and
  CI where supported.
- Cross-sectional association or prediction modules must avoid causal wording
  unless a future design adds explicit causal-design metadata.
- Warning text stays near the affected result but must not be mixed into the
  manuscript paragraph unless the module design says so.
- New modules should register reporting handlers through a dispatch registry
  when available. Until that registry exists, any central `table_for` or
  `prose_for` edits must be small dispatch additions only. A module-specific
  helper should own the actual table/prose construction.

## Chart Contract

Each module declares its canonical chart behavior.

Required:

- `ChartSpec.type`.
- data payload schema.
- axes and labels.
- rendering function or explicit "no canonical chart" reason.

Rules:

- Chart data comes from result DTO values or deterministic derived display data.
- Chart rendering lives in Python reporting/chart code, not QML.
- Display PNGs are generated under the app cache; export figures may include
  publication formats where supported.
- Chart failure must not erase an otherwise valid numeric result. It becomes a
  display note unless the chart itself is the result.
- Automated chart tests assert `ChartSpec` type, data payload, labels, and
  render dispatch behavior. Pixel comparison is not required for ordinary
  module tests because it is brittle across graphics backends.

## Knowledge And Help-Key Contract

Each module must define the user-facing terms it introduces.

Required:

- Help keys for result table columns.
- Help keys for method names, test names, diagnostic names, effect-size names,
  and warning concepts.
- Library entries, or documented `needs_review` entries, for new concepts.
- Coverage tests proving displayed user-facing terms resolve.

Rules:

- Internal ids such as step types and template ids are not automatically
  user-facing help terms.
- Citation honesty applies. Unverified citations stay marked as needing review.

## Recommendation Contract

Every module declares whether and how it may appear in "recommended run".

Levels:

- `strong`: safe default when metadata and data shape clearly identify the
  analysis.
- `candidate`: plausible but requires user confirmation.
- `caution_only`: executable only after explicit user review of research intent
  or assumptions.
- `manual_only`: visible in menus, never recommended.
- `never`: hidden or deferred.

Rules:

- A recommendation candidate must explain the reason in Korean.
- Recommendation policy is a maximum allowed level, not the full decision.
  Dataset-specific eligibility is dynamic.
- Each recommended module must provide a module-owned eligibility function or
  strategy object that turns the current dataset/session state into zero or
  more recommendation candidates.
- `RecommendationService` may orchestrate module eligibility providers, but it
  must not accumulate module-specific statistical heuristics in one central
  file.
- Strong recommendations cannot depend on causal assumptions, variable meaning
  that is not in metadata, or arbitrary predictor selection.
- Modules with multiple defensible models must not auto-run as strong
  recommendations.
- Recommendation selection must configure a Step first and run only through the
  existing controller/rerun path.

## UI Adapter Contract

The UI surface for a module is thin and replaceable.

Required:

- Controller command for manual selection, or use of a generic command shape
  once available.
- Display conversion to `DisplayResult`.
- QML controls that gather role selections and policy options only.
- Visible unsupported/error states.

Rules:

- QML must not import statistical libraries, parse raw data files, inspect
  pandas objects, or compute reductions.
- QML must not know result internals beyond display DTO properties.
- Static user-visible strings use the string catalog.
- The module may start headless-only. QML exposure is not required before the
  engine contract is complete.

## Verification Contract

Each executable module must pass these gates before it can be considered ready:

- Contract harness tests over registered module specs.
- Parameter schema tests, including unknown and missing params.
- Parameter migration tests for at least current version, missing version, older
  supported version if any, newer unsupported version, and unknown current
  params.
- Input eligibility tests for every supported and rejected role combination.
- Numeric golden/reference tests for every reported statistic.
- Routing/diagnostic tests when the module makes deterministic choices.
- Finite-output tests for edge cases.
- `reads()` and `writes()` tests.
- Pipeline replay and serialization tests.
- `table_for` and `prose_for` tests in Korean and English where applicable.
- Chart rendering tests for every supported chart type.
- UI thin-shell tests if QML/controller surfaces are added.
- Recommendation tests if the module participates in recommended run.
- Full `scripts/quality_gate.py` before merge to the release lane.
- Package and clean-VM evidence when the module changes packaged runtime,
  payload fixtures, or manual release claims.

The pilot implementation must add the first contract harness. The harness
should inspect every new-style executable `AnalysisModuleSpec` and fail when:

- required spec fields are missing;
- `step_type` has no registered Step class;
- the Step lacks `schema_version` validation/migration coverage;
- reportable result terms lack help-key coverage;
- declared contract test markers do not exist;
- an executable module has no numeric/reference verification marker;
- a recommended module has no module-owned eligibility provider.

## First Pilot Module: `descriptives_table1`

Purpose:

Provide a report-ready descriptive summary and Table 1 surface for imported
survey data. This pilot proves the module contract without starting with a
high-risk inferential model.

Initial scope:

- Continuous/scale variables: n, missing n, mean, SD, median, min, max.
- Nominal/ordinal variables: n, missing n, category counts and percentages.
- Optional grouping variable: grouped summaries by one nominal/ordinal group.
- Report table output suitable for a methods/results section.
- Korean-first plain prose summarizing the table and exclusions.
- Deterministic ordering: variables follow the explicit `params["variables"]`
  order. Category rows follow observed category order for ordered/categorical
  metadata when present; otherwise they use a deterministic display sort defined
  in the module-specific spec.

Explicit V1 exclusions:

- Survey weights.
- Complex samples.
- Multiple imputation.
- Standardized mean differences.
- Automatic "baseline imbalance" claims.
- Causal or treatment-effect language.
- Publication-layout custom table editor.

Recommendation policy:

- `strong` for an imported dataset with at least one usable variable and no
  active analysis.
- `candidate` when a plausible grouping variable exists, because grouping is
  useful but may not match the research design.
- Never infer treatment/control meaning from variable names alone.

Pilot schema:

- `schema_version: 1`
- `variables: list[str]`
- `group: str | None`
- `include_missing_counts: bool`
- `language: "ko" | "en"`

The pilot must include current-version validation and an unsupported newer
version test even if no v0 migration is needed.

Reference and verification:

- Numeric summaries cross-check against pandas/numpy independent calculations.
- Percentages and missing counts pinned by fixed fixtures.
- Grouped output cross-checks each group separately.
- Report prose tests assert no causal wording and includes exclusion counts.

## Parallel Session Integration Rules

Separate sessions may implement modules only after this contract is accepted.

For each module session:

1. Start from this contract and a module-specific design spec.
2. Implement headless engine and verification first.
3. Add reporting and chart integration.
4. Add capability and recommendation rules.
5. Add controller/QML only after the headless contract passes.
6. Merge one module at a time into the integration branch.
7. Run the full quality gate after each merge.

If two modules need to change the same shared contract, stop and revise this
design before implementation continues.

Shared-file rule:

- New module DTOs live in module-specific result files and are re-exported only
  if needed.
- New reporting logic lives in module-specific helpers. Central dispatch files
  may call those helpers but should not hold module-specific table/prose logic.
- New recommendation logic lives in module-owned eligibility providers.
- Any change that requires large edits to `results.py`, `reporting.py`, or
  `recommendations.py` is a contract-design change, not routine module work.

## Explicit Non-Goals

- No third-party plugin marketplace.
- No runtime dynamic module loading.
- No QML-first analysis feature.
- No AI/SLM recommendation or interpretation.
- No automatic exposure of experimental modules.
- No broad refactor of existing completed modules before the first pilot proves
  the contract.

## Acceptance Criteria

This design is accepted when:

- The owner agrees that module work starts with the common contract, not QML.
- The first pilot is `descriptives_table1`.
- Future modules can be assigned to separate sessions using the contract bundle.
- Recommendation levels are treated as stricter than manual execution.
- The design explicitly blocks unsupported or unverified statistics from
  reaching report prose or recommended run.
