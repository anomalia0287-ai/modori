# Modori Build Week Demo — Recording Master

Target duration: **2 minutes 55 seconds**

Broadcast language: **English voiceover with matching English subtitles**

Operator aid: **Korean meaning is supplied for every cue below**

Demo data: `examples/build-week-demo/student-study-and-grades.csv`

Source: UCI Student Performance, Portuguese-course table, 649 released records,
CC BY 4.0, DOI `10.24432/C5TG7T`

This is the canonical result-first recording script. The opening result teaser and
the later end-to-end sequence must come from the same verified data and calculation.
Normal jump cuts are allowed; the edit must not imply that a cut sequence is an
uninterrupted timing benchmark.

## Candidate bound to this packet

- source-under-test commit: `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b`
- packaged launcher: `.visual-qa/build-week-real-data-candidate-2026-07-21/onefolder-ca379fd-final/Modori/Modori.exe`
- launcher: `31,494,275` bytes, SHA-256
  `f539c9ae698fcc2f7b6cc5a0bc634aa9607a415993ccb4e83d5e8a507770c8d5`
- complete one-folder: `4,491` files, `625,478,586` bytes
- wheel: `.visual-qa/build-week-real-data-candidate-2026-07-21/wheel-ca379fd/modori-0.1.0-py3-none-any.whl`,
  `663,415` bytes, SHA-256
  `30f17c2ea96128f12786b4593c9d48ea0b103059cc45f72f549784b8862b43fb`
- derived CSV SHA-256: `e51ebf09f537865aa7353f3b23cfa391e75767783d0061b628c1361eaef4cb0e`
- demonstrated English Word report: `37,343` bytes, SHA-256
  `6343649e5fbf39adf1c212ac2495e8e59e8490494b57b35f562a3e5719651d31`
- demonstrated result: Spearman `rho = 0.2747118483356099`, two-sided
  `p = 1.060624038270125e-12`, `n = 649`, excluded rows `= 0`

The displayed table rounds the coefficient to `0.275` and the p-value to `0.000`.
The narration therefore says `p below .001`; it never describes the p-value as
literally zero.

The exact launcher completed the visible English Guided-mode path from import to
Word export. Its durable ledger passed a full integrity check with eight events,
20 artifacts, four committed passports, and head
`473eeba90f365ce5471ed997025a5ea919bf83fb871f5b53337dfda964ec5e0a`.
The final passport is experimental, grants only the association claim class, is
not auto-selected, and requires the explicit configure-confirm-run sequence.

Package evidence for this source state is also closed: `3,393 passed, 5 skipped`
in the full non-gallery suite; Ruff, Bandit, compileall, source launch, pip check,
wheel inspection, and the packaged launch, engine, and public-data smokes exited
zero. The packaged smokes completed in `7.258 s`, `23.43 s`, and `3.174 s`.

## Recording construction

Record one complete fresh-state walkthrough from entry to Word export. After that
run, copy its result-table and Word-report footage to the first 18 seconds. Continue
the edited story from the entry screen at 00:18. This gives judges the payoff first
while preserving one traceable dataset, method, and result.

Before capture:

1. Verify the launcher and CSV hashes above.
2. Use a new isolated Modori state and copy the CSV into a neutral demo directory.
3. Disable desktop notifications and keep private paths, recent files, account names,
   and unrelated windows outside the capture.
4. Select `English` and `GUIDED MODE`.
5. Pause capture for the native file picker and resume at Modori's import review.
6. Capture at 1080p or higher with text large enough to read without zooming.
7. Use the canonical subtitle file at
   `docs/build-week/assets/modori-build-week-demo.en.srt`.

## Shot list, exact narration, and Korean meaning

| Time | Screen and action | Exact English narration / subtitle | 한국어 의미 |
| --- | --- | --- | --- |
| 00:00–00:18 | **Result first.** Show the final wide result table with `rho = 0.275`, `p = 0.000`, `n = 649`, and `excluded = 0`; cut briefly to the generated English Word report. | **“Here is the result first. Across 649 public student records, weekly study-time bands and final grades show a modest positive rank association: Spearman rho point two seven five. Modori preserves the review trail and exports the result to Word locally.”** | “결과부터 보여드리겠습니다. 공개된 학생 기록 649건에서 주간 학습시간 구간과 최종 성적 사이에 약한 양의 순위 연관성이 나타났습니다. 스피어만 로는 0.275입니다. Modori는 검토 과정을 보존하고 결과를 로컬에서 Word로 내보냅니다.” |
| 00:18–00:34 | Entry screen, then a clean title card reading `Built with Codex + GPT-5.6`. Keep Modori visible for most of the cue. | **“Modori existed before Build Week. During the event, Codex with GPT-5.6 became a high-leverage engineering collaborator for building and testing this guided Windows workflow across a large existing codebase.”** | “Modori는 Build Week 이전부터 존재했습니다. 행사 기간에 Codex와 GPT-5.6은 대규모 기존 코드베이스에서 이 Windows 가이드 워크플로를 구축하고 시험하는 데 높은 생산성을 제공한 엔지니어링 협업자였습니다.” |
| 00:34–00:48 | Select `English`, choose `GUIDED MODE`, and click `Open data file`. Jump-cut past the native picker. | **“This demonstration uses UCI Student Performance: 649 public observations from the Portuguese-language course. The walkthrough focuses on six study and school-context fields.”** | “이 데모는 UCI Student Performance의 포르투갈어 과목에서 공개된 실제 관측 기록 649건을 사용합니다. 데모에서는 학습 및 학교 맥락 변수 6개에 집중합니다.” |
| 00:48–01:03 | Import review. Hold on `Preview sample: 30 rows · 6 variables`, the header evidence, and the full-load explanation; confirm and show the populated table. | **“Modori clearly labels the first 30 rows as a preview sample. Confirmation loads the complete 649-row table, while the workspace keeps the source data visible for review.”** | “Modori는 처음 30행이 미리보기 표본임을 명확히 표시합니다. 가져오기를 확인하면 649행 전체가 로드되고, 작업 공간에서 원본 데이터를 검토할 수 있습니다.” |
| 01:03–01:20 | Set `Weekly study time` to ordinal with four value labels and `Final grade` to scale. Open Research OS and hold on both Variable Meaning Gate cards. | **“Before proposing a method, Modori asks what each variable means. Study time is ordinal with four labeled bands; final grade is scale. The gate exposes these meanings and missing-code assumptions for confirmation.”** | “방법 후보를 제안하기 전에 Modori는 각 변수가 무엇을 뜻하는지 확인합니다. 학습시간은 네 개의 값 라벨을 가진 순서형 변수이고 최종 성적은 척도형입니다. 이 게이트는 변수 의미와 결측 코드 가정을 확인할 수 있게 보여줍니다.” |
| 01:20–01:38 | Choose the noncausal boundary and `Rank-based co-movement`. Assign `Final grade` as outcome and `Weekly study time` as focal predictor. | **“I frame a noncausal question: do weekly study-time bands and final grades tend to move together? Then I assign final grade as the outcome and study time as the focal predictor.”** | “비인과적 질문을 설정합니다. 주간 학습시간 구간과 최종 성적이 함께 움직이는 경향이 있는가? 이후 최종 성적을 결과 역할로, 학습시간을 핵심 예측 역할로 지정합니다.” |
| 01:38–01:54 | Confirm the Variable Meaning Gate. Show the three bounded questions about clustering, independence, and weight use, using concise jump cuts between answers. | **“Three bounded questions capture clustering, independence, and weight use. Their answers become part of the durable decision record instead of disappearing behind a single button click.”** | “군집 여부, 독립성, 가중치 사용을 세 개의 제한된 질문으로 확인합니다. 답변은 한 번의 클릭 뒤에 사라지지 않고 지속 가능한 의사결정 기록의 일부가 됩니다.” |
| 01:54–02:12 | Hold on the rank-based candidate, association-only claim boundary, experimental badge, then open `Review configuration` to expose the exact Spearman settings. | **“With ordinal study time and these design answers, Modori produces a reviewable Spearman candidate. It shows the association boundary, experimental status, exact variables, and pairwise missingness policy.”** | “순서형 학습시간과 연구설계 답변을 바탕으로 Modori는 검토 가능한 스피어만 후보를 만듭니다. 연관성 해석 범위, 실험적 상태, 정확한 변수, 쌍별 결측 처리 방식을 보여줍니다.” |
| 02:12–02:29 | Review the exact configuration and click `Confirm this configuration`. Hold while the result area is still empty and the separate `Run` action becomes available. | **“I prepare the candidate by reviewing its exact configuration. Confirmation seals the decision and leaves the result empty; the separate Run button makes the transition from planning to calculation explicit.”** | “정확한 구성을 검토하여 후보를 준비합니다. 확인은 결정을 봉인하지만 결과는 비워 두며, 별도의 Run 버튼이 계획에서 계산으로 넘어가는 전환을 명확히 합니다.” |
| 02:29–02:44 | Click the separately enabled `Run`; open the wide result table and keep all four reported quantities legible. | **“Now I choose Run. Modori calculates rho point two seven five, a two-sided p-value below point zero zero one, 649 complete pairs, and zero excluded rows.”** | “이제 Run을 선택합니다. Modori는 로 0.275, 양측 p값 0.001 미만, 완전한 쌍 649개, 제외된 행 0개를 계산합니다.” |
| 02:44–02:55 | Open Report, choose English, click `Save to Word`, show the saved confirmation, and finish on the report title and result table. | **“Finally, Modori saves an English Word report with the method, evidence, and interpretation boundary—ready to review, share, and reproduce.”** | “마지막으로 Modori는 방법, 근거, 해석 범위를 담은 영문 Word 보고서를 저장합니다. 검토하고 공유하며 재현할 수 있는 결과물입니다.” |

## Operator click sheet

Use this order; do not improvise a different task or method during capture.

1. `English` → `GUIDED MODE` → `Open data file`.
2. Select `student-study-and-grades.csv`; resume capture at import review.
3. Confirm import and verify that the table reports 649 rows.
4. Set `weekly_study_time_band`:
   label `Weekly study time`, measure `Ordinal`, labels `1 = Under 2 hours`,
   `2 = 2 to 5 hours`, `3 = 5 to 10 hours`, `4 = Over 10 hours`.
5. Set `final_grade`: label `Final grade`, measure `Scale`.
6. Open Research OS → noncausal → `Rank-based co-movement`.
7. Outcome: `final_grade`; focal predictor: `weekly_study_time_band`.
8. Confirm the Variable Meaning Gate.
9. Answer independence as independent; indicate that neither weights nor clustering
   variables are being used.
10. Open `Review configuration` → verify `method: spearman`, the exact pair,
    `missing_policy: pairwise`, and `p_adjust: none` → `Confirm this configuration`.
11. Show that no result exists yet; click the separately enabled `Run`.
12. Open the wide result table → Report → English → `Save to Word`.

## Recording acceptance gate

- [ ] Runtime is `02:55` or shorter and the subtitle endpoint matches the edit.
- [ ] Opening and later result shots show the same `rho`, p-value display, `n`, and
      excluded-row count.
- [ ] The import review visibly distinguishes the 30-row preview from the 649-row
      loaded table.
- [ ] Variable Meaning Gate, bounded clarification, candidate, exact configuration
      review, confirmation, separate Run, result, and Word export are all visible.
- [ ] `GUIDED MODE`, the experimental badge, and the association interpretation
      boundary are legible.
- [ ] No narration or overlay claims causation, population representativeness,
      universal recommendation validity, expert equivalence, or SPSS superiority.
- [ ] No private path, account name, notification, session transcript, API key, or
      unrelated application appears.
- [ ] The YouTube upload is Public and opens successfully in a signed-out browser.
