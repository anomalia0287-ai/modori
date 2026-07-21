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

## 2A. Verification integrity — the measuring instrument must be trusted first

- **A release claim is invalid if the verification tool is unverified.** Test scripts, QA payloads, VM setup helpers, batch files, and smoke-test fixtures are part of the release system. They must be reviewed and tested with the same seriousness as product code.
- **Never mix verification roles.** A fixture created for import-preview visibility is not automatically valid for engine-smoke verification. A fixture created for engine smoke is not automatically valid for UX inspection. Each artifact must have one declared purpose, and scripts must enforce that purpose.
- **No hidden execution paths.** Scripts that affect release evidence must not hide failure behind auto-elevation, disappearing windows, implicit state, or unlogged background work. If administrator privileges are required, the script must say so and stop unless run explicitly as administrator.
- **No invisible success.** Every release-affecting helper must leave inspectable evidence: exit code, log path, generated artifact path, and a plain-language success/failure line. If no log exists, assume the helper did not run.
- **No unvalidated reuse.** Existing generated artifacts such as VHDX files, package folders, smoke outputs, reports, and QA payloads must be validated before reuse. A stale or partial artifact is more dangerous than no artifact.
- **Separate product failure from verification failure before acting.** When a gate fails, first classify the failure as product defect, verification-tool defect, operator/environment issue, or unknown. Do not patch the product to satisfy a broken gate.
- **Host-side proof precedes clean-VM delegation.** Before asking the owner to perform a VM step, run the same package/fixture contract on the host where possible and record the expected output. The clean VM should verify environment independence, not discover that the test itself was malformed.
- **Manual steps require exact state labels.** Instructions must distinguish host PC, VM, project path, VM storage path, guest drive label, and expected window/title text. Ambiguous terms like "here", "there", "the file", or "run it" are not acceptable in release QA instructions.

## 3. The project comes before egos and feelings

- **The integrity of the project outranks anyone's feelings or opinions — including the owner's.** Do not flatter. Do not agree to be agreeable. Do not soften a necessary objection to avoid friction.
- **Disagreement is a duty, not rudeness.** If a decision — from the owner, from Claude, or from Codex — is wrong for the project, say so plainly, with reasoning and evidence. Staying silent to keep the peace is a violation of this policy.
- **Decisions are made on merit and evidence, not on seniority or on who proposed them.** "I was wrong" and "that earlier idea doesn't hold up" are normal, expected sentences. (Precedent: the competitive reality-check that demoted two presumed "killer" features once evidence showed they already existed — that honesty is the standard, not the exception.)
- **Be honest about uncertainty and bad news.** Report failing tests as failing. Flag weak assumptions. Do not present a hopeful guess as a fact.
- **Do not defend an avoidable failure.** If the process skipped a necessary check, say so. The correct response is containment, root-cause analysis, regression protection, and re-verification — not rhetorical mitigation.
- **A user's confusion is a system signal.** If a non-developer owner confuses host and VM, old and new payloads, or import and engine fixtures, treat that as a documentation and workflow defect unless proven otherwise.

## 3A. Statistical software operating bar

- **The product must be treated as statistical infrastructure, not a demo app.** A wrong p-value, coefficient, CI, reliability estimate, or exported report can damage real decisions. UX polish never compensates for numerical uncertainty.
- **Claimed accuracy requires a named reference.** For each supported statistical path, the release record must identify the reference implementation or certified value, the dataset, the tolerance, and the command/test that reproduces the comparison.
- **Unsupported scope must be visible.** If a method, assumption, file format, model family, or edge case is outside the current release scope, the product and release notes must say so rather than implying SPSS-level breadth.
- **A green gate is not enough if the gate is weak.** Passing tests are evidence only for the behavior they actually exercise. Any discovered blind spot must become a new regression test or an explicit release blocker.

## 4. Anyone may speak

- **Any contributor may raise a concern, propose a change, or challenge any decision, at any time** — regardless of role.
- **Roles define responsibility, not permission to speak.** A reviewer may question the architecture; an implementer (Codex) may push back on a spec it believes is wrong; the owner may be overruled by evidence. The owner retains final say on direction, but only after the objection has been heard on its merits.
- **Raise issues early and directly.** A problem spotted at design time costs a sentence; the same problem spotted after implementation costs a rewrite.

## 5. How conflicts resolve

1. **Evidence beats opinion.** Cite sources: papers, competitor behavior, test results, or this project's own stated principles.
2. **When blocked, escalate to the owner with a clear recommendation**, not an open-ended question.
3. **The non-negotiables in §2 cannot be bargained away** to settle a dispute. If a proposed compromise weakens correctness, stability, or P1, it is rejected by default.
4. **If verification credibility is damaged, recovery precedes feature work.** Do not continue UI, packaging, research, or release work until the failed verification path has a documented root cause, a regression guard, and a successful rerun.
5. **If the team cannot classify a failure, the release is blocked.** "Unknown but probably fine" is not an accepted state.

## 6. Required recovery procedure after a bad gate or bad instruction

When a release gate, QA helper, or operator instruction is found to be wrong:

1. **Freeze the affected claim.** Stop using any result produced by the suspect gate or instruction.
2. **Classify the failure.** Product defect, verification-tool defect, operator/environment issue, or unknown.
3. **Preserve evidence.** Keep logs, generated files, screenshots, terminal output, and exact commands when possible.
4. **Write or update a regression guard.** If code or scripts changed, add a test that fails on the old behavior.
5. **Remove ambiguity.** Update instructions so a non-developer can distinguish host, VM, old artifact, new artifact, expected output, and failure output.
6. **Rerun from a clean state.** Reuse generated artifacts only after validation, or create fresh artifacts with unique names.
7. **Record the incident.** Add a short risk note when the failure could affect release interpretation.
8. **Only then resume release work.** Do not bury the incident under new progress.

---

*This document is expected to evolve. Propose changes the same way you'd challenge any other decision — openly, with reasoning.*
