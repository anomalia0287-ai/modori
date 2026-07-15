# Risk-Bounded Counterfactual Clarification Planner Design

**Date:** 2026-07-15  
**Status:** Approved research direction; implementation is confined to the dedicated
`codex/research-os-contract-design` worktree.  
**Scope:** Deterministic C1 clarification selection only. No UI, statistical
calculation, model training, network access, persistence authority, or product release
claim is authorized by this design.

## 1. Decision

Replace C1's current severity/count/ID clarification sorter with a bounded,
counterfactual minimax planner that:

1. asks exactly one question per round;
2. looks ahead through the remaining inline question budget, which is at most three;
3. simulates every substantive closed answer branch without mutating the real request;
4. minimizes unresolved scientific risk before ambiguity or user burden;
5. treats `not_sure` as a safe refusal branch, never as evidence;
6. never repeats a question that the user has already answered with `not_sure`;
7. emits an auditable, digest-bound explanation of why the selected question dominated
   the alternatives; and
8. abstains rather than silently falling back to the legacy heuristic when the exact
   planner cannot finish inside its fixed structural resource bound.

This is an internal component research claim. It does not establish recommendation
validity, statistical accuracy, human-expert superiority, SPSS superiority, or broad
social-science coverage.

## 2. Why this is not a UI feature

Sequential screens and branching questions are prior art. StatHand guides users through
annotated questions for statistical procedure selection, execution, interpretation, and
reporting. [Allen et al. (2016)](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2016.00288/full)
Rule-derived adaptive questionnaires have also reduced displayed clinical conditions by
about two thirds in a medication decision-support application.
[Lamy et al. (2024)](https://arxiv.org/abs/2309.10398)

The algorithmic problem is instead a finite adaptive test-selection problem: which fact
should be acquired next so that the worst remaining scientific decision risk is as small
as possible? Decision-tree research establishes that expected test cost and worst-case
test cost can prefer radically different trees and that exact optimization is generally
hard. [Cicalese, Laber, and Saettler
(2014)](https://proceedings.mlr.press/v32/cicalese14.html) Cost-sensitive active feature
acquisition likewise separates the cost of acquiring information from the cost of a wrong
decision. [Ji and Carin
(2007)](https://doi.org/10.1016/j.patcog.2006.11.008)

Modori therefore does not claim to invent adaptive questionnaires, minimax search, or
decision trees. The candidate contribution is their constrained composition with:

- estimand-preserving capability identities;
- typed fact authority (`observed`, `inferred`, `user_confirmed`, `unknown`,
  `conflict`, `stale`, and `not_applicable`);
- first-class recommendation, clarification, external routing, and abstention;
- an E1--E5 scientific and boundary-risk ordering that cannot be averaged away;
- immutable answer transitions and stale propagation; and
- local evidence-carrying decision traces with no generative model.

Recent active-feature-acquisition evaluation work warns that changing the acquisition
policy itself changes the data distribution and requires separate evaluation assumptions.
[von Kleist et al. (2025)](https://www.jmlr.org/papers/v26/23-1635.html) The present
planner avoids a learned acquisition policy and probability estimates, but it still must
be evaluated separately from the downstream recommendation's validity.

## 3. Observed implementation gap

At the frozen baseline commit `cc1e94bce5d147717447e195179bb68584a2574e`,
`C1Resolver._rank_clarifications` ranks questions by:

```text
maximum rule severity, descending
number of unresolved rules carrying the question ID, descending
question ID, ascending
```

It does not evaluate answer branches, recompute decision signatures, inspect declared
question dependencies, minimize worst-case loss, or prevent a `not_sure` question from
being selected again. It may also return up to three questions in one decision. The
correct pre-change environment passed `1942` tests with `5` skips; the focused Research
OS baseline passed `187` tests and Ruff.

Consequently, placing a multi-round UI over the current resolver would be a presentation
change around a simple priority sorter, not the approved research system.

## 4. Alternatives

### A. Fixed dependency tree

Ask root questions such as research goal and design before method-specific facts in one
frozen order.

**Advantages:** smallest implementation, easy to explain, constant planning cost.  
**Failure:** cannot adapt when prior trusted facts already eliminate branches; repeats the
central limitation of classical statistical decision trees; order is catalog-author
judgment rather than case-specific evidence.  
**Decision:** retain only as a comparison baseline.

### B. One-step counterfactual greedy planner

For every candidate question, simulate its immediate answers and choose the best
one-step reduction.

**Advantages:** materially stronger than the current sorter; small and fast.  
**Failure:** a question with the best immediate split can force a poor second or third
question. It cannot establish that the chosen root is optimal for the already fixed
three-question budget.  
**Decision:** implement only as an ablation baseline, not the selected architecture.

### C. Bounded counterfactual minimax planner

Search all legal substantive answer branches to the remaining depth, at most three,
memoize equivalent states, and select the root whose worst terminal loss is smallest.

**Advantages:** globally optimal inside the frozen abstract P1 state model and budget;
directly testable against exhaustive program oracles; matches the approved multi-round
interaction.  
**Cost:** more state evaluations and a required structural resource guard.  
**Decision:** selected.

## 5. Formal objects

### 5.1 Production facts are immutable during planning

Let `F` be the current trusted fact mapping. The planner creates ephemeral mappings
`F[q <- a]` for simulation. A simulated fact:

- is never appended to the Decision Ledger;
- never becomes user-confirmed production evidence;
- never changes a QuestionSpec, EstimandSpec, StudySpec, analysis configuration, or
  dataset;
- is discarded after the planning call; and
- carries a reserved planner-only provenance marker that cannot pass through the answer
  transition service.

Only an actual validated `ClarificationAnswerEvent` may create a real revision.

### 5.2 Answer equivalence classes

Each active `ClarificationSpec` already provides closed branches. The planner converts
them to abstract answer equivalence classes:

| Branch kind | Ephemeral projection |
| --- | --- |
| `choice_values` | one simulation for each registered choice value |
| `empty_variables` | confirmed empty tuple |
| `nonempty_variables` | confirmed non-empty structural sentinel |
| `answered` | confirmed non-empty structural sentinel of the declared answer kind |
| `not_sure` | unknown with `user_not_sure:<question_id>` |

The sentinel is valid only for unary `EMPTY`/`NONEMPTY` rule evaluation. A Method Space
that applies an `IN` predicate to an open-answer branch is rejected as a registry/rule
contract error rather than guessed.

Define:

```text
A+(q) = substantive answer equivalence classes
A?(q) = the single not_sure refusal class
```

`A?(q)` is always safety-tested: it must not open a recommendation or route, and it must
decrease the real question budget after an actual answer event. It is excluded from the
information-gain minimax calculation because including a deliberately non-informative
refusal makes the worst-case gain of every question identically zero. This exclusion is
not permission to infer an answer. If the user chooses `not_sure`, that question is
ineligible for automatic re-asking in the resulting revision.

### 5.3 Decision snapshot

For each simulated state, C1 computes a closed `DecisionSnapshot` before selecting any
next question:

```text
DecisionSnapshot =
  current_action
  stable_local_keys
  possible_local_keys
  ready_route_ids
  possible_route_ids
  estimand_template_ids
  role_fact_digests
  design_ids
  claim_permission_sets
  blocking_fact_addresses
  blocking_question_ids
  risk_vector
  route_classes
  data_policy_marks
```

`possible` means not excluded by a trusted current fact. It does not mean recommended.
Question text, method labels, raw data, and result values are absent from the snapshot.

The semantic signature used for branch comparison is:

```text
(current_action,
 stable_local_keys,
 possible_local_keys,
 ready_route_ids,
 possible_route_ids,
 estimand_template_ids,
 role_fact_digests,
 design_ids,
 claim_permission_sets,
 blocking_fact_addresses,
 risk_vector,
 route_classes,
 data_policy_marks)
```

This is exact for P1's six mutually distinguished capability identities. A future Method
Space that introduces true co-primary equivalence must first add a frozen
`co_primary_group_id`; the planner must not infer equivalence from similar names.

### 5.4 Risk vector

Duplicating a rule across several capabilities must not multiply the apparent severity of
one missing fact. For each unresolved actionable fact address `x`, define:

```text
R(x) = maximum severity of any unresolved actionable hard rule on x
```

Then:

```text
risk_vector(F) =
  (# unique E5 addresses,
   # unique E4 addresses,
   # unique E3 addresses,
   # unique E2 addresses,
   # unique E1 addresses)
```

Vectors are compared lexicographically from E5 to E1. Therefore no number of E1--E3
improvements can compensate for one additional E4 or E5 ambiguity.

### 5.5 Decision frontier size

An outcome atom is one possible surface-authorized local capability, verified route, or
definite abstention boundary described by exact identity, estimand template, design,
claim permissions, and route class. `frontier_size(F)` is the number of distinct atoms
still compatible with trusted facts. A definite correct abstention has zero unresolved
capability atoms; it is not penalized merely for declining coverage.

This quantity measures decision ambiguity, not prediction uncertainty or probability.

## 6. Bounded minimax policy

### 6.1 Terminal loss

For a state `F`, remaining budget `d`, and worst-path accumulated question cost `C`, the
terminal loss is:

```text
L(F, d, C) =
  (risk_vector(F),
   frontier_size(F),
   number_of_blocking_fact_addresses(F),
   worst_path_questions_asked,
   worst_path_dependency_deficit,
   worst_path_answer_kind_cost)
```

The tuple is lexicographic. Scientific ambiguity is therefore resolved before optimizing
convenience. No weighted sum is permitted.

The P1 burden policy is versioned with the planner and derived only from already frozen
contract fields:

1. unresolved declared dependencies;
2. answer-kind burden (`yes_no=1`; `single_choice` and `level_choice=2`;
   `variable_single=3`; `variable_multi=4`; `ordered_variables=5`;
   `bounded_text=6`; `conflict_resolution=7`); and
3. question ID as the final deterministic tie-break.

These are engineering cost tiers, not empirically validated user-burden estimates. Actual
answer time, `not_sure` rate, correction rate, and abandonment must be measured
separately before changing the tiers.

### 6.2 Recurrence

Let `Q(F)` be the unique active candidate questions referenced by unresolved actionable
rules, excluding questions previously refused with `not_sure`.

```text
V(F, 0) = L(F, 0, 0)

V(F, d) = min over q in Q(F) of
            max over a in A+(q) of
              V(F[q <- a], d - 1) + declared_cost(q)
```

The minimum and maximum use the complete lexicographic loss. The selected question is the
root `q*`. C1 returns only `q*`; after a real answer, it replans from the new immutable
revision.

Search stops early when normal primary-action precedence yields a stable local
recommendation, a verified route with no action-changing unresolved prerequisite, a
definite abstention, or no legal question.

### 6.3 Relevance

A question is legal for the current state only if at least one substantive branch:

- changes the action, exact capability frontier, estimand, role digest, design, claim
  permission, route class, or data-policy mark; or
- removes a hard method-selection blocker required to reach one of those decisions.

Questions that change only explanation wording are prohibited. A question is also
rejected if its substantive projections cannot resolve its own fact address under the
declared trust floor.

Declared dependencies are not blindly treated as hard prerequisites because some P1
dependencies are contextual rather than logically necessary. Each unresolved dependency
adds deterministic cost, causing root or better-grounded questions to win when scientific
loss is tied. A later contract may distinguish prerequisite from invalidation dependency,
but this planner does not invent that distinction.

### 6.4 Determinism and resource bound

The planner memoizes by:

```text
(planner_version,
 method_space_digest,
 clarification_registry_digest,
 surface,
 remaining_budget,
 canonical relevant-fact digest,
 refused_question_ids)
```

Equivalent answer classes with identical state digests are collapsed. Input fact order,
rule order, capability order, registry order, and branch declaration order must not affect
the selected question or trace.

The search has a fixed state-evaluation cap, chosen after measuring the complete P1
worst-case matrix. Wall-clock time is not used as a decision boundary because it would
make identical inputs produce different results. If the cap is reached, C1 emits typed
`abstain(planner_search_limit_exceeded)` and never falls back to the old sorter.

## 7. Output and evidence trace

A clarify decision contains one question ID and one blocking fact address. Its non-authority
audit trace records, for every root candidate:

```text
planner_version
question_id, question_version, question_digest, fact_address
substantive branch IDs and snapshot digests
not_sure safety snapshot digest
worst terminal loss
guaranteed E3+ blockers removed
dependency deficit and answer-kind burden
evaluated state count and memo hit count
selected flag and deterministic rank key
```

The trace cannot contain a capability recommendation inside a clarify payload. Exact
candidate identities remain in the internal resolver audit only. The selected question's
version and digest are included in the resolver semantic digest so a changed registry
changes the decision evidence.

## 8. Known passport binding gap

The current `ClarifyPayload` binds only `question_ids` and
`blocking_fact_addresses`. `ClarificationAnswerEvent` binds a question version and digest,
but the source passport does not directly bind those values. Consequently, an old
clarify passport can be presented with a newer registry question of the same ID unless a
separate schema-level reference is added.

This planner trace makes the drift observable in the resolver decision digest, but the
transition service cannot invert that digest to enforce the original question revision.
Therefore:

- this implementation must not claim complete replay-stable question provenance;
- no question text or version is changed as part of the planner implementation; and
- product integration remains blocked on a separately approved AnalysisPassport schema
  revision that binds typed clarification revision references directly.

Silently changing schema version 1 is prohibited.

## 9. Failure behavior

| Condition | Required result |
| --- | --- |
| corrupt context, mixed versions, malformed fact | integrity abstention before planning |
| zero remaining question budget | `clarification_budget_exhausted` abstention |
| user previously selected `not_sure` for the only blocker | `clarification_answer_unavailable` abstention |
| unresolved rule has no registered active question | integrity abstention |
| open answer paired with incompatible predicate | integrity abstention |
| all answers have identical irrelevant signatures | question prohibited; abstain if none remain |
| state-evaluation cap reached | `planner_search_limit_exceeded` abstention |
| simulated branch raises or contains unsupported value | integrity abstention; no partial result |

No failure permits recommendation, route emission, auto-configuration, or execution.

## 10. Verification strategy

### 10.1 Independent formal oracle

Build a deliberately small test-only method space and a separate exhaustive policy
enumerator. For every compatible fact assignment, every question budget from zero to
three, and every permutation of facts, rules, capabilities, questions, and branches:

- the production planner must choose the same root and terminal loss as the oracle;
- every path terminates within the budget;
- no refused question repeats; and
- no simulated fact escapes into a returned production context.

The oracle shares immutable contracts but not the production search implementation.

### 10.2 Locked baselines

Compare four policies on the same generated finite cases:

1. batch form: acquire every unresolved fact;
2. fixed dependency/ID tree;
3. frozen legacy severity-impact sorter;
4. bounded minimax planner.

Report separately:

- exact oracle agreement;
- worst residual E5--E1 vector;
- worst frontier size;
- worst and median question count;
- unnecessary questions;
- repeated-question attempts;
- states evaluated, memo hits, elapsed time, and peak memory.

This is planner-fidelity evidence. It is not recommendation-validity evidence and cannot
be labeled human gold.

### 10.3 Adversarial and metamorphic cases

Required attacks include:

- a high-impact common question that looks attractive to the legacy sorter but leaves a
  larger worst decision frontier than a discriminating question;
- a question with one excellent and one disastrous branch to defeat average-case scoring;
- E4/E5 versus many E1--E3 trade-offs;
- `unknown`, `conflict`, `stale`, imported-unreviewed/inferred trust failures, and
  `not_applicable`;
- same data structure with different question/estimand facts;
- duplicated rule references that must not multiply one fact address's risk;
- answer and registry order permutations;
- `not_sure` followed by replanning;
- budget exhaustion and exact state-cap exhaustion;
- malformed branch/predicate pairings; and
- route evidence states from unverified through roundtrip-verified.

### 10.4 Repository gates

After every red-green cycle, run the focused planner/resolver tests. Before any completion
claim, freshly run:

- every `tests/test_research_os_*.py` test;
- Research OS Ruff checks;
- the locked policy comparison;
- the complete repository pytest suite with the pinned Python and R reference runtime;
- full Ruff; and
- the architecture guard proving no I/O, network, calculation, or execution authority was
  introduced.

## 11. Predeclared success and stop criteria

### Conditional success

The planner may replace the legacy sorter only if all are true:

1. exact agreement with the independent exhaustive oracle on the full small-state matrix;
2. zero E4/E5 failures, recommendation leaks, route leaks, loops, or provenance mutations;
3. exactly one question returned per clarification round;
4. no worse worst-case formal loss than the one-step planner on every locked case;
5. at least one locked nontrivial case where the legacy sorter or fixed tree has strictly
   greater formal loss or asks a provably unnecessary question;
6. deterministic output under every declared permutation;
7. no planner state-cap abstention on the P1 locked operating slice;
8. focused and full repository gates pass; and
9. measured development-machine worst case remains below 5 seconds and 256 MiB, leaving a
   wide margin beneath the user's 30-second office-PC tolerance.

These thresholds authorize further pilot work only.

### Stop or simplify

- If bounded lookahead never improves formal loss or question count over one-step greedy,
  ship the simpler one-step planner and reject the extra machinery.
- If the exact planner exceeds its structural cap on P1 cases after one rational,
  profile-driven optimization cycle, retain deterministic C1 but do not adopt bounded
  lookahead.
- Any E4/E5 result, nontermination, silent fallback, or mixed-version trace stops the
  candidate release attempt under the existing global rule.
- If no independently anchored recommendation-validity corpus becomes available, the
  strongest allowed claim remains deterministic planner fidelity and formal safety, not
  expert-level statistical recommendation.

## 12. Implementation boundary

Expected production changes are limited to:

- a new pure `counterfactual_planner` module;
- resolver snapshot construction and one-question integration;
- service injection of the existing clarification registry;
- typed non-authority planner traces;
- closed abstention recovery mappings; and
- tests and internal QA evidence.

The legacy product recommendation service, UI, calculation steps, data import, Decision
Ledger storage, evidence-bundle quarantine, packaging, benchmark fixtures, and persisted
passport schema are not changed by this work.
