# TongTong — Project Policy & Engineering Principles

> **Status:** Governance document. Binds **all** contributors — the owner (design/planning + review), Claude (planning/review), and Codex (implementation). When convenience conflicts with this policy, this policy wins. Read before contributing.

---

## 1. Language of record

- **Implementation and code-related artifacts are written in English.** This covers: specs, design docs, code, code comments, identifiers, commit messages, PR descriptions, tests, and API documentation.
- **Rationale:** the AI contributors (Codex, Claude) perform more reliably in English. The owner is Korean but accepts English for engineering records for this reason.
- **High-level discussion** with the owner may be in Korean.
- **Exempt — product content, not engineering record:** user-facing strings (UI labels, APA auto-generated output) follow the product localization plan (Korean-first; see `specs/01-reference-slice-likert-to-report.md` §4). Korean here is a feature, not a violation.
- Existing Korean spec(s) predating this policy should be migrated to English when next substantially edited.

## 2. Quality and stability above all — non-negotiable

- **Correctness and stability are the only acceptable bar.** A statistics tool that produces a wrong number is worthless — trust drops to zero on the first error. There is no "mostly correct."
- **Token cost and wall-clock time are NOT constraints.** Never cut scope, skip validation, shorten a review, omit a test, or take a shortcut to save tokens or time. When in doubt, do the thorough thing. Slowness is acceptable; corner-cutting is not.
- **No silent failure, no "good enough."** If something cannot be done correctly, surface it explicitly with the reason — never paper over it.
- **Numerical golden-value validation is mandatory and may never be waived** (see slice spec §7.1). Every statistic is checked against a published/reference value to ≥3 decimals.
- The replayable-pipeline architecture (P1) and the other slice-spec principles (P2–P5) are load-bearing and are not traded away for expedience.

## 3. The project comes before egos and feelings

- **The integrity of the project outranks anyone's feelings or opinions — including the owner's.** Do not flatter. Do not agree to be agreeable. Do not soften a necessary objection to avoid friction.
- **Disagreement is a duty, not rudeness.** If a decision — from the owner, from Claude, or from Codex — is wrong for the project, say so plainly, with reasoning and evidence. Staying silent to keep the peace is a violation of this policy.
- **Decisions are made on merit and evidence, not on seniority or on who proposed them.** "I was wrong" and "that earlier idea doesn't hold up" are normal, expected sentences. (Precedent: the competitive reality-check that demoted two presumed "killer" features once evidence showed they already existed — that honesty is the standard, not the exception.)
- **Be honest about uncertainty and bad news.** Report failing tests as failing. Flag weak assumptions. Do not present a hopeful guess as a fact.

## 4. Anyone may speak

- **Any contributor may raise a concern, propose a change, or challenge any decision, at any time** — regardless of role.
- **Roles define responsibility, not permission to speak.** A reviewer may question the architecture; an implementer (Codex) may push back on a spec it believes is wrong; the owner may be overruled by evidence. The owner retains final say on direction, but only after the objection has been heard on its merits.
- **Raise issues early and directly.** A problem spotted at design time costs a sentence; the same problem spotted after implementation costs a rewrite.

## 5. How conflicts resolve

1. **Evidence beats opinion.** Cite sources: papers, competitor behavior, test results, or this project's own stated principles.
2. **When blocked, escalate to the owner with a clear recommendation**, not an open-ended question.
3. **The non-negotiables in §2 cannot be bargained away** to settle a dispute. If a proposed compromise weakens correctness, stability, or P1, it is rejected by default.

---

*This document is expected to evolve. Propose changes the same way you'd challenge any other decision — openly, with reasoning.*
