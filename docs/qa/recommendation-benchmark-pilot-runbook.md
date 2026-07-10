# 모도리 추천 벤치마크 20건 파일럿 실행 절차

Status: tooling ready; human reviews not yet performed

## 1. 이번 단계의 목적

이번 20건은 추천 정확도를 증명하는 시험이 아니다. 다음 세 가지를 측정한다.

1. 통계 전문가가 사례 하나를 판정하는 실제 시간
2. 두 전문가가 같은 지침으로 합의 가능한 정도
3. 150/200/800건으로 확대할 때 필요한 인력 시간과 비용

현재 A baseline의 실측 결과는 20건 모두 `descriptives_table1`을 강한 기본
추천으로 선택했다. 이것은 현재 정렬 정책의 관측값이며 정확도 점수가 아니다.
금라벨이 없으므로 맞고 틀림을 아직 계산할 수 없다.

## 2. 반드시 필요한 사람

- 통계 자격을 갖춘 독립 검토자 2인: 각각 20건을 독립 판정
- 판정자 1인: 두 답안의 불일치를 검토하고 최종 기록
- 벤치마크 소유자: 파일 배포, 비용 입력, split/결과 보관
- 데이터 스튜어드: 라이선스, checksum, 민감도 확인

사용자는 비전공자이므로 금라벨 검토자 역할을 맡지 않는다. 사용자는 소유자와
데이터 스튜어드 역할은 수행할 수 있다. Codex, Claude 또는 다른 AI는 통계 자격을
갖춘 사람 2인을 대체할 수 없고 판정자의 최종 권한도 가질 수 없다.

검토자 확보가 불가능하면 이 단계에서 멈춘다. 결정론적 개발은 계속할 수 있지만
공개 80% 주장, C2 채택, 새로운 strong 승격은 진행하지 않는다.

## 3. 원본 파일 위치

저장소 안의 원본 템플릿을 직접 수정하지 않는다.

```text
tests\fixtures\recommendation_benchmark\public\pilot\reviewer-a.xlsx
tests\fixtures\recommendation_benchmark\public\pilot\reviewer-b.xlsx
tests\fixtures\recommendation_benchmark\public\pilot\adjudication.xlsx
tests\fixtures\recommendation_benchmark\public\pilot\data\
```

리뷰어에게 아래 파일은 제공하지 않는다.

```text
baseline-a-predictions.jsonl
baseline-a-metadata.json
다른 리뷰어의 workbook
```

## 4. 사용자가 파일을 준비하는 방법

Windows 파일 탐색기로 진행할 수 있다.

1. 바탕 화면에 `Modori-Recommendation-Pilot` 폴더를 만든다.
2. 그 안에 `Reviewer-A`, `Reviewer-B`, `Adjudication` 폴더를 만든다.
3. 원본 `data` 폴더를 세 폴더 각각에 복사한다.
4. `reviewer-a.xlsx`를 `Reviewer-A`에 복사한다.
5. `reviewer-b.xlsx`를 `Reviewer-B`에 복사한다.
6. `adjudication.xlsx`를 `Adjudication`에 복사한다.
7. 이 annotation guide를 세 사람 모두에게 별도로 제공한다.
8. Reviewer A와 Reviewer B에게 서로의 신원이나 답안 파일을 전달하지 않는다.

각 폴더 안에서 workbook의 `data_file` 값은 `data\...csv`와 연결된다. CSV는
Excel에서 읽기 전용으로 열고 저장 형식을 바꾸지 않는다.

## 5. 리뷰어가 Excel에서 하는 조작

Reviewer A는 `reviewer-a.xlsx`, Reviewer B는 `reviewer-b.xlsx`만 사용한다.

1. `Instructions` 시트를 연다.
2. `B2`에 익명 reviewer ID를 입력한다. 실명은 필요 없다.
3. `Study Cards` 시트에서 사례의 질문, 관측 단위, 표집, 집단, 시간 구조,
   가중치/군집, 변수 의미, 결측 코드를 읽는다.
4. 같은 행의 `data_file` CSV를 열어 열 이름과 값 범위를 확인한다.
5. `Case Reviews`의 `action_class`, `failure_severity`, `active_minutes`, `notes`를
   입력한다.
6. 행동에 따라 정확히 한 종류의 보조 시트를 작성한다.
7. 20건 모두 완료한 뒤 저장하고 Excel을 닫는다.

보조 시트 입력 규칙:

- `recommendation_eligible`: `Recommendations`에 허용 후보를 1-3행 기록
- `clarification_required`: `Clarifications`에 decision-changing fact ID 기록
- `abstention_required`: `Abstentions`에 reason code 기록

여러 변수는 세미콜론으로 구분한다. workbook에 수식을 입력하거나 시트·열을
추가/삭제하지 않는다. `active_minutes`에는 실제 판정 시간만 숫자로 입력하고 휴식,
전화, 다른 업무 시간은 제외한다.

## 6. 판정자가 하는 조작

두 독립 파일이 모두 반환된 뒤에만 판정을 시작한다.

1. Reviewer A/B 파일과 `adjudication.xlsx` 사본을 준비한다.
2. 사례별 행동, 추천 정체성, 질문 fact, 심각도를 비교한다.
3. 불일치 이유를 `Adjudication` 시트에 기록한다.
4. 최종 행동과 라벨을 `Case Reviews` 및 해당 보조 시트에 기록한다.
5. 사례별 판정 시간을 `Resolution Minutes`에 입력한다. 합의 사례도 `0`을 쓴다.
6. 20건 모두 완료한 뒤 저장한다.

판정자는 조용히 다수결하지 않는다. 두 답안과 방법론 근거를 보존하고 최종 결정
이유를 적는다.

## 7. 사용자가 반환해야 하는 파일

아래 세 파일을 원본과 다른 폴더에서 전달한다.

- 완성된 `reviewer-a.xlsx`
- 완성된 `reviewer-b.xlsx`
- 완성된 `adjudication.xlsx`

가장 쉬운 방법은 세 파일의 위치를 Codex에 알려 주는 것이다. 사용자가 명령어를
직접 실행할 필요는 없다. Codex가 제출 검증, 합의도, 비용 계산을 수행할 수 있다.

## 8. 재현 가능한 명령

개발자가 직접 확인할 때는 저장소 루트의 PowerShell에서 실행한다. 아래의
`C:\Pilot\...` 경로는 실제 완성 파일 경로로 바꾼다.

팩 자체 검증:

```powershell
.\.venv\Scripts\python.exe scripts\recommendation_benchmark.py validate-pack --pack-root tests\fixtures\recommendation_benchmark --output .tmp\recommendation-pack-validation.json
```

제출 파일 구조 검증:

```powershell
.\.venv\Scripts\python.exe scripts\recommendation_benchmark.py validate-submissions --pack-root tests\fixtures\recommendation_benchmark --reviewer-a C:\Pilot\reviewer-a.xlsx --reviewer-b C:\Pilot\reviewer-b.xlsx --adjudication C:\Pilot\adjudication.xlsx --output .tmp\recommendation-submissions.json
```

합의도 계산:

```powershell
.\.venv\Scripts\python.exe scripts\recommendation_benchmark.py agreement --pack-root tests\fixtures\recommendation_benchmark --reviewer-a C:\Pilot\reviewer-a.xlsx --reviewer-b C:\Pilot\reviewer-b.xlsx --output .tmp\recommendation-agreement.json
```

비용 계산 예시. 시급과 고정비는 실제 계약 금액으로 바꾼다.

```powershell
.\.venv\Scripts\python.exe scripts\recommendation_benchmark.py cost --pack-root tests\fixtures\recommendation_benchmark --reviewer-a C:\Pilot\reviewer-a.xlsx --reviewer-b C:\Pilot\reviewer-b.xlsx --adjudication C:\Pilot\adjudication.xlsx --stage-cases 150 --reviewer-rate 100000 --adjudicator-rate 120000 --setup-cost 0 --data-steward-cost 0 --project-management-cost 0 --output .tmp\recommendation-cost-150.json
```

금라벨이 완료된 뒤 점수 계산:

```powershell
.\.venv\Scripts\python.exe scripts\recommendation_benchmark.py score --pack-root tests\fixtures\recommendation_benchmark --adjudication C:\Pilot\adjudication.xlsx --predictions tests\fixtures\recommendation_benchmark\public\pilot\baseline-a-predictions.jsonl --scorer-fingerprint sha256:50c0397b580866878795c4a6a2260c13a855137bb55acbffadd1266485c3ce3a --output .tmp\recommendation-score-a.json
```

출력 파일이 이미 있으면 명령은 실패한다. 의도적으로 교체할 때만 `--force`를
추가한다.

## 9. 결과 판정

- agreement 문턱 미달: 지침을 수정하고 독립 재라벨링한다.
- 비용 과다 또는 전문가 미확보: 150/200/800건 확대를 승인하지 않는다.
- 문턱 통과: 측정된 시간과 실제 시급으로 각 단계 예산을 산정한다.
- 20건 점수: 제품 정확도 주장에 사용하지 않는다.

이 파일럿이 끝나도 150건 development, 200건 frozen deterministic validation,
800건 locked claim corpus는 서로 다른 역할과 게이트를 유지한다.
