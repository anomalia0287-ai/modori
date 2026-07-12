# Evidence-Carrying Clarification Transition Design

**Date:** 2026-07-12  
**Status:** approved under the user's standing technical-autonomy authorization  
**Branch:** `codex/research-os-contract-design`

## 1. Decision

Modori will not treat a clarification answer as an in-place edit or as sufficient
authority to run an analysis. It will use an **evidence-carrying revision** chain:

```text
clarify passport
  -> clarification answer event
  -> deterministic revision candidate
  -> explicit acceptance certificate when scientific meaning changes
  -> committed canonical spec revision(s)
  -> fresh C1 resolution
  -> new passport carrying the evidence digests
```

The chain is local, content-addressed, deterministic, and authority-free. It records
why a recommendation changed without granting file, network, persistence, tool,
calculation, or execution authority.

This is the next foundation slice. UI rendering, storage, analysis execution, external
route launching, and public recommendation-validity claims remain excluded.

## 2. Why the Existing Foundation Is Insufficient

The current foundation can:

- represent QuestionSpec, EstimandSpec, and StudySpec;
- resolve them through C1;
- return neutral clarification questions; and
- bind a decision into an AnalysisPassport.

It intentionally cannot apply an answer. A naive implementation would introduce four
defects:

1. It could mutate an existing specification and destroy provenance.
2. It could use an estimand-changing answer without a second explicit acceptance.
3. It could apply an answer against a stale passport or replaced dataset.
4. It could carry the new recommendation without carrying the evidence that authorized
   the changed human-owned fact.

The design also closes a subtle lifecycle gap: an estimand draft must never be accepted
by C1 merely because it has the same Python type as an accepted specification.

## 3. Alternatives Considered

### A. Mutate the current specification

Rejected. This is simple but makes correction history unrecoverable, breaks digest
identity, and permits stale UI state to overwrite a newer decision.

### B. Add a mutable `accepted` flag to EstimandSpec

Rejected. Changing the flag changes the meaning of an existing revision in place. It
also invites time-of-check/time-of-use disagreement between the resolver and UI.

### C. Evidence-carrying revision bundle

Selected. The answer is an immutable event. A pure transition constructs a candidate
bound to the exact source passport and component digests. Any bundle that changes an
EstimandSpec requires an acceptance certificate bound to the candidate digest. Only
then does the transition produce a new ResearchRequest. The next passport carries the
evidence references.

This is not a claim of a new cryptographic primitive. It is a product-specific synthesis
of content addressing, append-only decision evidence, atomic revision bundles, and
typestate-like API separation.

## 4. Trust and Threat Boundary

The mechanism protects against stale UI state, accidental mutation, answer/candidate
mix-ups, incomplete multi-spec updates, and silent loss of human-decision provenance.
It is tamper-evident inside the local application workflow.

It is not a digital-signature system and does not defend against an attacker who can
arbitrarily replace the trusted local program or rewrite all local history. No claim of
non-repudiation is permitted.

The SLM, if one is ever adopted, cannot create an answer event, acceptance certificate,
or committed revision. These are user-owned deterministic application events.

## 5. Canonical Contracts

### 5.1 Clarification contract hardening

Before answers can be applied, ClarificationSpec gains the lifecycle, dependency, and
decision-branch metadata required by the approved Research OS design:

```text
ClarificationLifecycle = draft | active | withdrawn

BranchMatchKind = choice_values | empty_variables | nonempty_variables |
                  answered | not_sure

ClarificationBranch:
  branch_id
  match_kind
  choice_values[]
  effects[]  # closed ClarificationTrigger values
```

An active question must cover every registered choice exactly once, cover both empty
and nonempty outcomes for variable-multi questions, cover an answered outcome for
other open answer kinds, and always cover `not_sure`. Dependencies are closed fact
addresses, not free prose. P1 ships only active questions. Draft and withdrawn
questions cannot validate an answer event.

This metadata does not name a method. It makes the claim “this question can change a
decision” auditable instead of relying on its wording.

### 5.2 `AnswerValue`

```text
AnswerValueKind = choice | variables | text | not_sure

AnswerValue:
  kind
  choice_value | null
  variable_ids[]
  text_value | null
```

Exactly one representation is active. `not_sure` carries no value. Variable identifiers
are NFC-normalized, nonblank, unique, and checked against the exact ResearchRequest
variable set. `not_sure` always becomes an unknown fact; it never becomes an inferred
or default answer.

### 5.3 `ClarificationAnswerEvent`

```text
event_id
project_id
event_sequence
source_passport_digest
question_id
question_version
question_digest
fact_address
answer_value
```

The event binds the exact clarification passport and question revision. It contains no
dataset values, free command, path, URL, model output, or execution instruction.

### 5.4 `RevisionCandidate`

The candidate binds:

- project ID;
- source passport digest;
- answer event digest;
- base question, estimand, and study component references;
- the exact current dataset fingerprint;
- zero or one proposed revision of each component;
- remaining inline-question budget;
- whether explicit estimand acceptance is required; and
- a reserved acceptance certificate ID when acceptance is required.

At least one component changes. A changed EstimandSpec always makes the whole bundle
acceptance-required. The bundle commits atomically; a QuestionSpec change and its
dependent EstimandSpec invalidations cannot be split across resolver calls.

The candidate is a proposal, not a ResearchRequest and not an AnalysisPassport. C1
cannot consume it.

### 5.5 `RevisionAcceptanceCertificate`

```text
certificate_id
project_id
event_sequence
candidate_digest
answer_event_digest
accepted_component_digests[]
```

The certificate represents an affirmative local user action. Rejection is recorded as
a separate history event by a future persistence layer and never materializes a
ResearchRequest. The certificate event sequence must be greater than the answer event
sequence.

The accepted component revisions use the certificate ID as their `created_event_ref`.
Changed facts retain the answer event ID in provenance. Thus the final component digest
binds acceptance, while the fact binds the answer that supplied its value.

### 5.6 `DecisionEvidenceRef`

```text
evidence_id
project_id
evidence_kind = clarification_answer | revision_acceptance
event_sequence
evidence_digest
subject_digests[]
```

A committed ResearchRequest carries only these compact references, not a mutable event
store. The next AnalysisPassport copies their evidence digests. Persistence and event
retrieval remain separate future work.

## 6. Answer Validation

An answer is valid only if all of the following hold:

1. The source passport is a `clarify` passport.
2. Its digest equals `source_passport_digest`.
3. The project IDs match.
4. The question ID occurs in the passport's clarify payload.
5. The question version, digest, and fact address match the active registry entry.
6. The answer representation matches AnswerKind.
7. A choice is one of the registered choices.
8. Variable IDs exist in the exact current request and satisfy address-specific
   cardinality.
9. The passport component refs and dataset fingerprint still match the request.
10. The answer event sequence is positive and its event ID is not already present in
    request evidence.

Failure raises a closed transition error and produces no candidate.

## 7. P1 Transition Rules

| Clarification | Direct revision | Dependent action |
| --- | --- | --- |
| research goal | QuestionSpec.research_goal | stale estimand template, claim basis, roles, contrast, effect scale, and association target |
| causal intent | QuestionSpec.causal_intent | stale claim basis when its current meaning may conflict |
| estimand template | EstimandSpec.template | stale claim basis, roles, contrast, effect scale, and association target |
| claim basis | EstimandSpec.claim_basis | none |
| effect scale | EstimandSpec.effect_scale | none |
| association target | EstimandSpec.association_target | none |
| contrast | EstimandSpec.contrast | none |
| outcome/focal predictor/group/repeated role | matching EstimandSpec role | none |
| dependence | StudySpec.dependence_structure | invalidate incompatible repeated-order meaning |
| weight/cluster | matching StudySpec role | none; empty selection is an explicit confirmed absence |
| repeated-measure order | StudySpec.repeated_measure_order | none |

Staling preserves the prior active value and its original provenance through
StaleSnapshot. A non-current dependent fact becomes unknown instead. No lexical or
model guess repairs a stale fact.

Address-specific cardinality:

- outcome, focal predictor, and group: exactly one variable;
- repeated-measure role: zero or at least two variables; empty explicitly means no
  repeated-measure set exists;
- repeated-measure order: at least two variables;
- weight and cluster: zero or more variables;
- ordered variables cannot contain duplicates.

## 8. Atomic Commit and Re-resolution

`ClarificationTransitionService.propose(...)` is pure. It validates and returns a
RevisionCandidate.

`commit_ready(...)` accepts only a candidate with no EstimandSpec revision. It returns
a new ResearchRequest and never mutates the source request.

`commit_accepted(...)` accepts only an acceptance-required candidate and a matching
RevisionAcceptanceCertificate. It returns a new ResearchRequest whose changed
component envelopes use the certificate event ID.

Both paths decrement the inline clarification budget once, preserve the current
dataset fingerprint and surface, append DecisionEvidenceRef values, and validate every
variable reference before returning.

The caller then invokes the existing `resolve()` or `plan()` again. The transition
service never chooses a capability and the resolver never applies an answer.

## 9. Passport Extension

AnalysisPassport gains one metadata-only field:

```text
decision_evidence_digests[]
```

The tuple is ordered, unique, and contains only lowercase SHA-256 digests. Existing
requests legitimately have an empty tuple. A passport for a transition-produced request
must reproduce the request's evidence-digest tuple exactly.

This field is provenance, not authority. It cannot contain event payloads, commands,
paths, URLs, worker tokens, or persistence handles.

## 10. Failure and Recovery Semantics

- stale passport or component mismatch: reject answer and request a fresh plan;
- unknown or withdrawn question: reject without revision;
- invalid variable reference: reject and refresh available variables;
- not_sure: commit unknown, decrement question budget, and re-resolve;
- acceptance missing or mismatched: candidate remains uncommitted;
- candidate based on an older request: reject rather than merge;
- resulting contract invariant failure: reject the entire bundle;
- zero question budget after not_sure: the next C1 result may abstain under the existing
  budget rule.

No partial bundle, best-effort merge, or fallback guess is permitted.

## 11. Verification Strategy

Required tests include:

- strict wire round-trips and digest stability for every new contract;
- exhaustive AnswerKind/AnswerValue shape tests;
- stale passport, wrong question digest, wrong project, replayed event, and variable
  substitution attacks;
- every P1 clarification address reaching its exact component field;
- metamorphic checks that source specs never change;
- template/goal changes staling all declared dependents while preserving snapshots;
- acceptance certificate mismatch and event-sequence reversal attacks;
- atomic multi-spec commit and fresh C1 re-resolution;
- passport evidence binding;
- architecture guards proving no I/O, calculation, persistence, or execution authority;
- full existing recommendation/UI and numerical regression.

## 12. Non-Goals

This slice does not:

- render questions or acceptance UI;
- persist or delete events;
- sign evidence cryptographically;
- send data or metadata to a cloud service;
- execute an analysis;
- launch an external route;
- expand P1 Method Space;
- claim that the recommendation is scientifically valid merely because the evidence
  chain is internally consistent.

## 13. Completion Criterion

Completion means a P1 clarification answer can change the planning state only through
an immutable, stale-safe, content-addressed, explicitly accepted revision chain, and a
fresh passport can prove which local decision evidence was used. It does not mean the
answer, recommendation, or downstream analysis has human-gold validity.
