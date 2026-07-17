# Modori 휴대용 사무용-PC 벤치마크 실행 절차

Status: kit design and implementation complete only after the final ZIP digest is
reported in chat; target-laptop measurement pending

## 1. 무엇을 측정하는가

이 키트는 Modori Decision Ledger의 다음 작업만 합성 데이터로 측정한다.

1. 10,000개 사건 원장을 열고 재생하는 시간
2. SQLite FULL 동기 쓰기 1,000회의 지연시간
3. 16 MiB·10,000개 사건 evidence bundle 검증시간
4. 프로세스 최대 메모리

UI, 통계 계산 정확도, 추천 타당성, 실제 연구 데이터는 시험하지 않는다.
결과의 `office_hardware_claim_allowed`는 언제나 `false`이며, 반환 후 별도
검토를 거쳐야 한다.

## 2. 노트북에 미치는 영향

- 프로그램을 설치하지 않는다.
- 관리자 권한을 요구하지 않는다.
- 인터넷을 사용하지 않는다.
- 레지스트리, Windows 서비스, 전원 설정을 변경하지 않는다.
- 사용자 문서·사진·연구자료·네트워크 정보를 열거나 열거하지 않는다.
- 키트를 푼 폴더 아래의 `work`와 `results`만 사용한다.
- Windows 자체의 실행 기록, 캐시, 백신 기록까지 남지 않는다고 보장하지는
  않는다.

## 3. USB에 담기 전

현재 PC에서 전달받은 파일은 두 개다.

- `modori-office-benchmark-kit-<commit>-py31210.zip`
- 같은 이름의 `.zip.sha256`

채팅에 보고된 64자리 SHA-256과 `.zip.sha256` 첫 값이 같은지 확인한다. ZIP과
해시 파일을 50GB USB에 복사한다. 프로젝트 폴더, `.git`, `.venv`, 실제 데이터는
복사하지 않는다.

## 4. 대상 노트북 준비

1. Windows 노트북을 AC 전원에 연결한다.
2. Windows Update나 대용량 복사처럼 명백히 무거운 작업이 진행 중이면 끝날
   때까지 기다린다.
3. 사용자가 직접 열어 둔 무거운 프로그램을 닫는다. 백신이나 일반 사무환경을
   인위적으로 제거하지 않는다.
4. 내부 디스크에 최소 2 GiB가 남아 있는지 확인한다.

노트북이 비어 있을 필요는 없으며 포맷하거나 기존 파일을 삭제하지 않는다.

## 5. ZIP 이동과 해시 확인

1. USB의 ZIP을 측정할 노트북 내부 디스크로 복사한다.
2. USB에서 직접 실행하지 않는다. 그렇게 하면 USB 성능을 재게 된다.
3. OneDrive나 다른 클라우드 동기화 폴더에서 실행하지 않는다. 바탕 화면과
   문서 폴더도 OneDrive에 연결되어 있을 수 있다. 키트는 재분석 지점
   (`reparse point`), 바로가기, 심볼릭 링크, junction을 거부한다.
4. 확실한 일반 사용자 로컬 경로가 필요하면 `Win+R`을 누르고
   `%LOCALAPPDATA%`를 연 뒤 그 아래에 `ModoriBench`를 만든다. USB의 원본 ZIP을
   완성된 `%LOCALAPPDATA%\ModoriBench` 폴더에 복사하고 그 자리에서 새로 압축
   해제한다. OneDrive에서 이미 푼 폴더를 단순 이동하지 않는다.
5. 원하는 경우 명령 프롬프트에서 다음을 실행해 ZIP 해시를 다시 확인한다.

```bat
certutil -hashfile "modori-office-benchmark-kit-<commit>-py31210.zip" SHA256
```

6. 출력된 64자리 값이 채팅에 보고된 값과 정확히 같은지 확인한다.
7. ZIP을 같은 내부 디스크의 새 폴더에 압축 해제한다.

## 6. 실행

압축을 푼 최상위 폴더에서 `RUN-MODORI-BENCHMARK.cmd`를 두 번 클릭한다.

정상 흐름은 다음 다섯 문구를 차례로 표시한다.

1. 키트 무결성 확인
2. 노트북 하드웨어와 AC 전원 확인
3. 합성 벤치마크 세 번 실행
4. 결과 장부와 SHA-256 검증
5. 완료 및 JSON 파일명

구형 HDD에서는 수 분 이상 걸릴 수 있다. 멈춘 것처럼 보여도 창을 강제로
닫지 않는다. 완료되면 아무 키나 눌러 창을 닫는다.

## 7. 오류가 발생한 경우

다음 정보를 가져온다.

1. 오류 코드가 보이도록 찍은 화면 사진
2. `results` 아래 생성된 `bootstrap-error-*.txt`
3. 생성되었다면 JSON, `.json.sha256`, `.summary-ko.txt`
4. 어느 단계에서 멈췄는지에 대한 짧은 메모

Python traceback, 사용자 경로, 문서 목록을 수집할 필요가 없다. 오류가 난다고
노트북 설정을 임의로 바꾸거나 관리자 실행을 시도하지 않는다.

## 8. 정상 완료 후 회수

`results` 폴더에서 다음 파일만 USB에 복사한다.

- `modori-office-benchmark-<measurement-id>.json`
- 동일 이름의 `.json.sha256`
- 동일 이름의 `.summary-ko.txt`
- 존재하는 `bootstrap-error-*.txt`

이 파일과 오류 사진만 현재 PC로 가져온다. `work` 폴더나 노트북의 다른 파일은
가져오지 않는다. 반환된 JSON 해시를 독립적으로 확인한 뒤 CPU·RAM·저장장치
프로필, 세 번의 변동, 최악값, 잠정 게이트를 판정한다.
