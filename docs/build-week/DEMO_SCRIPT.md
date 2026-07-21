# Modori Build Week Demo — Final Recording Master

Final duration: **2 minutes 47.167 seconds**

Broadcast language: **English narration with matching English subtitles**

Operator aid: **Korean meaning is supplied for every cue below**

Demo data: `examples/build-week-demo/student-study-and-grades.csv`

Source: Cortez (2008), UCI Student Performance, Portuguese-course table,
649 released records, CC BY 4.0, DOI `10.24432/C5TG7T`

This is the canonical result-first script. The video opens with the creator's
motivation, reveals the actual result at `00:02.500`, then demonstrates the path
that produced it. The successful association task and the later causal request are
visibly separate tasks. No competitor interface, price, currency conversion, logo,
private identity, or private path appears.

## Candidate bound to this packet

- product source-under-test: `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b`
- packaged launcher SHA-256:
  `f539c9ae698fcc2f7b6cc5a0bc634aa9607a415993ccb4e83d5e8a507770c8d5`
- demo CSV SHA-256:
  `e51ebf09f537865aa7353f3b23cfa391e75767783d0061b628c1361eaef4cb0e`
- demonstrated English Word report: `37,343` bytes, SHA-256
  `6343649e5fbf39adf1c212ac2495e8e59e8490494b57b35f562a3e5719651d31`
- demonstrated result: Spearman `rho = 0.2747118483356099`, two-sided
  `p = 1.060624038270125e-12`, `n = 649`, excluded rows `= 0`
- final source suite: `3,393 passed, 5 skipped in 500.66s`, exit `0`

The interface displays rounded `rho = 0.275` and `p = 0.000`. Narration says
`p below .001`; it never describes the p-value as literally zero. The result is an
association in the released records, not a causal effect or population estimate.

## Narration and timing source

All cue boundaries come from the locally rendered speech plus a fixed 0.75-second
transition tail, aligned to 30 fps. The single voice is Kokoro ONNX `af_sarah` at
global speed `0.92`; no per-cue speed changes are permitted. Product excerpts run
at `1.0x`; waiting and file-picker footage are removed with hard cuts.

## Exact shot list, narration, and Korean meaning

| Time | Screen and action | Exact English narration / subtitle | 한국어 의미 |
| --- | --- | --- | --- |
| 00:00.000–00:13.867 | Near-black navy card for 2.5 seconds: `THE QUESTION CAME FIRST.` and `APPROACHABLE · SUBSCRIPTION-FREE · LOCAL`; narration begins immediately. Cut to the actual result and report at 00:02.500. | **“I majored in sociology and will soon begin graduate school. I wanted an approachable, subscription-free statistics tool—and I want other students to have that same ease. That idea became Modori.”** | “저는 사회학을 전공했고 곧 대학원에 진학합니다. 부담 없이 사용할 수 있는 구독료 없는 통계 도구를 원했고, 다른 학생들도 같은 편리함을 누리기를 바랍니다. 그 생각이 Modori가 되었습니다.” |
| 00:13.867–00:27.800 | Actual Spearman result and matching editable report. | **“Here is the payoff: 649 released student records reach a reviewable Spearman result and an editable report. Method, coefficient, p-value, sample size, and exclusions stay visible.”** | “결과부터 보겠습니다. 공개된 학생 기록 649건이 검토 가능한 스피어만 결과와 편집 가능한 보고서로 이어집니다. 분석법, 계수, p값, 표본 수, 제외된 행이 모두 보입니다.” |
| 00:27.800–00:40.267 | Select Guided Mode, show the labeled 30-row preview, then the full 649-row data view. Display the text-only dataset attribution. | **“Now the path. I open a six-variable, non-identifying view, review the labeled thirty-row preview, then load all 649 records. The data stays on this computer.”** | “이제 그 과정을 보겠습니다. 식별정보가 없는 6개 변수 데이터를 열고, 명확히 표시된 30행 미리보기를 확인한 뒤 649건 전체를 불러옵니다. 데이터는 이 컴퓨터 안에 머뭅니다.” |
| 00:40.267–00:53.033 | Review study time as ordinal and final grade as scale, then show the Variable Meaning Gate. | **“Before any method appears, Modori asks what the variables mean. Study time is ordinal; final grade is scale. Labels, value codes, missing rules, and storage type are reviewed first.”** | “어떤 분석법도 제시되기 전에 Modori는 변수의 의미부터 묻습니다. 학습시간은 순서형이고 최종 성적은 척도형입니다. 라벨, 값 코드, 결측 규칙, 저장 형식을 먼저 검토합니다.” |
| 00:53.033–01:06.100 | Choose the co-movement task, assign exact roles, then show the bounded questions in actual ledger order: clustering, dependence, weights. | **“I begin with the research task: do study time and grades move together? I assign exact roles. Modori then asks bounded questions about clustering, dependence, and weights instead of guessing.”** | “분석법 이름이 아니라 연구과업에서 시작합니다. 학습시간과 성적이 함께 움직이는지를 묻고 정확한 변수 역할을 지정합니다. Modori는 임의로 추측하지 않고 군집, 의존 구조, 가중치에 관한 제한된 질문을 합니다.” |
| 01:06.100–01:20.467 | Show the Spearman candidate, experimental status, association boundary, variables, missingness policy, and exact configuration. | **“The candidate is Spearman correlation. Its association-only claim, experimental status, variables, missing-data policy, and exact parameters remain visible. Nothing is silently selected or run.”** | “후보는 스피어만 상관분석입니다. 연관성에 한정된 주장 범위, 실험적 상태, 변수, 결측 처리 정책과 정확한 파라미터가 계속 보입니다. 어떤 것도 몰래 선택되거나 실행되지 않습니다.” |
| 01:20.467–01:35.600 | Prepare, inspect the exact configuration, confirm it, hold on the empty result, then use the separately enabled Run and reveal the result. | **“Prepare exposes the configuration and keeps the result empty. Confirmation authorizes without calculating. Only the separate Run produces rho zero point two seven five, with p below point zero zero one.”** | “Prepare는 구성을 보여주고 결과를 비워 둡니다. 확인은 계산 없이 구성을 승인합니다. 별도의 Run을 선택해야만 로 0.275, p값 0.001 미만의 결과가 생성됩니다.” |
| 01:35.600–01:47.833 | Label `SECOND REQUEST`, choose causal-effect intent in a fresh task, and show the causal-abstention title, explanation, and decision basis. | **“For a causal-effect request, Modori gives a clear scope decision. It records the request instead of substituting a convenient analysis. Abstention is a product behavior.”** | “인과효과를 요청하면 Modori는 명확한 범위 결정을 내립니다. 편리한 다른 분석으로 바꾸지 않고 원래 요청을 기록합니다. 기권은 제품의 실제 행동입니다.” |
| 01:47.833–02:06.900 | Evidence cards: `PRODUCT QUESTION → CONTRACT → RED TEST → IMPLEMENTATION → PACKAGED APP`, followed by `VARIABLE MEANING`, `PASSPORT + LEDGER`, and `PREPARE ≠ CONFIRM ≠ RUN`. | **“With Codex and GPT-5.6, I turned product decisions into contracts, failing tests, implementation, and packaged-app verification. That collaboration established the Variable Meaning Gate, passport-and-ledger authority, and separate Prepare, Confirm, and Run boundaries.”** | “Codex와 GPT-5.6을 활용해 제품 결정을 계약, 실패 테스트, 구현, 패키징된 앱 검증으로 전환했습니다. 이 협업을 통해 Variable Meaning Gate, passport와 ledger에 기반한 권한, 그리고 분리된 Prepare·Confirm·Run 경계가 구축되었습니다.” |
| 02:06.900–02:21.433 | Three actual regression chains: empty first worksheet recovery, safe report replacement, and actionable failure recovery. | **“That loop also closed real interface failures: recovering a workbook whose first sheet held no data, protecting an existing report during replacement, and replacing a generic failure card with an actionable recovery path.”** | “그 과정은 실제 인터페이스의 실패도 해결했습니다. 첫 시트에 데이터가 없는 통합문서를 복구하고, 기존 보고서를 교체할 때 원본을 보호하며, 일반적인 실패 카드를 실행 가능한 복구 경로로 바꾸었습니다.” |
| 02:21.433–02:35.800 | Integration cards: seven ordered UI commits, 25 overlapping paths, 12 predicted conflicts, semantic review, final source suite, and separate NIST/R calculation checks. | **“Seven Royal Blue interface commits were integrated path by path across the existing codebase. The source suite passed, while external reference checks supported calculation separately from recommendation boundaries.”** | “Royal Blue 인터페이스 커밋 7개를 기존 코드베이스에 경로별로 통합했습니다. 소스 테스트가 통과했고, 외부 기준 검사는 추천 경계와 분리된 계산을 뒷받침했습니다.” |
| 02:35.800–02:47.167 | Reconnect question, Run, and result, then close on `MODORI`, `FROM QUESTION TO REVIEWABLE ACTION`, and `KINDNESS IS SYSTEM BEHAVIOR`. | **“Modori turns a research question into a reviewable path, then leaves the final action to the researcher. Kindness is not decoration. It is system behavior.”** | “Modori는 연구 질문을 검토 가능한 경로로 바꾸고 최종 행동은 연구자에게 남겨둡니다. 친절은 장식이 아닙니다. 시스템의 행동입니다.” |

## Demonstrated operator sequence

1. `English` → `GUIDED MODE` → `Open data file`.
2. Open `student-study-and-grades.csv`; cut past the native picker.
3. Review the clearly labeled 30-row, six-variable preview and import all rows.
4. Verify the separate data view reports `rows 1–17 / 649 · columns 1–6 / 6`.
5. Review `weekly_study_time_band` as `Weekly study time`, `Ordinal`, with its four
   value labels; review `final_grade` as `Final grade`, `Scale`.
6. Start Research OS → noncausal → rank-based co-movement.
7. Assign outcome `final_grade` and focal predictor `weekly_study_time_band`.
8. Confirm the Variable Meaning Gate.
9. Record clustering, dependence, and weight answers in that order.
10. Review the Spearman candidate and exact `pairwise` / `p_adjust: none` settings.
11. Prepare and confirm; verify that the result remains empty and Run is separate.
12. Choose Run, open the wide result, and verify `rho 0.275`, `p 0.000`, `n 649`,
    and excluded `0`; show the matching Word report.
13. Start a separate causal task and hold on the explicit abstention decision basis.

## Acceptance status

- [x] `167.170` measured seconds, 5,015 decoded frames, constant 30 fps.
- [x] Result visible at `00:02.500`; subtitle endpoint `00:02:47,167`.
- [x] All moving product excerpts are `1.0x`.
- [x] H.264 High/yuv420p, 1,920 × 1,080, square pixels; AAC-LC 48 kHz stereo.
- [x] Integrated loudness `-16.12 LUFS`, true peak `-1.93 dBTP`, no detected
      silence interval at or above 1.25 seconds.
- [x] Original-resolution review covers 38 frames and all story groups; the first
      contradictory Guided/Pro cut was rejected and rebuilt from the verified
      Guided selection.
- [x] Every current release-facing story uses the single final source-suite count.
- [x] Final handoff directory contains only one MP4 and one matching SRT.
- [ ] Owner watches the exact hashed MP4 once at normal speed with sound.
- [ ] YouTube upload is Public and opens in a signed-out browser.

Exact media hashes and the remaining external boundary are recorded in
[`VIDEO_VERIFICATION.md`](VIDEO_VERIFICATION.md).
