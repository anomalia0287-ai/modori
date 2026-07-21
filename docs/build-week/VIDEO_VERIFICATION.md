# Modori Build Week Demo — Local Video Verification

Verified on 2026-07-21 (Asia/Seoul).

## Bound product evidence

- Product source-under-test: `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b`
- Packaged launcher SHA-256:
  `f539c9ae698fcc2f7b6cc5a0bc634aa9607a415993ccb4e83d5e8a507770c8d5`
- Demo CSV SHA-256:
  `e51ebf09f537865aa7353f3b23cfa391e75767783d0061b628c1361eaef4cb0e`
- Generated Word report:
  `.visual-qa/build-week-real-data-candidate-2026-07-21/reports/report-ca379fd-final.docx`;
  `37,343` bytes; SHA-256
  `6343649e5fbf39adf1c212ac2495e8e59e8490494b57b35f562a3e5719651d31`
- Demonstrated result: Spearman `rho = 0.2747118483356099`, two-sided
  `p = 1.060624038270125e-12`, `n = 649`, excluded rows `= 0`

## Final local upload candidate

- File: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/modori-build-week-demo-human-problem-en-paced.mp4`
- Size: `9,132,762` bytes
- SHA-256: `901503954cad536c2ea368bb63bb73b8b19fa7df247d6e396f0566987d04d32f`
- Duration: exactly `00:02:05.03` (`125.033` seconds)
- Video: H.264 High, 1,920 × 1,080, square pixels, 30 fps, yuv420p
- Exact video count: `3,751` decoded frames
- Audio: AAC-LC, 48 kHz, stereo; FFmpeg `loudnorm` first-pass input
  measurements are integrated `-15.93 LUFS`, true peak `-1.50 dBTP`, and
  loudness range `2.90 LU`
- Full video/audio decode: exit 0, no reported decode errors

The 25 visual clips were independently rendered at the frame-aligned duration of
their matching narration cue. The render script probes each rendered utterance,
removes only the synthesizer's trailing silence, adds a fixed `0.75`-second tail,
and derives the video and subtitle boundaries from that result. It rejects a final
timeline at or above three minutes and any moving excerpt above 1.25×. The final
timeline uses 1.0× for every moving Modori excerpt; waiting and cursor travel are
removed by ordinary hard cuts.

The black-frame detector reported only three short `0.100–0.333` second intervals at
intentional brand-card fades near `94.87`, `118.47`, and `124.67` seconds.
Full-resolution source frames confirm that the surrounding shots are designed
near-black navy cards with visible copy, not blank or missing video.

The superseded `modori-build-week-demo-human-problem-en-175s.mp4` candidate and its
SHA-256 `bd66d76db468c52caa535bbfccba57cebab2639ab262ae7ce10860e7f1e67189`
are withdrawn and must not be uploaded. Its opening cue used a different speech
rate, and the media gate detected ten silence intervals over 1.25 seconds, with a
maximum of 7.26 seconds.

## Script, voice, and subtitles

- Narration text is the exact spoken English meaning in
  `docs/build-week/DEMO_SCRIPT.md` and the canonical SRT. The rendering script loads
  the same cue text source used by the voice generator.
- Voice was synthesized locally with the installed Microsoft Zira Desktop voice.
- All 12 utterances use the single default SAPI rate `0`; per-cue rate overrides are
  rejected by the pacing test.
- The synthesizer contributed `0.81–0.92` seconds of trailing silence per raw WAV.
  That trailing silence was removed before the deterministic tail was added.
- The actual frame-aligned tail margins are `0.750–0.777` seconds. A full-media
  `silencedetect` scan at `-40 dB` found a maximum interval of `0.927` seconds and no
  interval over the enforced `1.25`-second limit.
- The canonical UTF-8/LF SRT is `2,129` bytes with SHA-256
  `4115d86f67de91cfe061d7effde485bb64e83ff240a60fe69d70b6788b941c09`.
- The SRT contains 12 non-overlapping cues and ends at `00:02:05,033`.
- The MP4 burns only short marketing labels. The complete narration remains in the
  separate SRT for YouTube captions.

## Motion, framing, and visual audit

- The edit combines actual Modori interaction footage, a fresh isolated causal
  request take, the actual generated Word report, and intentional branded evidence
  cards. No product footage is accelerated.
- Product shots preserve all 1,920 source pixels horizontally. Only the 30-pixel
  Windows title bar and 60-pixel taskbar are removed; 45-pixel top/bottom padding
  preserves a 16:9 frame without side cropping or stretching.
- The 30-row import review is followed by the separate `Open data sheet` view whose
  footer visibly reads `rows 1–17 / 649 · columns 1–6 / 6`.
- Representative full-resolution frames retain the complete `MODORI` wordmark,
  mode controls, right-side result panel, and bottom-right Run action.
- The Word report is rendered from the hashed DOCX through Microsoft Word, not
  recreated as a mock. Its complete 10-column result row, warning, and interpretation
  boundary remain legible without Word ribbon or add-in chrome.
- A fresh Microsoft Word export of that DOCX, rasterized again at 144 dpi, produced
  a byte-identical `page-1.png` to the frame source used by the edit: SHA-256
  `796f4a3d5c402e00f1383b40e4529d0500d345c13a8449848919903521cef239`.
- Both Word cutaways use a restrained 1.000 → 1.018 zoom while preserving the result
  content.
- A 16-frame full-timeline contact sheet and 16 exact gallery candidates were
  inspected after the paced render. The frames cover result, Word report, import
  review, 649-row data sheet, Variable Meaning Gate, bounded questions, candidate,
  Prepare, result, causal abstention, all three engineering cards, report export,
  and closing card. Earlier review had already rejected candidates that stopped at
  the causal scope notice or confused the 30-row preview with the 649-row sheet.

## Codex contribution claim audit

The 01:29.633–01:47.067 montage names the demonstrated engineering sequence and
boundaries:

1. `SPEC > RED TEST > IMPLEMENTATION > WINDOWS VERIFICATION`
2. `VARIABLE MEANING GATE`, `PASSPORT + LEDGER`, and `PREPARE > RUN`
3. `EXCEL RECOVERY`, `SAFE WORD EXPORT`, `FAILURE RECOVERY`, and
   `3,393 TESTS PASSED`

The narration says Codex with GPT-5.6 helped turn product questions into contracts,
failing tests, implementation, and Windows verification during Build Week. It does
not imply that a generative model performs the released statistical calculation.
The design/code/test/commit evidence is recorded in
`docs/build-week/CODEX_CONTRIBUTION_EVIDENCE.md`.

## Fresh final source-suite confirmation

After the final media packet was rendered, the source-under-test tree was checked
again on 2026-07-21 with CPython 3.12.10 and the pinned R 4.5.3 runtime. The run used
isolated application, temporary, and cache roots; `QT_QPA_PLATFORM=offscreen`; a
700-second hard limit; and BelowNormal process priority.

The submission source suite excluded the visual-gallery timing test and the
branch-history integration-ledger validator:

```text
python -m pytest -q -p no:cacheprovider --color=no \
  --ignore=tests/ui/test_research_flow_visual_gallery.py \
  --ignore=tests/test_research_os_royal_blue_integration_ledger.py tests
```

Result: `3,393 passed, 5 skipped in 500.66s`, exit `0`. The wrapper completed in
`505.7s`, inside the fixed 700-second limit. The captured stdout log is `3,933`
bytes with SHA-256
`19906ee7ff2adeb44ef3b134c09d71cff52ed7a5b2a449e08440f7c859f38267`.
The source and test trees were unchanged from `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b`.

## Visual claim and privacy audit

- Opening and later result shots show the same displayed `rho = 0.275`, `p = 0.000`,
  `n = 649`, and `excluded_n = 0`. Narration correctly says `p below .001`; it does
  not describe the p-value as literally zero.
- Import review, the 649-row data sheet, Variable Meaning Gate, bounded questions,
  experimental candidate, exact Spearman configuration, confirmation with an empty
  result, separate Run, result, explicit causal abstention, and Word output are
  visible.
- The causal vignette uses a fresh isolated application state and ends on
  `Causal request abstained`, the no-candidate explanation, and its decision basis.
- No causation, universal-validity, expert-equivalence, representativeness,
  NIST-certification, or SPSS-superiority claim is made.
- Native file-picker footage, desktop taskbar, notifications, account identity,
  private path, session transcript, API key, and personal recent-file list are absent.
- The public UCI records shown in the app contain only the six approved demo columns;
  no private user dataset is used.

## Still requiring human or external action

- Watch the exact hashed MP4 once at normal speed with sound to judge subjective voice
  naturalness, pronunciation, and pacing.
- Upload that exact file as Public and verify the URL in a signed-out browser.
- Complete the submission form and preserve its confirmation receipt.
- Fable 5 external-participant verification remains separate and unclaimed.
