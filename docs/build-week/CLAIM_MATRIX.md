# Build Week Claim Matrix

This is the technical wording authority for the README, Devpost text, demo narration,
subtitles, screenshots, and story edits. When another document conflicts with this
matrix or with executable repository evidence, the narrower repository-backed wording
wins.

| Topic | Evidence status | Allowed wording | Do not say |
| --- | --- | --- | --- |
| Project origin | Verified pre-existing project | "Modori existed before Build Week and was meaningfully extended during the submission period." | "Modori was built entirely during Build Week." |
| Build Week delta | Timestamp/history audited | "The pre-release baseline has 127 post-cutoff commits, with later release-document commits added separately." | Treating every line reachable through the integration merge as new work |
| Runtime AI | No runtime model route in current code | "Codex and GPT-5.6 were build-time collaborators; Modori calculations remain local and deterministic." | "GPT-5.6 analyzes the user's data inside Modori." |
| P1 scope | Executable catalog and tests | "Research OS P1 supports exactly six bounded local research tasks." | "Modori covers social-science research broadly." |
| External routes | Catalog contains zero routes | "There are no verified external routes." | Naming a cloud or external fallback as available |
| Recommendations | `EXPERIMENTAL`, explicit selection and confirmation | "Modori presents experimental candidates that never auto-run." | "Modori recommends the correct test" or an accuracy percentage |
| Calculation start | Product contract and tests | "A separate user action starts calculation after review." | "The recommendation automatically runs the analysis." |
| Local processing | Source audit and security tests | "The current runtime has no configured network client, telemetry, or hosted analysis route." | "Certified private", "zero data risk", or claims about OS/cloud/antivirus behavior |
| Statistical accuracy | Method-specific R/NIST/formula/library anchors | "Selected methods have bounded reference tests described in the QA ledger." | "All calculations are proven correct" |
| Expert equivalence | Not tested | State that it is unproven | Any professor, expert, or human parity claim |
| SPSS/JASP/jamovi | Limited fixture/reference comparisons only | Describe a named fixture and exact comparison when necessary | Superiority or full equivalence |
| Interface language | Main shell Korean-first; selected report/Research OS contracts support English | "The full UI is not completely bilingual." | "Complete Korean and English support" |
| Accessibility | Partial tests and accessible labels; no complete conformance audit | "Complete accessibility conformance has not been established." | "Fully accessible" |
| Windows target | Windows 11 x64 and CPython 3.12.10 verified | Name the exact target and local unsigned build path | macOS/Linux support or general Windows certification |
| B4-R | Recorded development-PC pass at the sealed kit identity | Quote `3233 passed, 13 skipped`, 300 rejected mutations, and three byte-identical kit builds with the bound commit/hash | Applying those numbers to an unbound later build |
| B5 HP | Pending | "B5 low-cost HP laptop measurement is pending." | "Runs well on a low-cost HP laptop" or "HP passed" |
| Open source | Owner-approved `GPL-3.0-only` source with notices | "Modori-authored source is GPL-3.0-only." | Treating dependencies, data, trademarks, or future binaries as relicensed by Modori |
| Public binary | Intentionally absent | "Judges can run from source or produce a local unsigned one-folder build." | "Download the official Modori executable" |
| General reproducibility | Exact Windows constraints and local gates | "The documented environment and commands are reproducible targets." | Byte-identical general application builds; only the sealed benchmark kit has that evidence |
| Live judge flow | Packaged-app walkthrough on the synthetic fixture | "Import, Research OS review, separate Run, and the displayed synthetic result were exercised on Windows." | Generalizing one fixture to recommendation validity, all datasets, or all methods |

## Facts that must remain linked

- Sealed kit source/build commit:
  `989d5c5829e3d3de69ebda0f4fc88e6f76d16112`
- Sealed kit SHA-256:
  `6f567b327ad53c68eff5f27623e494c1273f9a424e11896e99c5d9f5a0bb8d43`
- B4-R gate: `3233 passed, 13 skipped`
- B5: pending
- Public default HEAD at the 2026-07-19 audit:
  `0413059b993ae5bb28190907badb7733d94f3f64`
- Integrated pre-release baseline:
  `eaa0e802a0c64f6619297432f129be4d198a79ea`
- Build Week cutoff:
  `2026-07-13T09:00:00-07:00` / `2026-07-14T01:00:00+09:00`

## Fable review rule

Fable may improve structure, tone, and clarity. It may not introduce new technical
facts. Reject or narrow any edit that adds open-source status beyond the approved
license, full bilingual support, verified external routes, an HP pass, recommendation
accuracy, expert equivalence, SPSS superiority, broad social-science coverage, complete
accessibility, runtime GPT-5.6, or a public binary.
