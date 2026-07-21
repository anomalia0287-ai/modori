# Build Week Result-First Demo Final Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one polished, evidence-bound, 164–170 second English Modori upload master and matching SRT, with a local neural narration when it passes the bounded gate and the verified Zira narration as the deterministic fallback.

**Architecture:** Keep the verified product binary, source/test trees, raw Guided Mode capture, causal-abstention capture, and generated Word report immutable. A new isolated media pipeline owns exact cue data, one fixed narration engine/speed, audio-derived cue timing, deterministic FFmpeg edits, and machine-readable verification; only canonical submission documents and the final SRT enter Git. The upload handoff directory contains exactly one MP4 and one SRT.

**Tech Stack:** PowerShell 7/Windows PowerShell, CPython 3.12, Kokoro ONNX plus `soundfile` for preferred local synthesis, Microsoft Zira Desktop SAPI fallback, FFmpeg 7.1, Git, and the existing packaged PySide6/QML Modori footage.

## Global Constraints

- Product source-under-test remains `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b`; do not modify `src/` or `tests/`.
- Use the twelve exact English narration cues in `docs/superpowers/specs/2026-07-21-build-week-result-first-demo-final-design.md`.
- Final duration is at least 164 seconds, at most 170 seconds, and strictly below 180 seconds; no duration padding is permitted.
- The opening card lasts about 2.5 seconds, narration begins immediately, and the real result is visible no later than `00:03`.
- Use one recorded voice engine, voice name, and fixed global speed/rate across all twelve cues; per-cue rate changes are prohibited.
- Prefer Kokoro ONNX synthesis performed locally after dependency/model download; do not use `edge-tts`, which sends text to an online service.
- Cap Kokoro environment setup, model download, and first representative sample at 25 minutes of active wall time; on timeout, take the verified Zira fallback instead of waiting.
- Fall back to Microsoft Zira Desktop SAPI rate `0` only if the bounded Kokoro installation, license, pronunciation, decode, or duration gate fails.
- Trim only synthesizer trailing silence; add one fixed `0.75`-second transition tail; no detected full-media silence interval may exceed `1.25` seconds.
- Product footage runs at `1.0x`; remove waiting, native pickers, and irrelevant cursor travel with hard cuts; never exceed `1.25x`.
- Final video is H.264 High-compatible, `1920x1080`, square pixels, constant 30 fps, yuv420p, with AAC-LC 48 kHz stereo, about `-16 LUFS`, and true peak no higher than `-1.5 dBTP`.
- Use only `3,393 passed, 5 skipped` in current release-facing copy. Preserve dated `3,233 passed, 13 skipped` Office-benchmark history without reusing it in the submission story.
- Show current UI `p = 0.000` when it appears, but narrate `p below .001`; do not claim a literal zero p-value.
- No competitor price/interface, currency conversion, third-party logo, copyrighted music, stock footage, private path, private identity, account, notification, API key, session transcript, or unrelated application appears.
- Do not push, merge, change the public default, or replace release artifacts.
- Present the user with only `modori-build-week-final.mp4` and `modori-build-week-final.en.srt` from the final handoff directory.

## File Structure

- Modify `docs/superpowers/specs/2026-07-21-build-week-result-first-demo-final-design.md`: frozen narration, verified clarification order, voice policy, and acceptance gates.
- Modify `docs/qa/build-week-real-data-research-os-e2e.md`: actual ledger question order and post-submission p-format backlog.
- Create `.visual-qa/build-week-real-data-candidate-2026-07-21/video/final-demo-cues.psd1`: single source of exact narration, spoken aliases, labels, voice choice, and tail timing.
- Create `.visual-qa/build-week-real-data-candidate-2026-07-21/video/test-final-demo-contract.ps1`: local red/green media-contract tests that do not alter the product suite count.
- Create `.visual-qa/build-week-real-data-candidate-2026-07-21/video/synthesize-final-kokoro.py`: local Kokoro WAV renderer with no network code.
- Create `.visual-qa/build-week-real-data-candidate-2026-07-21/video/generate-final-demo-voice.ps1`: preferred-Kokoro/fallback-Zira orchestration and voice manifest.
- Create `.visual-qa/build-week-real-data-candidate-2026-07-21/video/build-final-demo-video.ps1`: audio-derived 30-fps timeline, product cuts, evidence cards, SRT, and mux.
- Create `.visual-qa/build-week-real-data-candidate-2026-07-21/video/verify-final-demo.ps1`: media, silence, claim, privacy, subtitle, and handoff-directory gates.
- Create `.visual-qa/build-week-real-data-candidate-2026-07-21/video/final-voice-manifest.json`: exact engine, voice, speed/rate, versions, hashes, and fallback reason if any.
- Create `.visual-qa/build-week-real-data-candidate-2026-07-21/video/qa/final-upload-master/`: probes, audits, contact sheet, and selected original-resolution frames.
- Create `.visual-qa/build-week-real-data-candidate-2026-07-21/upload-master/modori-build-week-final.mp4`: sole upload video.
- Create `.visual-qa/build-week-real-data-candidate-2026-07-21/upload-master/modori-build-week-final.en.srt`: sole upload subtitle.
- Modify `docs/build-week/DEMO_SCRIPT.md`: exact final timeline, English narration, Korean operator meaning, source hashes, and human upload boundary.
- Modify `docs/build-week/VIDEO_VERIFICATION.md`: exact final hashes, probes, voice manifest, media QA, claim/privacy audit, and remaining external actions.
- Modify `docs/build-week/assets/modori-build-week-demo.en.srt`: byte-identical copy of the final handoff SRT.
- Modify `docs/build-week/DEVPOST_SUBMISSION.md`: replace superseded 2:05 video references with the final result-first master and consistent `3,393 / 5` evidence.

---

### Task 1: Freeze the reviewed copy and make the contract test fail

**Files:**
- Modify: `docs/superpowers/specs/2026-07-21-build-week-result-first-demo-final-design.md`
- Modify: `docs/qa/build-week-real-data-research-os-e2e.md`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/test-final-demo-contract.ps1`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/final-demo-cues.psd1`

**Interfaces:**
- Consumes: the approved twelve-cue table and verified SQLite order `confirm_cluster_use`, `confirm_dependence`, `confirm_weight_use`.
- Produces: `$cueData.Cues` with `Index`, `SubtitleText`, and `SpeechText`; `$cueData.Labels`; `$cueData.TailPaddingSeconds`; `$cueData.PreferredVoice`; `$cueData.PreferredSpeed`.

- [ ] **Step 1: Write the failing contract test**

Create `test-final-demo-contract.ps1` with assertions that fail while `final-demo-cues.psd1`, `build-final-demo-video.ps1`, and the handoff files are absent:

```powershell
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$cuePath = Join-Path $root 'final-demo-cues.psd1'
if (-not (Test-Path -LiteralPath $cuePath)) { throw 'final cue source is missing' }
$data = Import-PowerShellDataFile -LiteralPath $cuePath
if (@($data.Cues).Count -ne 12) { throw 'exactly twelve cues are required' }
$indices = @($data.Cues | ForEach-Object { [int]$_.Index })
if (($indices -join ',') -ne '1,2,3,4,5,6,7,8,9,10,11,12') { throw 'cue indices are not contiguous' }
$joined = (@($data.Cues | ForEach-Object SubtitleText) + @(
    $data.Labels.GetEnumerator() | ForEach-Object { [string]$_.Value }
)) -join "`n"
foreach ($required in @(
    'I majored in sociology',
    'clustering, dependence, and weights',
    'Prepare exposes the configuration',
    'With Codex and GPT-5.6',
    '3,393 passed',
    'Kindness is not decoration. It is system behavior.'
)) {
    if ($joined -notmatch [regex]::Escape($required)) { throw "missing required copy: $required" }
}
foreach ($forbidden in @('independence, clustering', '3,233', '13 skipped', 'SPSS', '₩')) {
    if ($joined -match [regex]::Escape($forbidden)) { throw "forbidden current-story copy: $forbidden" }
}
if ([double]$data.TailPaddingSeconds -ne 0.75) { throw 'tail must be exactly 0.75 seconds' }
if ([string]$data.PreferredVoice -ne 'af_sarah') { throw 'preferred local voice must be af_sarah' }
if ([double]$data.PreferredSpeed -ne 0.92) { throw 'initial global Kokoro speed must be 0.92' }
Write-Output 'PASS: final narration contract'
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
& .visual-qa/build-week-real-data-candidate-2026-07-21/video/test-final-demo-contract.ps1
```

Expected: exit `1` with `final cue source is missing`.

- [ ] **Step 3: Create the exact cue data**

Create `final-demo-cues.psd1` with `TailPaddingSeconds = 0.75`, `PreferredVoice = 'af_sarah'`, `PreferredSpeed = 0.92`, all twelve approved `SubtitleText` strings verbatim, and the exact evidence labels in Task 3. Use spoken-only aliases in `SpeechText` for `Modori` → `Moh-doh-ree`, `GPT-5.6` → `G P T five point six`, and `rho` → `row`; do not alter subtitle spelling or claim meaning.

- [ ] **Step 4: Run the copy test and repository consistency scans**

Run:

```powershell
& .visual-qa/build-week-real-data-candidate-2026-07-21/video/test-final-demo-contract.ps1
rg -n '3,233|13 skipped' README.md docs/build-week docs/qa/build-week-real-data-research-os-e2e.md docs/superpowers/specs/2026-07-21-build-week-result-first-demo-final-design.md
git diff --check
```

Expected: contract test passes; the release-facing scan returns no matches; `git diff --check` exits `0`.

- [ ] **Step 5: Commit the reviewed design and plan checkpoint**

```powershell
git add docs/superpowers/specs/2026-07-21-build-week-result-first-demo-final-design.md docs/qa/build-week-real-data-research-os-e2e.md docs/superpowers/plans/2026-07-21-build-week-result-first-demo-final.md
git commit -m "docs: reconcile final Build Week demo review"
```

Expected: one local documentation commit; no push.

### Task 2: Gate one local neural voice and preserve the deterministic fallback

**Files:**
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/synthesize-final-kokoro.py`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/generate-final-demo-voice.ps1`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/final-voice-manifest.json`
- Modify: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/test-final-demo-contract.ps1`

**Interfaces:**
- Consumes: `final-demo-cues.psd1`, official `kokoro-v1.0.onnx`, official `voices-v1.0.bin`, or installed Zira.
- Produces: `final-voice/cue-01.wav` through `cue-12.wav` plus a manifest with `engine`, `voice`, `global_speed_or_rate`, package/model hashes, and `fallback_reason`.

- [ ] **Step 1: Extend the test before implementing synthesis**

Add assertions that the generator contains no `edge-tts`, `speech.platform.bing.com`, HTTP client, per-cue speed/rate field, or network download call; requires twelve nonempty WAV files; and requires one manifest engine in `kokoro-onnx-local` or `sapi-local`.

- [ ] **Step 2: Run the extended test to verify it fails**

Run the contract test. Expected: exit `1` because the generator, WAV set, and manifest do not exist.

- [ ] **Step 3: Install the local engine in an isolated media environment**

Run:

```powershell
py -3.12 -m venv .visual-qa/video-tools/kokoro-venv
& .visual-qa/video-tools/kokoro-venv/Scripts/python.exe -m pip install --upgrade pip
& .visual-qa/video-tools/kokoro-venv/Scripts/python.exe -m pip install kokoro-onnx soundfile
```

Download only the two official release assets into `.visual-qa/video-tools/kokoro-model/`:

```text
https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

Record SHA-256 hashes and installed package versions before synthesis. The renderer itself contains no network code.

- [ ] **Step 4: Implement the local WAV renderer**

`synthesize-final-kokoro.py` accepts `--model`, `--voices`, `--voice`, `--speed`, `--text`, and `--output`, then performs exactly:

```python
kokoro = Kokoro(args.model, args.voices)
samples, sample_rate = kokoro.create(
    args.text,
    voice=args.voice,
    speed=args.speed,
    lang="en-us",
)
sf.write(args.output, samples, sample_rate)
```

Reject empty samples, non-finite values, output shorter than 0.5 seconds, and output longer than 40 seconds.

- [ ] **Step 5: Implement one-engine orchestration and bounded fallback**

`generate-final-demo-voice.ps1` first attempts all twelve Kokoro cues at global speed `0.92`. If import, model, license-manifest, render, WAV decode, or duration checks fail, delete the partial preferred set and render all twelve cues with Microsoft Zira Desktop at global rate `0`. Never mix engines within one candidate. Write the exact reason only when the fallback is taken.

- [ ] **Step 6: Calibrate only one global Kokoro speed when needed**

Probe all twelve trimmed speech durations. With twelve fixed `0.75`-second cue tails, require the predicted final duration in `164–170` seconds. If Kokoro at `0.92` misses, calculate one replacement global speed:

```text
replacement_speed = 0.92 * measured_speech_seconds / 158.0
```

Clamp to `0.85–1.00`, rerender all twelve cues once at that one speed, and reject Kokoro if the second prediction still misses. Do not modify individual cue speeds.

- [ ] **Step 7: Run the voice gates**

Run the generator, contract test, FFmpeg decode of all twelve WAVs, and a silence/duration report. Expected: exactly one engine and voice, twelve decodable WAVs, one fixed speed/rate, predicted duration `164–170`, and no network endpoint in the renderer.

### Task 3: Build the exact result-first visual timeline with red/green checks

**Files:**
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/build-final-demo-video.ps1`
- Modify: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/test-final-demo-contract.ps1`

**Interfaces:**
- Consumes: twelve final WAVs, verified raw clips, rendered DOCX page, cue data, and fixed `0.75`-second tail.
- Produces: frame-aligned visual MP4, voiceover WAV, final MP4, final SRT, segment audit CSV, and cue timing CSV.

- [ ] **Step 1: Add failing structural assertions for the final edit**

Require the build script to declare `1920x1080`, `30` fps, `164` minimum seconds, `170` maximum seconds, `1.25` maximum motion speed, result reveal at or before `3.0`, and these ordered visual groups: opening/result, payoff/report, import, meaning gate, bounded questions, candidate, Prepare/Confirm/Run, causal abstention, Codex authority, three UI fixes, Royal Blue integration/test evidence, and closing.

- [ ] **Step 2: Run the test to verify it fails**

Expected: exit `1` because `build-final-demo-video.ps1` is absent.

- [ ] **Step 3: Implement the clip matrix without changing product speed**

Use the existing source ranges as hard-cut anchors, all at `1.0x`:

| Story group | Source anchors |
| --- | --- |
| opening/result | 2.5-second navy card, then `raw-full-guided-20260721.mp4` near `645.0s` |
| payoff/report | result near `645.0s`, then `report-render/page-1.png` |
| import | Guided entry near `18.5s`, import review near `126.5s`, full table near `162.0s` |
| meaning | role/meaning review near `391.5s`, Variable Meaning Gate near `530.2s` |
| bounded questions | `443.0s`, `480.0s`, `520.0s`, `550.3s`, `570.0s` in ledger order |
| candidate/config | `588.0s`, `597.0s` |
| Prepare/Confirm/Run | `609.2s`, `622.0s`, result near `645.0s` |
| causal abstention | both verified `raw-causal-abstention-20260721.mp4` captures |
| closing reconnect | Run/result anchors, followed by closing navy card |

Allocate each cue's audio-derived frames across its clips by declared weights. Never stretch a moving clip; shorten with hard cuts or finish a cue on a designed evidence card/image.

- [ ] **Step 4: Implement deterministic evidence motion**

Create short Royal Blue/navy cards with gentle progress-line, crop, or 1.000→1.018 zoom motion. Use these exact visible claims:

```text
PRODUCT QUESTION → CONTRACT → RED TEST → IMPLEMENTATION → PACKAGED APP
VARIABLE MEANING
PASSPORT + LEDGER
PREPARE ≠ CONFIRM ≠ RUN
EMPTY FIRST SHEET → RECOVERED TO DATA
EXISTING REPORT → SAFE REPLACEMENT
GENERIC FAILURE → ACTIONABLE RECOVERY
7 ORDERED ROYAL BLUE UI COMMITS
25 OVERLAPPING PATHS
12 PREDICTED TEXT CONFLICTS
SEMANTIC REVIEW · NO BLANKET RESOLUTION
3,393 PASSED · 5 SKIPPED · EXIT 0
NIST StRD REFERENCE CHECKS · R CROSS-ENGINE ANCHORS
```

Use no logo or screenshot belonging to a third party.

- [ ] **Step 5: Generate subtitle and timing data from the same cue source**

SRT text comes only from `SubtitleText`, while speech uses `SpeechText`. Each subtitle begins at its cue's first frame and ends at its last frame. UTF-8/LF output must contain twelve contiguous, non-overlapping cues and end on the final video frame.

- [ ] **Step 6: Run the structural test to green**

Expected: all declared groups present in order; first card duration `2.5 ± 0.1`; result reveal `≤3.0`; moving speed `1.0`; output duration `164–170`.

### Task 4: Render one candidate and reject technical failures automatically

**Files:**
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/verify-final-demo.ps1`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/qa/final-upload-master/`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/upload-master/modori-build-week-final.mp4`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/upload-master/modori-build-week-final.en.srt`

**Interfaces:**
- Consumes: final render outputs and source evidence hashes.
- Produces: exactly two handoff files plus internal QA evidence.

- [ ] **Step 1: Write failing verification gates before the final render**

The verifier must reject missing files, extra files in `upload-master`, duration outside `164–170`, result after `3.0`, non-1080p output, non-30-fps output, non-square pixels, non-H.264/AAC output, non-48-kHz stereo audio, subtitle mismatch, silence over `1.25`, true peak over `-1.5 dBTP`, decode errors, old test counts, and missing source hashes.

- [ ] **Step 2: Run the verifier to confirm the red state**

Expected: exit `1` because no final handoff exists.

- [ ] **Step 3: Render and mux the final master**

Render all visual segments at constant 30 fps, concatenate losslessly where compatible, concatenate the padded 48-kHz voice WAVs, normalize once with FFmpeg `loudnorm=I=-16:LRA=11:TP=-1.5`, mux AAC-LC at 192 kb/s, and write fast-start MP4. Copy only the final MP4 and SRT into a freshly emptied `upload-master` directory after verifying the resolved directory is inside this worktree.

- [ ] **Step 4: Run full media verification**

Run FFprobe/FFmpeg for stream metadata, exact frame count, full audio/video decode, `silencedetect=noise=-40dB:d=1.25`, `blackdetect`, and two-pass loudness measurement. Expected: every machine gate passes and the SRT endpoint equals the last video frame within one frame.

- [ ] **Step 5: Generate visual-review evidence**

Extract at least one original-resolution frame for every story group, plus frames at `00:00`, `00:02.5`, `00:03`, result, p-value, n/exclusions, import preview, 649-row table, meaning gate, each bounded question, candidate, experimental badge, Prepare, Confirm with empty result, separate Run, causal abstention, each engineering chain, final card, and subtitle endpoint. Create a labeled contact sheet only in the internal QA directory.

### Task 5: Audit claims, privacy, and subjective presentation

**Files:**
- Modify: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/qa/final-upload-master/verification.json`
- Modify: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/qa/final-upload-master/manual-review.md`

**Interfaces:**
- Consumes: final MP4, SRT, original-resolution frames, design spec, exact ledger/result/package evidence.
- Produces: explicit pass/fail status for every acceptance gate and a bounded list of external-only actions.

- [ ] **Step 1: Compare every displayed number to its source**

Verify `649`, `rho = 0.275`, displayed `p = 0.000`, narrated `p below .001`, `n = 649`, excluded `0`, seven commits, 25 overlapping paths, 12 predicted text conflicts, and `3,393 passed / 5 skipped / exit 0` against committed or hash-bound evidence.

- [ ] **Step 2: Review every original-resolution frame for privacy and legibility**

Reject cropped controls, covered values, unreadable required text, file pickers, OS taskbar/title bar, private paths, personal identity, accounts, notifications, third-party price/logo screens, or unrelated windows.

- [ ] **Step 3: Review pacing and voice at normal speed**

Confirm the opening does not rush, narration begins immediately, no screen waits after its message is understood, no key UI state disappears before four seconds, evidence cards remain legible for 2.5–3.5 seconds, pronunciation is acceptable for Modori/Spearman/rho/GPT-5.6, and the voice remains one natural global speed. If a subjective defect is found, correct the source once and rerun Tasks 4–5 in full; do not patch the final MP4 in isolation.

- [ ] **Step 4: Mark only external operations as remaining**

Leave YouTube upload visibility, signed-out URL verification, submission-form completion, receipt preservation, and Fable 5 external-participant verification open. Do not describe them as completed.

### Task 6: Replace the canonical submission packet with exact final evidence

**Files:**
- Modify: `docs/build-week/DEMO_SCRIPT.md`
- Modify: `docs/build-week/VIDEO_VERIFICATION.md`
- Modify: `docs/build-week/assets/modori-build-week-demo.en.srt`
- Modify: `docs/build-week/DEVPOST_SUBMISSION.md`

**Interfaces:**
- Consumes: verified final MP4/SRT hashes, cue timing CSV, voice manifest, media probes, claim/privacy review, immutable product evidence.
- Produces: one internally consistent release-facing packet that distinguishes completed local evidence from human/external operations.

- [ ] **Step 1: Update the canonical script from measured timing**

Write all twelve actual cue start/end times, exact English subtitle text, approved Korean meanings, shot descriptions, engine/voice/speed, source hashes, and actual total duration. Remove the superseded 2:05 claim and social-science-student wording.

- [ ] **Step 2: Update verification from generated evidence**

Record exact byte sizes, SHA-256 hashes, codecs, dimensions, frame count, duration, loudness, peak, maximum silence, black-frame interpretation, subtitle endpoint, voice/model hashes, source assets, and manual review status. Explicitly state whether Kokoro or Zira won the gate and why.

- [ ] **Step 3: Copy and compare the canonical SRT**

Copy the handoff SRT to `docs/build-week/assets/modori-build-week-demo.en.srt`, normalize UTF-8/LF, and verify byte identity with `Get-FileHash` plus `Compare-Object` or `fc /b`.

- [ ] **Step 4: Reconcile the Devpost story and all release-facing counts**

Update duration/video references and run:

```powershell
rg -n '2:05|125\.033|social-science student|3,233|13 skipped' README.md docs/build-week
rg -n '3,393 passed, 5 skipped|3,393 PASSED · 5 SKIPPED' README.md docs/build-week
```

Expected: no superseded current-story text; every test-count mention resolves to `3,393 / 5`.

- [ ] **Step 5: Run focused repository checks**

Run Markdown structure/whitespace checks already used by the release packet, SRT parser checks, `git diff --check`, and `git diff --stat`. Confirm `git diff -- src tests` is empty and tree hashes still match the product source-under-test evidence.

- [ ] **Step 6: Commit the final local submission evidence**

```powershell
git add docs/build-week/DEMO_SCRIPT.md docs/build-week/VIDEO_VERIFICATION.md docs/build-week/assets/modori-build-week-demo.en.srt docs/build-week/DEVPOST_SUBMISSION.md
git commit -m "docs: verify final Build Week upload master"
```

Expected: local documentation-only commit; no push.

### Task 7: Final handoff without file-choice ambiguity

**Files:**
- Read: `.visual-qa/build-week-real-data-candidate-2026-07-21/upload-master/modori-build-week-final.mp4`
- Read: `.visual-qa/build-week-real-data-candidate-2026-07-21/upload-master/modori-build-week-final.en.srt`

**Interfaces:**
- Consumes: the green verification packet and clean Git state.
- Produces: one local playback review request and exact upload instructions.

- [ ] **Step 1: Re-run the final verifier and hash both handoff files**

Expected: exit `0`; exactly two files; hashes identical to `VIDEO_VERIFICATION.md`.

- [ ] **Step 2: Open only the final MP4 in the local Windows video player**

Do not use Chrome. Do not open intermediate candidates. Ask the user to judge voice naturalness, pronunciation, pacing, visual legibility, and whether any wait or rush remains.

- [ ] **Step 3: Report the remaining manual submission sequence**

After the user accepts playback: upload the exact MP4, attach the matching SRT, set the video Public, verify the URL signed out, paste it into the submission form, submit, and preserve the confirmation receipt. Do not perform these external writes without the user's action or a new explicit instruction.

## Self-Review

- Spec coverage: all twelve story beats, timing, local-first voice, Zira fallback, 1.0x motion, media profile, claims, privacy, exact test count, p-value wording, two-file handoff, and external boundaries map to Tasks 1–7.
- Placeholder scan: the plan contains exact paths, commands, expected outcomes, cue requirements, source anchors, evidence labels, and acceptance thresholds; no deferred implementation placeholder remains.
- Interface consistency: cue data feeds both voice and subtitles; WAVs plus cue timing feed the visual build; build outputs feed the verifier; verifier evidence feeds canonical docs; canonical hashes feed the final handoff.

Execution choice is already resolved by the user's instruction to proceed: perform **Inline Execution** in this session with `superpowers:executing-plans`. Do not dispatch subagents.
