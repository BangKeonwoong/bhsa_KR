로컬 실행 안내 (간편)
=====================

필수 조건
--------
- Python 3.x 설치 (윈도우/맥/리눅스)
- 처음 한 번만 인터넷 연결(필요 패키지 및 TF 데이터 캐시용)

가장 쉬운 실행 방법
---------------
- macOS: `start_viewer.command` 더블클릭 (보안 경고 시 우클릭→열기 또는 시스템 설정에서 허용)
- Windows: `start_viewer.bat` 더블클릭 (PowerShell 정책 차단 시 “추가 정보 → 실행”)
- Linux: 터미널에서 `./run.sh`

참고: TF 데이터(ETCBC BHSA) 캐시 및 오프라인 동작
-----------------
- 뷰어는 BHSA(Text‑Fabric) 데이터가 "로컬에 있을 때만" 로드합니다. 네트워크가 막혀 있거나 데이터가 없으면 CTT만으로 작동합니다.
- 오프라인에서 TF 기능을 사용하려면 한 번 온라인으로 실행해 캐시를 채워 두거나, 아래 경로를 프로젝트의 `data/text-fabric-data/`로 복사하세요.
  - macOS/Linux: `~/text-fabric-data/etcbc/bhsa/`
  - Windows: `C:\\Users\\<계정>\\text-fabric-data\\etcbc\\bhsa\\`
- 환경변수로 경로를 직접 지정할 수도 있습니다: `TF_LOCAL_DIR`, `TF_DATA_DIR`, `TF_LOCATIONS`

성능/지연 관련 팁
----------------
- CTT 파싱 중 BHSA 매핑은 로컬 데이터가 있을 때만 시도합니다. 대용량 TF 로드를 피하려면 `CTT_SKIP_TF=1`로 강제 비활성화할 수 있습니다.
- `source=tf`로 요청해도 로컬 BHSA 데이터가 없으면 자동으로 CTT로 폴백합니다.
- 파싱 캐시: 동일 책/장을 반복 요청하면 서버 내부 LRU 캐시가 재사용되어 응답이 빨라집니다. 강제 재계산이 필요하면 서버를 재시작하세요.

대체 방법(모든 OS 공통)
------------------
1) 터미널/PowerShell에서 프로젝트 폴더로 이동
2) 가상환경 생성 및 의존성 설치
   - `python -m venv .venv` (또는 `python3 -m venv .venv`)
   - Windows: `.venv\\Scripts\\activate`
   - macOS/Linux: `source .venv/bin/activate`
   - `pip install -r requirements.txt`
3) 실행
   - `python app.py`
   - 브라우저에서 `http://127.0.0.1:5001/` 접속

빠른 실행/오프라인 설치 팁
---------------------
- pip 설치 단계가 느리거나(네트워크 제한) 건너뛰고 싶다면 `SKIP_PIP=1`로 실행하면 됩니다.
  - macOS: `SKIP_PIP=1 ./start_viewer.command`
  - Linux: `SKIP_PIP=1 ./run.sh`
  - Windows: `setx SKIP_PIP 1` 후 `start_viewer.bat` 실행(또는 일회성 환경변수로 PowerShell에서 `$env:SKIP_PIP='1'`).
- 오프라인 설치를 하려면 `data/wheels/` 폴더에 필요한 휠(.whl)을 넣어두세요. 실행기가 먼저 여기에서 설치를 시도합니다.
- pip 네트워크 타임아웃 기본값은 짧게(10초) 설정되어 있습니다. 필요 시 `PIP_DEFAULT_TIMEOUT`으로 조정 가능합니다.

문제 해결
-------
- macOS에서 .command 실행이 막힐 때:
  - `chmod +x start_viewer.command`
  - `xattr -d com.apple.quarantine start_viewer.command` (필요 시)
- Windows에서 .bat 실행이 막힐 때:
  - PowerShell에서 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- 포트(5001) 충돌:
  - `app.py`의 `app.run(... port=5001 ...)` 값을 다른 포트로 변경
- pip 관련 오류(ImportError, invalid metadata 등) 발생 시:
  - 실행기에 pip 복구 로직이 포함되어 있습니다. 한 번 더 실행해 보세요.
  - 가상환경 초기화: `RESET_VENV=1 ./start_viewer.command` (macOS) 또는 `RESET_VENV=1 ./run.sh` (Linux)
  - 기본적으로 pip 자동 업그레이드는 비활성화되어 있습니다. 꼭 필요할 때만 `UPGRADE_PIP=1`을 함께 지정하세요.

포터블(이동형) 데이터
-----------------
- `data/text-fabric-data/etcbc/bhsa`를 프로젝트 내에 포함하면 네트워크 없이 실행할 수 있습니다.
- 첫 실행 시 로컬 경로가 없고 사용자 캐시가 있으면 자동 복사됩니다.

일시 정지(멈춤) 원인과 해결
------------------------
- 원인 1: 시스템 `python` 명령 부재로 스크립트 실행/테스트가 실패 → 가상환경의 Python(`.venv/bin/python`)을 사용하도록 절차를 조정했습니다.
- 원인 2: CTT 파싱 중 Text‑Fabric 원격 로드를 시도해 네트워크 타임아웃 발생 → 로컬 BHSA 데이터 존재 시에만 TF를 사용하도록 게이트를 추가했습니다. 필요 시 `CTT_SKIP_TF=1`로 완전 비활성화 가능.

구조/리팩토링 요약
----------------
- `parser/books.py`: 성경 약어/영문/한글 매핑(CTT 디렉터리/KNT 폴더 포함)을 한 곳으로 통합.
- `parser/bhsa.py`: BOOK 상수를 제거하고 `parser.books`를 참조, 로컬 TF 존재 검출(`has_local_bhsa_data`) 추가.
- `parser/ctt_parser.py`: BHSA 매핑은 로컬 TF가 있을 때만 수행하도록 변경.
- `app.py`: TF 의존 API(`/api/tf/phrases`, `/api/types`)는 로컬 TF가 없으면 503을 반환하도록 보호.
