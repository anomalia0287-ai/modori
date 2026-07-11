# Experimental Recommendation Boundary Release Evidence

Date: 2026-07-11 KST

Status: host-side implementation and package evidence passed. Clean-VM visual
walkthrough and owner acceptance remain open. This evidence does not establish
recommendation accuracy and does not promote any recommendation family to
`VALIDATED`.

## Claim Boundary

The product keeps every executable statistics module available while placing the
current recommendation layer behind an explicit experimental surface. Live
candidates have `evidence_status=EXPERIMENTAL`, start with no selected candidate,
cannot execute directly, and require user confirmation plus the existing manual
configuration/run path.

Calculation-module numerical evidence and recommendation-selection validity are
independent claims. The work in this pass does not modify statistical formulas,
result DTOs, numerical tolerances, or reference fixtures. The only changed file
under `src/modori/steps` is `reporting.py`; its diff adds selection-origin
validation and a fixed disclosure at the start of report prose.

## Source And Artifact Identity

| Item | Pinned value |
| --- | --- |
| Branch | `codex/recommendation-benchmark-pilot` |
| Implementation HEAD under test | `34e42eb8fa2075f88b7ff524d5a1dae55d16c3da` |
| Experimental-boundary base | `aa04d4347e065f44ef3431ffc59e31c53ca844b9` |
| Pilot case count | 20 |
| Manifest count | 20 |
| Unique pilot data files | 19 |
| Pilot cases SHA-256 | `E90140EC10A3A36414BA0212EA7D2E0A5D1BC9C0A42350890B53EA95F8B48484` |
| Pilot manifest SHA-256 | `62FF49F3EBB36E0CFD76B48E977E75F52868AB03A7989DD91117CC1D3845C82B` |
| Scorer fingerprint | `sha256:1d232ac88bc705b8c31735aa6e997d253a388a478c9337d146f6798d50f33aac` |
| Scorer implementation digest | `sha256:127d7cd7c1f313a592ed6d491307e891fee138f59212ecbbe8e1da8a78765679` |
| Frozen and regenerated baseline SHA-256 | `FC5D3E9032D086225B0C7C62F4E3145217BA44F8FDDF73CB10E4F5EADD485650` |

`validate-pack` returned `ok: true`. A fresh `predict-a` output and the frozen
`baseline-a-predictions.jsonl` had the same SHA-256 and a zero-byte diff. The
historical benchmark adapter therefore remains reproducible while live product
state has no default selection.

## Product Boundary Evidence

- Every process starts in standard mode. Experimental mode is not persisted and
  requires an explicit entry action.
- No candidate is selected automatically. The UI states that candidate order is
  an unvalidated deterministic ordering, not accuracy or priority evidence.
- Selecting or preparing a candidate does not mutate the dataset, pipeline,
  cache, results, pipeline version, or worker queue.
- All 16 emitted candidate kinds route into an existing manual configurator.
  Calculation remains behind explicit confirmation and the manual run command.
- Selection origin is either `manual` or
  `experimental_candidate_assisted`. Assisted reports receive a fixed bilingual
  disclosure; unknown origin values fail before report output.
- Product wording scanning covers runtime Python, QML, accessibility strings,
  help/library content, report/export text, README, and product documentation.
  Historical benchmark vocabulary is confined to an explicit allowlist.
- Package engine smoke configures its analysis directly and no longer depends on
  recommendation output.

## Executed Gates

All commands ran from the isolated worktree with Python 3.12.10. The final
integrated gate explicitly set
`MODORI_RSCRIPT=C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe`.

1. Final integrated quality, package, and slow-statistics gate:

   ```text
   python scripts/quality_gate.py --with-package-check --with-package-build --with-packaged-launch --with-slow-stats
   compileall: pass
   ruff: pass
   bandit: pass
   launch-smoke-ok
   1532 passed, 5 skipped in 81.24s
   pip check: no broken requirements
   package-tool-ok
   package build: pass
   package-launch-smoke-ok
   package-engine-smoke-ok
   package-public-data-smoke-ok
   4 passed, 1533 deselected in 23.08s
   exit code: 0
   ```

2. Skip audit with `pytest -q -rs`:

   - One skip is the expected `paired_comparison` recommendation-ineligibility
     contract; that module does not use recommendation routing.
   - Four skips are tests guarded by `MODORI_RUN_SLOW_STATS=1`: three bootstrap
     adequacy tests and one factorial-ANOVA performance test.
   - The separate slow-statistics gate executed all four guarded tests and passed.
   - Explicit R configuration increased the full result from 1524 passed and 13
     skipped to 1532 passed and 5 skipped. The eight previously skipped R
     references therefore executed and passed; they are not counted as skipped
     evidence.

3. Focused boundary and product-path gates executed during implementation:

   ```text
   final recommendation/report/QML/package focus: 161 passed
   complete UI suite: 420 passed
   reporting/prose focus: 164 passed
   recommendation focus: 168 passed
   wording/payload/QML focus: 43 passed
   clean-VM payload tests: 19 passed
   product-wording scanner tests: 6 passed
   file-operation audit plus scanner: 8 passed
   PowerShell payload script parser: pass
   ```

4. Source-range audit:

   ```text
   git diff --check aa04d4347e065f44ef3431ffc59e31c53ca844b9...HEAD
   exit code: 0

   git diff --name-status aa04d4347e065f44ef3431ffc59e31c53ca844b9...HEAD -- src/modori/steps src/modori/core
   M src/modori/steps/reporting.py
   ```

## Built Package And VM Fixtures

The final integrated gate rebuilt the Windows package with PyInstaller 6.21.0.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `dist/Modori/Modori.exe` | 30,983,214 bytes | `79D4944B56B5E8929C06B408B9D9971240C8FAB6CEA89437F2D8B57BF1ADC210` |
| `experimental-candidate.csv` | fixed fixture | `7C8930F6CF05428F4C80EF99E54278664D4CEE303361C5A4B819407DF1975CF3` |
| `experimental-configuration.csv` | fixed fixture | `DA555DA9FB6379AC0192EC174477885DB0812AB806B7734CB155206CC56D8DCD` |
| `experimental-no-candidate.csv` | fixed fixture | `8E2B0BFF6B601D1D54626990A48F2436F0AD7C2021C19AE636B3A34C1CADA4AC` |

The package build emitted optional PyInstaller discovery warnings, including a
missing unused Qt asset-downloader plugin and `scipy.special._cdflib`. Packaged
launch, engine, public-data, and statistical smoke gates all passed after that
build. These warnings are retained as packaging residuals rather than silently
treated as evidence.

## Open Gates And Residual Limits

1. The owner must complete the clean-VM walkthrough in
   `docs/qa/experimental-recommendation-vm-runbook.md`. Until then, layout,
   keyboard/mouse interaction, no-preselection behavior, and disclosure visibility
   on the clean VM are not accepted.
2. If Word is absent in the VM, successful DOCX creation is useful but does not
   verify rendered disclosure placement. That inspection remains open until the
   document is viewed on a machine with a compatible renderer.
3. The 20-case pilot is an economics and workflow artifact, not recommendation
   accuracy evidence. No qualified-reviewer calibration corpus or 800-case locked
   claim corpus exists.
4. Recommendation accuracy, expert equivalence, public 80 percent claims, SLM
   adoption, and any `VALIDATED` promotion remain blocked by their human evidence
   gates.
5. This pass is ready for payload rebuild and owner VM inspection, not product
   promotion or public recommendation-quality claims.
