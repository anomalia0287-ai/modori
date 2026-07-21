# Modori Build Week Demo — Local Video Verification

Verified on 2026-07-21 (Asia/Seoul).

## Bound product evidence

- Product source-under-test: `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b`
- Packaged launcher SHA-256:
  `f539c9ae698fcc2f7b6cc5a0bc634aa9607a415993ccb4e83d5e8a507770c8d5`
- Demo CSV SHA-256:
  `e51ebf09f537865aa7353f3b23cfa391e75767783d0061b628c1361eaef4cb0e`
- Generated Word report: `37,343` bytes; SHA-256
  `64e6f8ea663b7438be56c4cca5565292e9c70a63e2d4360a6877923fcb075ac6`

## Final local upload candidate

- File: `.visual-qa/build-week-real-data-candidate-2026-07-21/video/modori-build-week-demo-result-first-en-175s.mp4`
- Size: `11,154,958` bytes
- SHA-256: `a759c91e745c16eabe36687996798aec5bea3f051ab7d66fd108a7efe97b2fdf`
- Duration: exactly `00:02:55.00`
- Video: H.264 High, 1,920 × 1,080, square pixels, 30 fps, yuv420p
- Exact video count: `5,250` decoded frames
- Audio: AAC-LC, 48 kHz, stereo; mean `-19.5 dB`, peak `-1.5 dB`
- Full video/audio decode: exit 0, no reported decode errors
- Black-frame detector: zero intervals

The 27 visual segments were independently decoded. Every segment contained exactly
`planned seconds × 30` frames, and both the concatenated visual stream and final
subtitle/audio render contained 5,250 frames. This check caught and corrected an
earlier edit where a 25 fps still input and per-segment end-frame loss shortened the
visual stream while the audio container still reported 2:55.

## Script, voice, and subtitles

- Narration text is the exact English text in `docs/build-week/DEMO_SCRIPT.md` and the
  canonical SRT.
- Voice was synthesized locally with the installed Microsoft Zira Desktop voice.
- Cue 2 is `15.56` seconds inside its 16-second slot; all 11 voice cues are shorter
  than their allocated slots.
- Canonical and sidecar SRT files are byte-identical: `2,484` bytes, SHA-256
  `95a5af648a9484e6915692a5789e857ad3e25def94c54685486bcfe2afd5d72e`.
- The SRT contains 11 cues and ends at `00:02:55,000`.

## Motion and framing audit

- `164` seconds are sourced from the actual 1,920 × 1,080 Modori interaction
  recording. The remaining `11` seconds show the actual generated Word report.
- Product shots preserve all 1,920 source pixels horizontally. Only the 30-pixel
  Windows title bar and 60-pixel taskbar are removed; 45-pixel top/bottom padding
  preserves a 16:9 frame without side cropping or stretching.
- Representative full-resolution frames retain the complete `MODORI` wordmark,
  language/mode controls, right-side result panel, and bottom-right Run action.
- The Word report is rendered from the hashed DOCX through Microsoft Word, not
  recreated as a mock. Its complete 10-column result row, warning, and interpretation
  boundary remain legible without Word ribbon or add-in chrome.
- Both report cutaways use a restrained 1.000 → 1.025 zoom. Different start/end frame
  hashes independently confirm motion while preserving all content.

## Codex contribution claim audit

The 00:18–00:34 cue presents three timed cards over the real Modori entry recording:

1. `Engineered with Codex + GPT-5.6`
2. `Meaning Gate | passport / ledger | separate Run`
3. `Excel recovery | safe Word export | failure recovery` and
   `3,393 tests passed`

The matching narration identifies development and testing work during Build Week. It
does not imply that a generative model performs the released statistical calculation.
The full design/code/test/commit evidence is recorded in
`docs/build-week/CODEX_CONTRIBUTION_EVIDENCE.md`.

## Visual claim and privacy audit

- Opening and later result shots show the same displayed `rho = 0.275`, `p = 0.000`,
  `n = 649`, and `excluded_n = 0`.
- Import review distinguishes the 30-row preview from the complete 649-row import.
- Variable Meaning Gate, bounded questions, experimental candidate, exact Spearman
  configuration, confirmation with an empty result, separate Run, result, and Word
  output are visible.
- No causation, universal-validity, expert-equivalence, representativeness, or
  SPSS-superiority claim is made.
- Native file-picker footage, desktop taskbar, notifications, account identity,
  session transcript, API keys, and personal recent-file lists are absent.

## Still requiring human or external action

- Watch the exact hashed MP4 once at normal speed with sound to judge subjective voice
  naturalness, pronunciation, and pacing.
- Upload that exact file as Public and verify the URL in a signed-out browser.
- Complete the submission form and preserve its confirmation receipt.
- Fable 5 external-participant verification remains separate and unclaimed.
