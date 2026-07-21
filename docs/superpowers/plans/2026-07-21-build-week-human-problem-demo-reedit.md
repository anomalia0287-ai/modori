# Build Week Human-Problem Demo Re-edit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and verify an exact 175-second English Build Week submission video that combines a first-person social-science problem story, one real-data successful workflow, one clearly separate causal abstention, and concrete Codex/GPT-5.6 engineering evidence.

**Architecture:** Keep the verified UCI dataset, packaged launcher, successful raw capture, result, and Word report. Create only the missing causal-abstention capture, then assemble natural-speed source excerpts, generated brand cards, a privacy-clean Codex evidence montage, and new voice cues through the existing local FFmpeg/SAPI toolchain. Treat the MP4, SRT, script, and verification record as one hash-bound packet.

**Tech Stack:** PowerShell 7/Windows PowerShell, FFmpeg 7.1 from `imageio-ffmpeg`, Microsoft Zira local SAPI voice, packaged PySide6/QML Modori launcher, Python/pytest for existing evidence, Git for immutable documentation.

## Global Constraints

- Work only in `C:\Users\V\.codex\worktrees\3998\TongTong` on branch `codex/research-os-functional-usability`.
- Do not modify product source or tests for the video edit.
- Do not push, change the public default branch, replace release artifacts, or merge.
- Preserve source-under-test `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b` and the exact packaged launcher/hash already recorded in `docs/build-week/DEMO_SCRIPT.md`.
- Use the observed UCI 649-row demo CSV; do not use synthetic data.
- Do not show SPSS or another third-party price page, logo, copyrighted music, stock footage, private session text, or private identity data.
- Keep runtime exactly 175.00 seconds and every continuous speed adjustment at or below 1.25x.
- Keep the successful noncausal request and causal abstention as visibly separate tasks.
- Keep calculation claims separate from recommendation-validity claims.
- Keep the product local-only, experimental, abstention-capable, commit-before-display, and explicit-Run framing.

---

### Task 1: Freeze the canonical script and caption packet

**Files:**
- Modify: `docs/build-week/DEMO_SCRIPT.md`
- Modify: `docs/build-week/assets/modori-build-week-demo.en.srt`
- Modify: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/generate-demo-voice.ps1`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/caption-labels.psd1`

**Interfaces:**
- Consumes: the frozen 12-cue table in `docs/superpowers/specs/2026-07-21-build-week-human-problem-demo-reedit-design.md`.
- Produces: twelve `cue-NN.wav` files, one exact 175-second SRT, and a short-label manifest consumed by the video build.

- [ ] **Step 1: Replace the old shot table with the frozen 12-cue story**

Copy the timing, exact English narration, Korean meaning, capture rules, and acceptance gates from the approved design into `docs/build-week/DEMO_SCRIPT.md`. Retain the existing launcher, dataset, result, Word-report, and suite hashes unchanged.

- [ ] **Step 2: Replace the SRT with exact cue boundaries**

Use these endpoints exactly:

```text
00:00:00,000 --> 00:00:06,000
00:00:06,000 --> 00:00:18,000
00:00:18,000 --> 00:00:30,000
00:00:30,000 --> 00:00:44,000
00:00:44,000 --> 00:01:02,000
00:01:02,000 --> 00:01:22,000
00:01:22,000 --> 00:01:38,000
00:01:38,000 --> 00:01:55,000
00:01:55,000 --> 00:02:08,000
00:02:08,000 --> 00:02:31,000
00:02:31,000 --> 00:02:48,000
00:02:48,000 --> 00:02:55,000
```

The twelve ranges correspond one-to-one with the twelve visual/narration rows in the
approved design. The final close is its own seven-second subtitle and audio cue.

- [ ] **Step 3: Update the local SAPI source**

Replace `$cues` in `generate-demo-voice.ps1` with the exact English narration. Start with SAPI rates `@(0, -1, -1, -1, -1, -1, -1, 0, 0, -1, -1, 0)` for the twelve subtitle/audio slots and preserve Microsoft Zira Desktop as the offline English voice.

- [ ] **Step 4: Define only the short burned-in labels**

Create `caption-labels.psd1` with this closed content:

```powershell
@{
    Opening = @('ASKS BEFORE IT CALCULATES', 'ABSTAINS WHEN EVIDENCE IS NOT ENOUGH')
    Result = '649 PUBLIC RECORDS  ->  REVIEWABLE RESULT  ->  WORD'
    Candidate = @('ASSOCIATION ONLY', 'SPEARMAN', 'PAIRWISE MISSINGNESS')
    SecondRequest = 'SECOND REQUEST'
    CodexFlow = 'SPEC  ->  RED TEST  ->  IMPLEMENTATION  ->  WINDOWS VERIFICATION'
    Evidence = '3,393 passed  |  NIST StRD checks  |  R cross-engine anchors'
    Closing = @('MODORI ASKS  |  ABSTAINS  |  WAITS FOR RUN', 'Kindness is a system behavior.')
}
```

- [ ] **Step 5: Generate and measure every cue**

Run:

```powershell
& '.visual-qa\build-week-real-data-candidate-2026-07-21\video\generate-demo-voice.ps1'
```

Expected: twelve non-empty `voice/cue-NN.wav` files. Probe each cue with FFprobe and require its spoken duration to be shorter than its assigned slot by at least 0.35 seconds; adjust only the corresponding SAPI rate if a cue exceeds its slot.

- [ ] **Step 6: Commit the canonical copy separately**

```powershell
git add docs/build-week/DEMO_SCRIPT.md docs/build-week/assets/modori-build-week-demo.en.srt
git commit -m "docs: reframe Build Week demo around human problem"
```

Expected: one docs-only commit; `.visual-qa` operational files remain untracked/ignored.

### Task 2: Capture the real causal-abstention vignette

**Files:**
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/raw-causal-abstention-20260721.mp4`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/abstention-capture-notes.txt`

**Interfaces:**
- Consumes: the exact packaged launcher and `examples/build-week-demo/student-study-and-grades.csv`.
- Produces: a privacy-clean, full-width English Guided-mode capture showing a causal request ending in `The causal-effect request is outside the current scope`.

- [ ] **Step 1: Read the Windows-control instructions before launching**

Read `C:\Users\V\.codex\plugins\cache\openai-bundled\computer-use\26.715.52143\skills\computer-use\SKILL.md` completely and follow its screenshot, focus, and safety rules.

- [ ] **Step 2: Prepare isolated state without deleting user state**

Create a new empty directory below:

```text
.visual-qa/build-week-real-data-candidate-2026-07-21/video/state-causal-abstention/LocalAppData
```

Launch the packaged executable in a child process whose `LOCALAPPDATA`, `TEMP`,
`TMP`, and `MODORI_CACHE_DIR` all point inside `state-causal-abstention`. Do not
remove or reuse the user's normal `%LOCALAPPDATA%\Modori` data.

- [ ] **Step 3: Start a 1,920 × 1,080 desktop capture**

Use the bundled FFmpeg executable with `gdigrab`, constant 30 fps, H.264, and no desktop audio. Record only after notifications are disabled and unrelated windows are hidden.

```powershell
& $ffmpeg -hide_banner -loglevel warning -y -f gdigrab -framerate 30 `
  -offset_x 0 -offset_y 0 -video_size 1920x1080 -i desktop `
  -c:v libx264 -preset ultrafast -crf 16 -pix_fmt yuv420p `
  '.visual-qa\build-week-real-data-candidate-2026-07-21\video\raw-causal-abstention-20260721.mp4'
```

- [ ] **Step 4: Drive one real causal request**

In English Guided Mode, import the verified 649-row CSV, confirm the same two
variable meanings, open Research OS, select causal-effect intent, retain the causal
request, and stop only after the English abstention title and body are fully visible.
Do not switch to the noncausal recovery action during this capture.

- [ ] **Step 5: Stop capture and record exact source interval**

Probe the MP4, inspect a contact sheet, and record in `abstention-capture-notes.txt`
the exact start/duration that begins with the causal choice and ends after at least
2.5 seconds on the abstention card. Record the MP4 SHA-256 and confirm that no private
path, native file picker, notification, or unrelated application is visible.

### Task 3: Rebuild the visual edit without extreme speed ramps

**Files:**
- Modify: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/build-demo-video.ps1`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/segment-speed-audit.csv`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/modori-build-week-demo-human-problem-visual-175s.mp4`

**Interfaces:**
- Consumes: the successful raw capture, causal-abstention raw capture, Word report PNG, caption labels, and frozen timing table.
- Produces: one exact 5,250-frame silent visual master and a CSV proving every continuous speed factor is at most 1.25x.

- [ ] **Step 1: Replace the old 27-segment manifest**

Build twelve cue groups matching the frozen endpoints. Use short 1.0x source excerpts
before and after slow UI waits instead of compressing an entire wait. Each segment
entry must include `Cue`, `Name`, `Input`, `Start`, `SourceDuration`,
`OutputDuration`, and `Purpose`.

- [ ] **Step 2: Add a fail-closed speed assertion**

Before rendering each moving source segment, calculate:

```powershell
$speed = $segment.SourceDuration / $segment.OutputDuration
if ($speed -gt 1.25) {
    throw "Segment $($segment.Name) exceeds the 1.25x speed ceiling: $speed"
}
```

Images and generated cards are exempt because they are not time-warped recordings.
Write every segment's source duration, output duration, and speed to
`segment-speed-audit.csv`.

- [ ] **Step 3: Generate intentional brand cards**

Use FFmpeg `color=c=0x06111F:s=1920x1080:r=30`, Segoe UI, Royal Blue
`0x3166B7`, and warm white `0xF7F3EA`. Animate only opacity and a small horizontal
reveal. The opening lasts six seconds and the closing lasts seven seconds. Do not
place either card over the Modori entry screen.

- [ ] **Step 4: Build the Codex evidence montage**

Create a 23-second privacy-clean dark montage with these four timed stages and no
private chat transcript:

```text
SPEC              Variable Meaning Gate · ledger authority · separate Run
RED TEST          test_prepare_confirm_and_run_remain_three_distinct_actions
IMPLEMENTATION    Excel recovery · safe Word export · failure recovery
VERIFICATION      3,393 passed · NIST StRD checks · R cross-engine anchors
```

Use gentle vertical movement or progress-line animation so the sequence reads as an
engineering process, not four unrelated stills.

- [ ] **Step 5: Render and enforce frame counts**

Render every segment at 30 fps with an exact integer `-frames:v` value, concatenate
with stream copy, and require the silent visual master to report exactly 5,250 frames
and 175.000 seconds.

### Task 4: Assemble audio, captions, and final MP4

**Files:**
- Modify: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/build-demo-video.ps1`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/modori-build-week-demo-human-problem-voiceover-175s.wav`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/modori-build-week-demo-human-problem-en-175s.mp4`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/modori-build-week-demo-human-problem.en.srt`

**Interfaces:**
- Consumes: twelve measured voice cues, silent visual master, and the canonical SRT.
- Produces: the upload candidate and separate YouTube captions.

- [ ] **Step 1: Pad each cue to its exact slot**

Use `apad`, `atrim`, and `aresample=48000` for the twelve durations
`@(6,12,12,14,18,20,16,17,13,23,17,7)`. Concatenate to exactly 175 seconds.

- [ ] **Step 2: Mix without burned full subtitles**

Mux the silent visual and voiceover, applying:

```text
loudnorm=I=-16:LRA=11:TP=-1.5
```

Encode H.264 High-compatible `yuv420p`, AAC 192 kbps, 48 kHz stereo, square pixels,
30 fps, and `+faststart`. Do not apply the old `subtitles=` filter. Copy the complete
SRT next to the MP4 for YouTube upload.

- [ ] **Step 3: Verify exact media structure**

Require FFprobe to report 1,920 × 1,080, 30/1 fps, 5,250 frames, 175.000 seconds,
H.264 video, AAC stereo audio at 48 kHz, and sample aspect ratio 1:1.

### Task 5: Perform evidence-based visual and technical QA

**Files:**
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/qa/human-problem-final/contact-sheet.png`
- Create: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/qa/human-problem-final/frame-*.png`
- Modify: `docs/build-week/VIDEO_VERIFICATION.md`

**Interfaces:**
- Consumes: the final MP4, SRT, speed audit, source hashes, and existing product evidence.
- Produces: a claim-bounded verification record suitable for the submission packet.

- [ ] **Step 1: Decode the complete MP4**

Run FFmpeg with `-f null NUL` and require exit zero. Run `blackdetect` and manually
classify only the intentional branded opening/closing cards; no unintended black gap
may exceed 0.25 seconds.

- [ ] **Step 2: Measure audio**

Run `ebur128`/`volumedetect`; record integrated loudness and peak. Require integrated
loudness close to `-16 LUFS` and peak no higher than `-1.5 dBTP`.

- [ ] **Step 3: Generate one frame per editorial beat**

Extract frames at seconds `2, 10, 24, 36, 52, 72, 92, 110, 122, 139, 157, 171`
and assemble a labeled contact sheet. Inspect original-resolution frames for crop,
legibility, overlay obstruction, correct result values, successful/second-request
separation, and privacy.

- [ ] **Step 4: Watch the full candidate at normal speed**

Open the exact MP4 locally and manually check that no action appears unnaturally fast,
the first product interaction begins at 18 seconds, each key state holds at least 2.5
seconds, and the Codex montage reads as evidence rather than apology or self-criticism.

- [ ] **Step 5: Record immutable evidence**

Update `docs/build-week/VIDEO_VERIFICATION.md` with final path, byte count, SHA-256,
SRT SHA-256, codec/frame/audio probes, decode exit, black scan, speed audit maximum,
frame-review result, exact source footage hashes, and any remaining manual uncertainty.

- [ ] **Step 6: Commit the final documentation packet**

```powershell
git add docs/build-week/DEMO_SCRIPT.md docs/build-week/VIDEO_VERIFICATION.md docs/build-week/assets/modori-build-week-demo.en.srt docs/superpowers/specs/2026-07-21-build-week-human-problem-demo-reedit-design.md docs/superpowers/plans/2026-07-21-build-week-human-problem-demo-reedit.md
git commit -m "docs: verify human-problem Build Week demo"
```

Expected: a docs-only commit. Do not push it or change any release branch.

### Task 6: Hand off only the upload-ready packet

**Files:**
- Read: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/modori-build-week-demo-human-problem-en-175s.mp4`
- Read: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/modori-build-week-demo-human-problem.en.srt`
- Read: `docs/build-week/VIDEO_VERIFICATION.md`

**Interfaces:**
- Consumes: the verified final packet.
- Produces: exact upload instructions without performing a YouTube upload or public repository push.

- [ ] **Step 1: Report the exact files and hashes**

Provide clickable absolute paths for the MP4, SRT, canonical script, and verification
record. State the exact MP4/SRT SHA-256 values and duration.

- [ ] **Step 2: Keep external publication under the user's control**

Do not upload to YouTube, edit Devpost, push Git, or change the default branch. Give the
user the upload order: MP4, manual SRT captions, Public visibility, signed-out playback
check, then Devpost URL entry.
