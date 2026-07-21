# Modori Build Week Demo — Final Local Verification

Verified on 2026-07-21 (Asia/Seoul).

Status: **machine gates pass; original-resolution visual review passes; owner audio
playback and external publication remain open**.

## Bound product evidence

- product source-under-test: `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b`
- current `src` tree: `b9ab6799414f2238cc627a2b79a3e215b758f3e5`
- current `tests` tree: `f87bd2683e4fd5536c5df205fc85b165de1edfce`
- packaged launcher SHA-256:
  `f539c9ae698fcc2f7b6cc5a0bc634aa9607a415993ccb4e83d5e8a507770c8d5`
- demo CSV SHA-256:
  `e51ebf09f537865aa7353f3b23cfa391e75767783d0061b628c1361eaef4cb0e`
- demonstrated Word report: `37,343` bytes, SHA-256
  `6343649e5fbf39adf1c212ac2495e8e59e8490494b57b35f562a3e5719651d31`
- demonstrated result: Spearman `rho = 0.2747118483356099`, two-sided
  `p = 1.060624038270125e-12`, `n = 649`, excluded rows `= 0`
- final source suite: `3,393 passed, 5 skipped in 500.66s`, exit `0`

The result is an association in the released records. Current UI displays rounded
`rho = 0.275` and `p = 0.000`; narration correctly says `p below .001`.

## Exact two-file handoff

Directory:
`.visual-qa/build-week-real-data-candidate-2026-07-21/upload-master/`

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `modori-build-week-final.mp4` | 11,742,736 | `fc25ead3874d38afa99715c616a0c263945d1c156774a06e1b994bc083be104d` |
| `modori-build-week-final.en.srt` | 2,737 | `c91f660a1fa501b2738c519ecb013f7824589cb4c9cfd18226846b02426cf02e` |

The directory contains exactly these two files. The MP4 and SRT are byte-identical
to the candidate outputs accepted by the verifier.

## Media gates

- duration: `167.170` seconds (`00:02:47.170` probe duration)
- exact video count: `5,015` decoded frames
- video: H.264 High, yuv420p, 1,920 × 1,080, SAR 1:1, constant 30 fps
- audio: AAC-LC, 48 kHz, stereo
- integrated loudness: `-16.12 LUFS`
- true peak after AAC encoding: `-1.93 dBTP`
- silence scan: no interval at or above the enforced `1.25` seconds
- full audio/video decode: exit `0`
- MP4 atom order: `moov` precedes `mdat` (fast start)
- black-frame scan: no reported black interval at the 0.5-second gate
- result reveal: `00:02.500`
- maximum moving-product speed: `1.0x`
- subtitle cues: 12 contiguous, non-overlapping UTF-8/LF blocks
- subtitle endpoint: `00:02:47,167`, within one frame of the media endpoint

The verifier is
`.visual-qa/build-week-real-data-candidate-2026-07-21/video/verify-final-demo.ps1`.
Its machine report, probe, loudness scan, silence scan, black scan, frame index,
contact sheet, and source hashes are retained under
`.visual-qa/build-week-real-data-candidate-2026-07-21/video/qa/final-upload-master/`.

## Voice provenance

- engine: `kokoro-onnx-local`
- package: `kokoro-onnx 0.5.0`
- voice: `af_sarah`
- one global speed: `0.92`
- narration synthesis network use: `false`
- wrapper license: MIT
- model license: Apache-2.0
- model SHA-256:
  `7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5`
- voice-data SHA-256:
  `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`
- voice manifest SHA-256:
  `993ffc9b96a9f0ee39871b53cc59832755d74e945031b0db716bee0623963bdb`
- measured speech: `157.96` seconds
- fixed post-cue tail: `0.75` seconds, frame-aligned to `0.756–0.777` seconds

No online synthesis endpoint exists in the narration renderer. All twelve cues use
the same engine, voice, and speed; no per-cue acceleration is used.

## Source media hashes

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| successful Guided walkthrough | 37,971,147 | `cea69d367a4cba31a902230ae265b02ec78439cc9f3bf981dff66c5298d89617` |
| causal request capture | 773,034 | `8ac0134165b50237f8a4fbd799b2258b904a4cfdadb632ac334318b0da817e57` |
| causal abstention hold | 420,175 | `6d93acda40ddae54947fcfe0e88f2927fbd499c2857a244341a256fbafac70e7` |
| rendered Word report page | 55,100 | `796f4a3d5c402e00f1383b40e4529d0500d345c13a8449848919903521cef239` |
| exact cue source | 7,496 | `d472ce41502fe3878c48d78f8206dfbb6ced1df4815f3316b40fee610ce8c92d` |
| deterministic video builder | 23,862 | `2778b84ee77827967a71e6b8a01f762cd319d2104c9aad42c51b8254fb82b3d4` |

## Original-resolution visual audit

Thirty-eight 1,920 × 1,080 frames were inspected across the complete timeline. They
cover opening, result at 2.5 and 3.0 seconds, editable report, Guided selection,
30-row import review, 649-row data view, variable metadata, Variable Meaning Gate,
research task, exact roles, clustering, dependence, weights, experimental candidate,
exact configuration, Prepare, confirmed empty result, separate Run, result, fresh
causal request, abstention, every engineering card, closing result, and final card.

Verified findings:

- full product width remains visible; neither the Modori wordmark nor right-side
  controls are cropped;
- Windows title bar and taskbar are removed from the main footage;
- overlays occupy designed margins rather than covering required controls or values;
- the result and report agree on method, coefficient, displayed p-value, `n`, and
  exclusions;
- the 30-row preview and complete 649-row data view are visibly distinct;
- questions appear in the actual ledger order: clustering, dependence, weights;
- successful and causal requests are visibly separate;
- engineering cards use actual source/test names and the single current suite count;
- no private identity, private path, notification, account, API key, competitor
  price/interface, or third-party logo appears.

## Rejected intermediates

The acceptance gates rejected and corrected four defects before this hash was
accepted:

1. concat output initially contained 4,992 rather than 5,015 video frames;
2. AAC encoding initially produced `-1.42 dBTP`, above the `-1.5 dBTP` cap;
3. the first Guided label briefly covered a source frame where Pro was still
   selected; and
4. the first handoff calculation placed the two files one directory too high.

Each owning source was corrected, the complete render or verifier was rerun, and the
current two-file handoff passed all machine gates. No acceptance threshold was
lowered.

## Claim boundaries

- Seven Royal Blue UI commits, 25 overlapping paths, and 12 predicted text conflicts
  are presented as integration-ledger facts, not product-performance claims.
- NIST StRD and R are calculation references; they do not certify Modori or validate
  every recommendation.
- Codex and GPT-5.6 are described as development collaborators. The released
  statistical calculation remains deterministic and local.
- No claim of causation, universal recommendation validity, expert equivalence,
  representativeness, or competitor superiority is made.

## Still requiring owner or external action

- Watch the exact hashed MP4 once at normal speed with sound to judge voice
  naturalness, pronunciation, pacing, and the absence of subjective dead waits.
- Upload that exact MP4 to YouTube as Public with the matching English SRT.
- Verify the resulting URL in a signed-out browser.
- Complete the submission form and preserve the confirmation receipt.
- Fable 5 external-participant verification remains separate and unclaimed.
