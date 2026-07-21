# Modori 라이브 Research OS 사무용 PC 측정 절차

Status: **B4-R 개발 PC 복구 검증 완료. B5 HP 노트북 실측 대기.**

2026-07-18의 `0cae87d` 후보는 개발 PC 검증은 통과했지만 대상 HP 노트북의
legacy Win32 동적 경로 한계에서 실행 전 실패했으므로 폐기했다. 다음 두 파일은
회귀 분석에만 남기는 **폐기된 식별자**이며 다시 전달하거나 실행하지 않는다.

- `modori-live-research-os-office-kit-0cae87dfeb11-py31210.zip`
- SHA-256 `4aefcc613d3456c6ab0f81f730c34cdde00e40ed6f9636b0333292ce0e823de9`

HP 노트북에 전달할 현재 후보는 다음 두 파일뿐이다.

- source/build commit:
  `989d5c5829e3d3de69ebda0f4fc88e6f76d16112`
- ZIP:
  `modori-live-research-os-office-kit-989d5c5829e3-py31210.zip`
- sidecar:
  `modori-live-research-os-office-kit-989d5c5829e3-py31210.zip.sha256`
- ZIP 크기: `138,390,004` bytes
- SHA-256:
  `6f567b327ad53c68eff5f27623e494c1273f9a424e11896e99c5d9f5a0bb8d43`

키트는 위 source/build commit의 소스를 봉인한다. 이 증거를 기록하는 뒤의 문서
커밋과 ZIP 내부 source commit이 다른 것은 의도된 결과다. 문서 수정 때문에 이미
검증한 바이너리를 다시 만들지 않는다.

## 1. B4-R에서 확인된 사실

### 1.1 아카이브와 재현성

- 서로 다른 세 출력 폴더에서 독립 빌드한 ZIP 세 개와 sidecar 세 개가 바이트
  단위로 동일했다.
- 각 ZIP은 정렬된 항목 `1,612`개를 가지며 중복 항목은 0개, `work` 항목은 0개다.
- 모든 항목의 CRC 읽기가 성공했다. manifest가 봉인한 immutable 항목은
  `1,413`개이며 embedded runtime identity 검증도 통과했다.
- 처음 발견한 두 비결정성 원인은 Python hash 순서와 PE build timestamp였다.
  각각 `PYTHONHASHSEED=0`과 source commit 시각 기반 `SOURCE_DATE_EPOCH`으로
  고정한 뒤에만 위 3회 동일성을 얻었다.
- runtime·payload·identity·manifest·PowerShell bootstrap을 포함한 300개 봉인
  변조는 모두 runtime 시작과 유효 결과 게시 전에 거부되었다. 관련
  builder/verifier/architecture 묶음은 `34 passed`였다.

### 1.2 개발 PC의 전체 로컬 실행

- 실제 CMD 진입점으로 20회 cold/30회 warm 전체 프로토콜을 실행했고 종료 코드는
  0이었다.
- 반환 run ID는 `c44906b4-5814-4c34-a7cd-0de2087944ee`, result hash는
  `64504c753554bf2741c83d651055fd0cb563eaff5b028975f987a71e7be07d19`다.
- 독립 재검증 결과는 `valid_pass`, 분리된 gate `98/98` 통과, 실패 행 0,
  reason code 0이었다. origin authentication은 설계대로 `false`다.
- initial identity p95는 cold `2,569.428 ms`, warm `2,087.265 ms`였다.
  결정 단계에서 가장 느린 분리 그룹 p95는 cold initial `296.396 ms`, warm
  initial `394.023 ms`, cold later `656.206 ms`, warm later `583.975 ms`였다.
  acknowledgement 그룹의 최대 p95는 `0.178 ms`였다.
- peak working set p95는 `250.316 MiB`, max는 `250.680 MiB`였다. 125,000행 ×
  40열 합성 stress fixture는 `4.468 s`에 완료되었다.
- 이 개발 PC는 Windows 11, 12 physical/16 logical cores, 약 16.8GB RAM,
  내부 NTFS 저장장치다. 이 수치는 저가형 HP 노트북의 성능 결과를 대신하지 않는다.

### 1.3 전체 품질 gate와 남은 불안정성

- 공식 전체 gate는 `693.3 s`에 종료 코드 0이었다: compileall, Ruff, Bandit
  `src`, launch smoke, pip check, package check/build/launch/engine/public-data smoke가
  통과했고 pytest는 `3233 passed, 13 skipped`였다. 별도 slow-stats gate도
  `4 passed, 3242 deselected`로 통과했다.
- 13개 skip은 추천 적격성이 필요 없는 paired 비교 1개, 명시적 slow-stats
  실행이 필요한 bootstrap/factorial 4개, 설치되지 않은 Rscript 기반 교차 엔진
  참조 8개다. skip을 성공으로 바꾸어 세지 않는다.
- PyInstaller는 `Hidden import "scipy.special._cdflib" not found!`를 경고했다.
  설치된 SciPy 1.18.0 자체에 그 모듈이 없고 package engine smoke는 통과했지만,
  이것이 모든 SciPy 경로를 증명한다고 주장하지 않는다.
- skip 사유를 수집하려고 불필요하게 한 차례 더 실행한 전체 pytest에서 별도 UI
  갤러리 p95가 `256.569 ms`로 고정 한계 `250 ms`를 `6.569 ms` 초과해 1건
  실패했다. 즉시 단독 재실행은 `241.296 ms`로 통과했다. 기준은 낮추지 않았고,
  이를 안정 통과로 포장하지 않는다. 이 현상은 B4-R ledger/import 실행 경로와
  분리된 release-test timing 불안정성으로 남긴다. 또한 해당 실화면 갤러리 검사는
  Windows 창을 항목별로 표시하므로 사용자 PC에서 반복 실행하지 않는다.

개발 PC의 B4-R 통과는 **HP 후보를 다시 측정할 자격**을 확정한 것이지 B5를
완료한 것이 아니다. HP 결과가 `valid_stop`이면 사전 고정 기준을 낮추지 않는다.

## 2. 이 측정이 답하는 질문

이 키트는 공개·합성 데이터만 사용해 라이브 Research OS가 실제로 다음 작업을
수행하는 대기시간을 잰다.

1. 고정 데이터 지문 계산
2. 프로젝트별 Decision Ledger 생성·열기와 append/audit
3. 여섯 P1 연구과업의 질문·답변·재계획·패스포트·handoff·preflight
4. 공개 UI 동작의 busy/static 신호 응답

이 결과는 실행 가능성과 대기시간 증거다. 추천 타당성, 계산 정확도, 인간 전문가
동등성, SPSS 우월성, 실제 사용자 데이터 안전성을 한 번에 입증하지 않는다.

## 3. 노트북에 미치는 영향

- 설치하거나 관리자 권한을 요구하지 않는다.
- 인터넷, 레지스트리, Windows 서비스, 전원 설정을 사용하거나 변경하지 않는다.
- 사용자의 문서·연구자료·최근 파일을 열지 않는다.
- 압축을 푼 키트 안에서는 results 폴더만 쓴다.
- 합성 작업공간은 키트 안이 아니라 정확히 `<MBL 폴더>\w`에 자동 생성한다.
  각 실행이 남긴 소유 표식을 확인한 자기 하위 항목만 정리한다.
- Windows·백신의 일반 실행 기록까지 남지 않는다고 보증하지는 않는다.
- 이 작업과 무관한 폴더, OEM 도구, 복구 영역 또는 다른 파티션을 삭제하거나
  수정하지 않는다.

## 4. 전달받을 파일은 정확히 두 개다

- `modori-live-research-os-office-kit-989d5c5829e3-py31210.zip`
- `modori-live-research-os-office-kit-989d5c5829e3-py31210.zip.sha256`

비슷한 이름의 이전 키트는 사용하지 않는다. `.zip.sha256` 내용과 위에 고정된
64자리 SHA-256이 일치하지 않으면 실행하지 말고 그 두 파일을 다시 받는다.

## 5. 대상 노트북 준비

1. AC 전원을 연결하고 측정이 끝날 때까지 유지한다.
2. Windows Update나 대용량 복사처럼 명백히 무거운 작업은 끝날 때까지 기다린다.
3. 사용자가 직접 연 무거운 프로그램만 닫는다. 백신이나 사무환경을 인위적으로
   제거하지 않는다.
4. 내부 디스크에 ZIP, 약 350MB 런타임, 측정 작업공간을 담을 여유가 있는지
   확인한다.

노트북을 포맷하거나 기존 자료를 지울 필요가 없다.

## 6. 올바른 로컬 경로

위 source commit 앞 12자리를 사용해 다음 폴더를 만든다.

`%LOCALAPPDATA%\MBL-989d5c5829e3`

Windows 실행 창은 존재하지 않는 폴더를 새로 만들지 않는다. 위 경로가 바로 열리지
않으면 실행 창에 `%LOCALAPPDATA%`까지만 입력해 연 뒤, 그 안에
`MBL-989d5c5829e3` 폴더를 직접 만드는 방식이 정상이다.

1. USB의 ZIP과 `.zip.sha256`을 위 폴더로 복사한다.
2. USB에서 직접 실행하지 않는다. USB 속도를 제품 속도로 오인하게 된다.
3. OneDrive, Google Drive, 다른 동기화 폴더, 네트워크 드라이브에서는 실행하지
   않는다. 바탕 화면·문서 폴더도 동기화 대상일 수 있으므로 쓰지 않는다.
4. junction, 심볼릭 링크, 바로가기 또는 `reparse point` 경로를 쓰지 않는다.
5. ZIP을 오른쪽 클릭해 **모두 압축 풀기**를 선택한다. ZIP 안에 같은 이름의
   최상위 폴더가 이미 들어 있다. 따라서 **압축 풀기 창의 대상 폴더**는 반드시
   `%LOCALAPPDATA%\MBL-989d5c5829e3`에서 끝나야 한다. `찾아보기`로
   방금 만든 `MBL-...` 폴더 자체를 선택하는 것이 가장 확실하다.
6. Windows가 ZIP 파일명까지 자동으로 붙인 기본값—즉 대상 끝에
   `modori-live-research-os-office-kit-...`가 이미 붙은 경로—을 그대로 사용하지
   않는다. 그러면 ZIP 내부의 같은 폴더가 한 번 더 중첩되어
   `0x80010135: 경로가 너무 깁니다` 오류가 날 수 있다.
7. 이 오류가 났다면 작업을 취소한다. ZIP과 `.zip.sha256`은 그대로 두고, 실패한
   압축 해제로 생긴 `modori-live-research-os-office-kit-...` **폴더만** 삭제한 뒤
   5번의 짧은 대상 폴더로 다시 압축 해제한다. ZIP 파일이나 다른 폴더는 삭제하지
   않는다.
8. 다른 위치에서 풀어 둔 폴더를 이동하거나 이전 실행 폴더 위에 덮어쓰지 않는다.
9. 압축 해제 후 전체 경로가 너무 길면 `kit_path_too_long`으로 중단된다. 폴더
   이름을 임의로 길게 바꾸지 않는다. `MBL-`은 230자 gate와 현재 runtime의
   최장 상대 경로를 함께 만족시키기 위해 의도적으로 짧게 정한 이름이다.
10. 실행기는 합성 작업을 시작하기 전에 `<MBL 폴더>\w` 아래에서 생길 모든 동적
    경로를 **240 UTF-16 코드 단위** 기준으로 계산한다. 하나라도 넘으면 자식
    프로세스나 원장을 만들지 않고 `dynamic_path_budget_exceeded`로 중단한다.

## 7. 실행

압축을 푼 최상위 폴더의
`RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd`를 두 번 클릭한다.

키트는 다음 순서로 진행한다.

1. CMD가 검증된 PowerShell bootstrap을 잠근다.
2. PowerShell이 manifest·identity·모든 immutable 파일을 검증하고 읽기 핸들을
   유지한다.
3. frozen runtime이 자체 identity와 외부 kit identity를 대조한다.
4. 짧은 형제 작업공간과 전체 동적 경로 예산을 검증한다.
5. 고정된 release 프로토콜만 실행한다.
6. 모든 raw observation을 봉인한 뒤에만 JSON·sidecar·한국어 요약을 게시한다.

이 검사는 20회 cold 프로세스/프로필과 30회 warm 전체 반복을 수행한다. 구형
사무용 PC에서는 수 시간이 걸릴 수 있다. 개별 추천 대기 기준 30초와 전체 검사
시간은 다른 값이다. 진행 문구가 바뀌고 있다면 창을 강제로 닫지 않는다.

## 8. 가져올 파일

정상 완료 시 `results` 폴더에서 다음 세 파일만 가져온다.

- `modori-live-research-os-office-benchmark-<run-id>.json`
- 같은 JSON 전체 이름 뒤의 `.json.sha256`
- 같은 stem 뒤의 `.summary-ko.txt`

사전검증 또는 실행 오류가 났다면 results 폴더에서 한 실행에서 새 오류 문서 하나만
가져온다.

- `bootstrap-error-<UTC>.txt`
- 오류 코드가 보이는 화면 사진(선택)

`<MBL 폴더>\w`, 프로젝트 원장, 노트북의 다른 파일은 열거나 가져오지 않는다.

## 9. 오류와 판정의 구분

- `invalid_run`: 해시·파일 집합·프로토콜·AC·경로·runtime identity·raw observation
  완전성 중 하나가 유효하지 않다. `dynamic_path_budget_exceeded`도 작업을 시작하기
  전의 경로 환경 거부이므로 여기에 속한다. 제품 성능 실패로 세지 않으며,
  합리적인 설정 오류를 고친 뒤 새 폴더에서 다시 실행할 수 있다.
- `valid_stop`: 실행 자체는 유효하지만 사전 고정된 30초/100ms 행 또는 닫힌 제품
  오류 기준을 통과하지 못했다. 기준을 낮추지 않는다.
- `valid_pass`: 모든 실행 조건과 모든 분리 행을 통과했다. 그래도 추천 타당성이나
  통계 정확도를 증명한 것은 아니다.

`bootstrap-error`가 있거나 결과 세 파일이 불완전하면 `valid_stop`으로 추정하지
않고 먼저 `invalid_run` 여부를 확인한다.

## 10. 무결성 주장의 한계

SHA-256 sidecar, manifest, `result_hash`, 독립 p95 재계산은 봉인 뒤의 우발적 변경과
부분적 위조를 검출한다. 그러나 이 무료·오프라인 키트에는 신뢰된 비밀 서명키나
TPM 원격 증명이 없다. 따라서 **origin authentication**—악의적인 로컬 행위자가
JSON·평가·요약·sidecar를 모두 일관되게 새로 만든 경우 그 출처를 증명하는 것—은
제공하지 않는다. 반환 파일은 사용자가 직접 실행한 원본이라는 운영상 연속성과
함께 해석한다.
