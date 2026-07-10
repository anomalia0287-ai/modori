# 모도리 추천 벤치마크 라벨링 지침

Version: `recommendation-annotation-v1`

Status: 20-case economics pilot annotation guide; not accuracy evidence

## 1. 목적과 금지사항

이 지침은 같은 사례를 두 통계 전문가가 독립적으로 판정할 때 동일한 코드와
판정 단위를 사용하게 한다. 라벨링 단위는 `case_id + evidence_stage`다.

- 데이터에 보이는 사실과 스터디 카드에 주어진 사실만 사용한다.
- 자료만으로 알 수 없는 연구 의도나 설계 사실을 추측하지 않는다.
- R, jamovi, JASP는 계산값 검산 도구이지 추천 금라벨 결정자가 아니다.
- `baseline-a-predictions.jsonl`은 리뷰어에게 제공하지 않는다.
- 리뷰어에게 현재 모도리 추천 화면, 다른 리뷰어 답안, AI 답안을 제공하지 않는다.
- Codex, Claude 또는 다른 모델의 답을 금라벨로 복사하지 않는다.
- 수식, 시트 추가/삭제, 열 이름 변경을 하지 않는다.

## 2. 1차 행동 클래스

각 사례 단계에는 아래 셋 중 정확히 하나만 기록한다.

| 코드 | 선택 기준 |
| --- | --- |
| `recommendation_eligible` | 현재 주어진 사실만으로 안전한 분석 후보를 하나 이상 제시할 수 있다. |
| `clarification_required` | 특정 연구 사실의 답이 안전한 후보 또는 설계 모드를 바꾼다. |
| `abstention_required` | 질문을 추가해도 현재 제품 범위에서 안전한 분석을 제시할 수 없거나 증거가 충돌한다. |

기술적으로 실행 가능하다는 이유만으로 `recommendation_eligible`을 선택하지 않는다.
연구 질문, 관측 단위, 독립/대응 구조, 변수 역할이 맞아야 한다.

## 3. 추천 정체성

추천 하나는 `family + roles + design_mode`가 모두 같을 때만 같은 정답이다.
family만 맞고 결과·집단·예측 변수 또는 독립/대응 모드가 다르면 오답이다.

### 현재 V1 실행 가능 family

- `descriptives_table1`
- `reliability`
- `compare_groups`
- `paired_comparison`
- `regression_ols`
- `frequency_crosstab`
- `correlation`
- `anova_oneway`
- `kruskal_wallis`
- `ancova`
- `factor_pca`
- `repeated_measures_anova`
- `friedman`
- `mediation`
- `moderated_mediation`

`logistic_regression`과 `anova_factorial`은 WS3 예약 코드다. 구현과 reference
validation이 완료되기 전에는 이번 파일럿에서 허용 추천으로 기록하지 않는다.
그 분석만이 타당하면 현재 단계에서는 `abstention_required / unsupported_design`으로
기록한다.

### role 열

워크북 `Recommendations` 시트에서 해당하는 열만 채운다.

| role | 의미 | 여러 값 입력 |
| --- | --- | --- |
| `outcome` | 결과 변수 | 보통 1개 |
| `group` | 집단 변수 | 보통 1개 |
| `predictors` | 예측 변수 | 세미콜론으로 구분 |
| `items` | 하나의 척도를 이루는 문항 | 세미콜론으로 구분 |
| `variables` | 기술·상관·요인 분석 대상 | 세미콜론으로 구분 |
| `covariates` | 조정 공변량 | 세미콜론으로 구분 |
| `measures` | 순서 있는 반복 측정 변수 | 시간 순서대로 세미콜론 구분 |

변수 이름은 CSV 헤더와 정확히 같아야 한다. 표시명으로 번역하거나 띄어쓰기를
바꾸지 않는다.

### design_mode 통제 어휘

| family | 허용 design_mode |
| --- | --- |
| `descriptives_table1` | `table1` |
| `reliability` | `scale_items` |
| `compare_groups` | `independent` |
| `paired_comparison` | `paired` |
| `regression_ols` | `main_effects` |
| `frequency_crosstab` | `frequency`, `crosstab` |
| `correlation` | `bivariate` |
| `anova_oneway` | `independent_oneway` |
| `kruskal_wallis` | `independent_rank` |
| `ancova` | `main_effects` |
| `factor_pca` | `exploratory` |
| `repeated_measures_anova` | `repeated_wide` |
| `friedman` | `repeated_rank_wide` |
| `mediation` | `simple` |
| `moderated_mediation` | `conditional_process` |

허용 추천이 여러 개면 각각 한 행으로 쓰고 `rank`를 1부터 연속으로 부여한다.
진짜 동률은 family 코드 알파벳 순으로 행을 배치하고 `notes`에 `true_tie`를 쓴다.
채점기의 허용 추천 집합은 순서를 점수로 사용하지 않는다.

## 4. clarification fact ID

`clarification_required`일 때 실제로 안전한 결정을 바꿀 수 있는 fact ID만 쓴다.

- `unit_of_observation`: 한 행이 무엇을 나타내는지
- `research_goal`: 요약, 비교, 관계, 예측 중 주된 질문
- `outcome_role`: 결과로 해석할 변수
- `group_role`: 집단을 나타내는 변수
- `covariate_role`: 조정해야 할 공변량
- `paired_status`: 두 값/집단이 같은 대상에 대응하는지
- `repeated_measure_order`: 반복 측정의 순서
- `time_order`: 변수 측정의 시간적 선후
- `causal_intent`: 인과 표현이 연구 목적에 포함되는지
- `missing_code_meaning`: 범위 밖 코드가 실제 값인지 결측인지
- `scale_membership`: 문항이 같은 척도에 속하는지
- `reverse_coding`: 역채점 문항과 범위
- `weight_usage`: 가중치를 분석에 반영해야 하는지
- `cluster_usage`: 군집 설계를 분석에 반영해야 하는지

목록 밖 fact ID가 반드시 필요하면 임의로 만들지 말고 `notes`에 한국어로 적고
판정자에게 새 코드 등록을 요청한다.

## 5. abstention reason code

- `unsupported_design`: 현재 제품에 필요한 분석 또는 설계 보정이 없다.
- `insufficient_context`: 필요한 연구 정보가 없고 안전한 기본값도 없다.
- `conflicting_evidence`: 스터디 카드와 데이터 증거가 충돌한다.
- `out_of_scope`: 연구 질문이 통계 분석 추천 범위를 벗어난다.
- `unsafe_data_state`: 데이터 상태 때문에 분석 후보를 제시하면 위험하다.

## 6. 오류 심각도

각 사례에서 잘못된 1차 행동이 초래할 가장 높은 심각도를 기록한다.

- `E1`: 안전하지만 불필요한 질문 또는 기권
- `E2`: 비선호지만 허용 가능한 후보를 낮은 수준으로 표시
- `E3`: 변수 역할, 독립/대응, 반복 구조 또는 기억 적용 오류
- `E4`: 위험한 분석을 강한 추천으로 표시하거나 지원 밖 분석을 자동 승격
- `E5`: 데이터 변경, 원문 유출, 다른 프로젝트 기억 재사용 같은 경계 실패

평균 정확도가 `E4` 또는 `E5`를 상쇄할 수 없다.

## 7. 독립 라벨링 절차

1. `Instructions`와 이 지침을 읽는다.
2. `Study Cards` 한 행과 연결된 CSV를 확인한다.
3. 다른 리뷰어와 상의하지 않고 `Case Reviews`를 작성한다.
4. 해당 보조 시트에 추천, 질문 또는 기권 근거를 기록한다.
5. 실제 작업 시간만 `active_minutes`에 기록하고 휴식 시간은 뺀다.
6. 20건 완료 전 다른 리뷰어 답안이나 baseline을 보지 않는다.

## 8. 판정과 합의 게이트

판정자는 두 독립 제출을 모두 받은 뒤 불일치를 기록하고 최종 라벨을 만든다.
불일치를 삭제하지 말고 `Adjudication` 시트에 근거를 남긴다.

- 1차 행동 nominal Krippendorff alpha: 최소 `0.80`
- 허용 추천 집합 mean Jaccard: 최소 `0.80`
- 허용 추천 집합 exact-set agreement: 최소 `0.70`
- 질문 fact 집합 mean Jaccard: 최소 `0.80`
- 질문 fact 집합 exact-set agreement: 최소 `0.70`

문턱을 통과하지 못하면 비용만 기록하고 지침을 보정한 뒤 독립 재라벨링한다.
20건 결과는 정확도 주장이나 제품 출시 근거가 아니다.
