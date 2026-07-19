# Build Week Demo Packet

Target duration: **2 minutes 55 seconds**

Language: English voiceover with matching English subtitles

Fixture: `pilot-007-correlation.csv` from the repository's deterministic synthetic
benchmark pack

This packet leaves recording and public YouTube upload to the owner. It does not ask
the owner to improvise technical claims.

## Before recording

1. Use the final public release commit, not an older worktree or installer payload.
2. Before capture starts, open PowerShell in the final source tree and create a
   mandatory fresh state plus a neutral copy of the fixture:

   ```powershell
   $demoRoot = Join-Path $env:PUBLIC "Documents\ModoriDemo"
   $demoState = Join-Path $demoRoot ("state-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
   New-Item -ItemType Directory -Force `
     $demoRoot, `
     "$demoState\local-app-data", `
     "$demoState\temp", `
     "$demoState\cache", `
     "$demoState\matplotlib" | Out-Null
   Copy-Item `
     tests\fixtures\recommendation_benchmark\public\pilot\data\pilot-007-correlation.csv `
     "$demoRoot\pilot-007-correlation.csv" -Force

   $env:LOCALAPPDATA = "$demoState\local-app-data"
   $env:TEMP = "$demoState\temp"
   $env:TMP = $env:TEMP
   $env:MODORI_CACHE_DIR = "$demoState\cache"
   $env:MODORI_SETTINGS_PATH = "$demoState\settings.json"
   $env:MPLCONFIGDIR = "$demoState\matplotlib"
   .\.venv\Scripts\python.exe -m modori.app
   ```

   Keep that PowerShell window out of the capture. The unique state is required: it
   prevents recent files or an earlier Research OS transaction from changing the
   recorded flow.
3. Choose `English` on the entry screen. Do not show real research data, names, email
   addresses, API keys, hostnames, task titles, or private paths.
4. Set Windows display scaling and the capture window so text is readable at 1080p.
5. Keep normal application speed. Jump cuts are allowed, but do not present a cut as
   proof of uninterrupted timing.
6. Do not add copyrighted music, third-party stock footage, or unlicensed logos.
7. Prepare the final `/feedback` Session ID for the Devpost form, but do not needlessly
   expose the full ID in the video.

Prepared visual and subtitle assets:

- [`assets/demo-evidence-card.svg`](assets/demo-evidence-card.svg) — 1920×1080
  Build Week evidence card;
- [`assets/demo-closing-card.svg`](assets/demo-closing-card.svg) — 1920×1080
  closing limitations card; and
- [`assets/modori-build-week-demo.en.srt`](assets/modori-build-week-demo.en.srt) —
  canonical English subtitles matching the narration below.

## Shot list and exact narration

| Time | Screen | Action | English narration and subtitle |
| --- | --- | --- | --- |
| 00:00–00:09 | Modori entry screen | Hold on the wordmark, language controls, mode cards, and local-processing line. | "Modori is a local desktop research workflow for making a limited set of statistical choices visible before calculation." |
| 00:09–00:27 | Prepared Build Week evidence card | Show `Existing project`, the cutoff, and all five eligible extension groups on the supplied card. | "This was an existing project. During Build Week, I used Codex with GPT-5.6 to revise the Windows research surface, extend deterministic clarification and passport authority, add a variable-meaning review, and harden release evidence." |
| 00:27–00:39 | Same evidence card, then return to Modori | Highlight `build time, not runtime` and the owner-decision line. | "GPT-5.6 was a build-time engineering collaborator, not a runtime model. I retained the product, licensing, claim, hardware, and release decisions." |
| 00:39–00:55 | Entry screen, then import review | Select `English`, choose `CASUAL MODE`, and click `Open data file`. Jump-cut past the entire OS file picker; resume only after selecting `%PUBLIC%\Documents\ModoriDemo\pilot-007-correlation.csv`. | "I select English and Casual Mode, then open a deterministic synthetic file with stress and sleep hours. It contains no real respondent records." |
| 00:55–01:10 | Import review and work surface | Show the preview, confirm the import, and briefly show the 16-row, two-column table plus the source-protection notice. | "Modori previews the table before import. Source cells are read-only; transformations become recorded steps and new variables. The current runtime has no configured hosted analysis, network client, or telemetry route." |
| 01:10–01:34 | Research OS boundary, task, and roles | Open Research OS, accept the noncausal boundary, choose linear co-movement, and assign `stress` and `sleep_hours`. | "Research OS P1 supports exactly six bounded tasks. I accept the noncausal boundary, choose linear co-movement, and bind both variable roles to this exact dataset." |
| 01:34–01:49 | Variable Meaning Gate | Hold on both variable cards, including measurement levels and any `not recorded` definition/unit boundary, then confirm. | "Before any durable request is created, the Variable Meaning Gate shows the current labels, measurement levels, missing codes, and any definition or unit that is not recorded." |
| 01:49–02:07 | Clarification and passport-bound candidate | Show one bounded clarification about clustering, independence, or weights, then advance to the candidate. | "After I confirm those meanings, bounded clarification records my answers. A deterministic policy can explain its question order, and the AnalysisPassport stays bound to the data and decision state." |
| 02:07–02:29 | Candidate and configuration review | Hold on the experimental boundary, open the exact prepared configuration, confirm it, and pause while the result remains empty and Run becomes available. | "The Pearson candidate is experimental, not an accuracy ranking, and cannot run automatically. I review and confirm its exact configuration; confirmation adds no result and the separate Run action is now available." |
| 02:29–02:44 | Separate Run action and results | Click Run, then open `Open wide table`; hold where `r = -0.995`, display-rounded `p = 0.000`, `n = 16`, and zero excluded rows are all legible. | "Only Run starts the calculation. For this synthetic file, Modori reports an association of negative point nine nine five across sixteen rows, not a causal conclusion or validated recommendation." |
| 02:44–02:55 | Report dialog and prepared closing card | Close the wide table, open Report, select English, and hold where `Save to Word` is enabled. Do not open the OS save dialog; cut directly to the supplied closing card. | "After the result, tested Word export becomes available. The full interface is not yet completely bilingual; source, setup, tests, limitations, and current evidence are public." |

The closing card must contain only:

```text
6 bounded local tasks
Experimental recommendations · no auto-run
Source, setup, tests, and limitations in the public repository
```

## Subtitle file

Use the canonical
[`assets/modori-build-week-demo.en.srt`](assets/modori-build-week-demo.en.srt)
directly in the editor or upload it to YouTube. Do not retime one copy without making
the shot table, narration, and canonical SRT agree again.

## Evidence card text

Use a plain, high-contrast card with no decorative third-party assets:

```text
Modori · OpenAI Build Week eligible extension

Existing project
Official cutoff: 2026-07-13 09:00 PT

Built with Codex + GPT-5.6
• revised Windows research surface
• bounded deterministic clarification
• variable meaning + AnalysisPassport v2 authority
• durable confirm → Run → Word flow
• release integration and verification hardening

GPT-5.6 is not a Modori runtime dependency.
Owner retained product and release decisions.
```

## Recording acceptance checklist

- [ ] Final duration is less than 3:00; target is 2:55.
- [ ] Voiceover is audible throughout and covers Modori, Codex, and GPT-5.6.
- [ ] English subtitles match the approved narration.
- [ ] The video shows a working import, Variable Meaning Gate, Research OS flow,
      configuration confirmation with no result, separate Run action, result, and Word
      export—not only slides.
- [ ] Only the synthetic demo fixture is visible.
- [ ] The app was launched with the fresh isolated state above; no recovered Research
      OS task or recent-file history changes the flow.
- [ ] No private path, recent file, notification, account name, session transcript,
      or real study data is visible.
- [ ] OS file-picker and save dialogs are entirely excluded by jump cuts; no OS chrome
      is used as product evidence.
- [ ] The experimental badge and no-auto-run boundary are legible.
- [ ] The source-protection notice is legible; the video does not imply direct cell
      editing.
- [ ] No HP pass, full bilingual, recommendation-accuracy, expert-equivalence, SPSS-
      superiority, complete-accessibility, broad-scope, or external-route claim appears.
- [ ] There is no copyrighted background music or unlicensed third-party material.
- [ ] The upload is a **Public** YouTube video, not Unlisted or Private.
- [ ] The public video link works in a signed-out browser.
