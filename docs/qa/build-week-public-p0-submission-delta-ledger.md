# Public P0 Submission Delta Ledger

Date: 2026-07-21 KST

## Scope

This ledger reconciles the nonfunctional Build Week release delta between the shared
functional-usability parent `b368cdcf208d04509717826bc6b0ab7e7b72ba7e` and the
published P0 tip `c23164c2cf42857c24776c83ee3cfbd017e74b9e` into the current
real-data usability lane. It is separate from
`build-week-public-p0-functional-delta-ledger.md`, which already audits the 12
release-only `src/` and `tests/` paths.

No merge, whole-tree checkout, `ours`/`theirs` resolution, public push, or release
artifact replacement is used. Each path is classified by current meaning.

## Inventory and disposition

| Release delta | P0 paths | Disposition in this lane | Reason |
| --- | ---: | --- | --- |
| Source license | `LICENSE` | Exact port | The public P0 already froze the GPL-3.0-only license text. Rewriting it would create risk without product value. |
| Package metadata | `pyproject.toml` | Semantic port of three lines | Retain the current dependency and package-data tree; add the validated README, GPL metadata, and setuptools 77 floor required by the P0 wheel. |
| Project README | `README.md` | Rewritten against current evidence | The P0 README described the superseded synthetic correlation demo and `CASUAL MODE`. The current file leads with the 649-row UCI path, `GUIDED MODE`, actual-QML Word/replan evidence, and positive Codex/GPT-5.6 collaboration framing. |
| Third-party notice | `THIRD_PARTY_NOTICES.md` | P0 notice plus bounded extension | Preserve the P0 dependency/font/icon/test-data disclosures and add UCI Student Performance DOI, CC BY 4.0 terms, and the derived-view boundary. |
| Windows constraints | `constraints/build-week-windows-py312.txt` | Exact port | The existing verified Python 3.12.10/PyInstaller 6.21.0 environment matches the public P0 constraint inventory. |
| Submission documents | seven Markdown files under `docs/build-week/` | Regenerate in Task 5 | The evidence structure is reusable, but its synthetic story, old source hashes, old test counts, and evidence-first narration are no longer the submission truth. These files will be authored from the current real-data package and result-first demo. |
| Submission visual/text assets | two SVG cards and one English SRT | Regenerate in Task 5 | The old cards/subtitles are bound to the superseded narration. They may be used only as layout references, not copied as current evidence. |
| P0 implementation plan | `docs/superpowers/plans/2026-07-20-modori-build-week-submission-closure.md` | Retain in P0 history only | The current lane has its own real-data closure plan and must not present the older plan as the active one. |
| Existing Royal Blue audit/spec files | two QA documents and one Variable Meaning Gate spec | Preserve current descendants | The usability lane contains later recovery, inspectability, Guided Mode, and real-data work. Replacing those files with the earlier P0 versions would erase current evidence. |
| Release-only product/test paths | 12 paths | Already reconciled semantically | See the functional delta ledger and the passing 179-test adjacent cohort. |

## Metadata gates before packaging

The candidate may proceed to wheel and one-folder build only after all of the
following are true:

1. `README.md`, `LICENSE`, and `THIRD_PARTY_NOTICES.md` exist and are linked by the
   final source tree;
2. `pyproject.toml` parses and declares `readme = "README.md"`,
   `license = "GPL-3.0-only"`, and `setuptools>=77`;
3. the constraint file remains byte-identical to public P0;
4. the README describes `GUIDED MODE`, the UCI real-data path, the separate Run,
   actual Word/replan evidence, and the direct-cell-editing boundary;
5. the README does not claim causality, recommendation validity, expert equivalence,
   SPSS superiority, complete bilingual/accessibility coverage, or a public binary;
6. the generated wheel contains valid metadata, the current README, and the GPL
   license file.

## Deferred—not discarded

The seven submission Markdown files and three demo assets remain mandatory. They are
deferred until the fresh package hash, executable smokes, visible result, screenshots,
and Word file are available, so the final narration cannot drift from the candidate
actually shown to judges.
