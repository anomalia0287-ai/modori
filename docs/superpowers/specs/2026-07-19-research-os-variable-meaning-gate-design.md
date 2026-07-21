# Research OS Variable Meaning Gate Design

Date: 2026-07-19

Status: implemented and audited in `ed8bcae6f7452d2713865afc3ebfa98508d3b65b`

## Decision

Add one explicit Variable Meaning Gate between P1 role entry and
`ResearchFlowRuntime.commit_initial`. Entering variable keys prepares an immutable,
local review; it does not create a ledger or a `user_confirmed` Fact. Only the separate
meaning-confirm action may commit the initial request.

## Why this is the minimum gate

The audited UI accepted a valid key and immediately committed it as a confirmed research
role. Later preflight can reject an incompatible measurement level, but it cannot prove
that the user reviewed the variable's label, coding, missing values, or intended role.
The gate closes that authority transition without adding new methods, raw-cell editing,
cloud services, or generative inference.

## Closed review contract

`VariableMeaningReview` is immutable and contains:

- schema/version identity;
- current dataset fingerprint and captured pipeline version;
- the selected P1 task profile;
- one ordered row per selected role-variable pair;
- a canonical SHA-256 review digest.

Each row binds:

- variable key;
- current human-readable label, including an explicit absent state;
- current measurement level;
- current value labels;
- current declared missing codes;
- storage dtype;
- the exact research-task role;
- evidence source `current_dataset_metadata`;
- conceptual-definition and unit status `not_recorded`.

The digest covers every normative field. Duplicate role-variable rows, variables outside
the current dataset, invalid role cardinality, non-NFC text, malformed metadata, or
pipeline drift fail closed.

## State and command flow

```text
intake_roles
  --submit roles--> meaning_reviewing
  --worker returns sealed review--> variable_meaning_review
  --back--> intake_roles
  --confirm meanings--> committing
  --request + passport committed--> clarify_ready | candidate_ready | abstain_ready
```

`meaning_reviewing` is cancellable and performs no ledger write. The review state shows
the exact rows and a 12-character digest only in Pro mode. Korean and English use the
same controller state and record.

## Durable provenance

On meaning confirmation the runtime recaptures the current pipeline, recomputes the
review, and requires byte-for-byte equality with the displayed review. It then allocates
the initial event ID and constructs the request.

Each user-confirmed target-role Fact receives exactly these provenance refs:

1. the real initial request event ID; and
2. `variable-meaning-review:v1:<full-review-digest>`.

The initial event ID is the request component `created_event_ref` and the committed
ledger event identity. The request snapshot stores both refs. The V2 passport's request
binding digest then seals that request. Candidate display remains impossible until the
ledger commit succeeds (commit-before-display).

## UI

The Royal Blue visual system is preserved. The gate uses existing `PearlSurface`,
`StateBadge`, labels, and `AppButton` components. It displays role, key, label,
measurement level, value labels, missing codes, storage type, evidence source, and
explicit “not recorded / not inferred” rows for definition and unit. Confirm is primary;
Back is quiet.

## Safety and non-goals

- local-only and deterministic;
- no model, SLM, network, telemetry, or cloud transfer;
- no candidate, passport, or ledger mutation before explicit confirmation;
- no calculation from role submit or meaning confirm;
- abstention and later clarification remain unchanged;
- no broad definition/unit editor and no raw-cell editing;
- no new statistical method or recommendation-validity claim.

## Acceptance criteria

1. Role submit produces the review state and no ledger path/event/passport.
2. The review exposes every selected role exactly once and reflects current metadata.
3. Back returns to role entry without authority gain.
4. Pipeline or metadata drift invalidates the review and requires replan.
5. Confirm recomputes the review and commits only an exact match.
6. Role Fact refs contain the real committed event ID and the review digest ref.
7. The ledger request snapshot and V2 passport bind those refs.
8. Prepare, Confirm configuration, separate Run, Word export, and recovery still pass.
9. Korean and English QML states load without significant runtime warnings.
