# CTT Viewer (BHSA/Text-Fabric)

간단한 플라스크 기반 뷰어로, CTT 파일과 BHSA(Text‑Fabric) 데이터를 트리 형태로 탐색할 수 있습니다.

## 빠른 시작
- 파이썬 3.9+ 권장, 가상환경 사용 권장
- 의존성: `Flask`, `text-fabric`
- 실행:
  - macOS/Linux: `./run.sh` 또는 `python app.py`
  - Windows: `start_viewer.bat` 또는 PowerShell `./start_viewer.ps1`
- 모듈 실행: `python -m ctt_viewer`
 - 클론 시 항상 서브모듈 포함 권장: `git clone --recurse-submodules <repo>`

## 비개발자용 빠른 실행 (권장 순서)

### Windows
1) Git 설치 후 레포 클론(서브모듈 포함)
```
git clone --recurse-submodules https://github.com/BangKeonwoong/bhsa_KR.git
cd bhsa_KR
```
2) 실행(권장):
```
 .\start_viewer.bat
```
- PowerShell 정책으로 `.ps1` 실행이 막히는 환경에서도 `.bat`가 자동으로 우회(-ExecutionPolicy Bypass).
- Python이 없으면 자동으로 embeddable Python(3.11)을 다운로드/설정 후 진행합니다(최초 1회).

옵션: 자동 설치 도우미(winget)
```
# winget이 있고, Python/Git 미설치라면 자동 설치 후 실행
PowerShell> .\setup_windows.ps1 -AutoInstall
# 또는 환경변수로
PowerShell> $env:AUTO_INSTALL='1'; .\setup_windows.ps1
```

3) 브라우저 열림 확인: `http://127.0.0.1:5001/`
   - 상단 상태가 “TF gloss 사용 가능”이면 정상. 문제가 있으면 `Invoke-RestMethod http://127.0.0.1:5001/api/tf/status`로 확인.

문제 해결(Tips)
- “명령을 인식하지 못함”: PowerShell은 현재 폴더 실행에 `./` 또는 `.\`가 필요합니다. ` .\start_viewer.bat`처럼 실행하세요.
- 실행 정책 오류: `start_viewer.bat`를 사용하거나, `powershell -NoProfile -ExecutionPolicy Bypass -File .\start_viewer.ps1`로 실행.
- 방화벽 팝업: 허용해야 브라우저 접근이 가능합니다.
- 오프라인(네트워크 제한): `data/wheels/` 폴더에 미리 `.whl` 파일(Flask, text-fabric 등)을 넣어두면 런처가 우선 사용합니다. 상세: `data/wheels/README.md` 참조.

### macOS
1) Git & Python 3 준비
- Git이 없으면 Xcode Command Line Tools로 설치: `xcode-select --install`
- Python 3이 없다면 Homebrew 설치 후: `brew install python`

2) 레포 클론(서브모듈 포함)
```
git clone --recurse-submodules https://github.com/BangKeonwoong/bhsa_KR.git
cd bhsa_KR
```

3) 실행
```
./run.sh            # 일반 실행
AUTO_INSTALL=1 ./run.sh   # Python 미설치 시 Homebrew로 자동 설치 시도
```
- 권한 문제 시: `chmod +x run.sh` 후 재실행
- 최초 실행 시 venv 생성, pip로 의존성 설치, 사용자 캐시(`~/text-fabric-data`)에서 TF 데이터 복사 시도

더블클릭 런처
- Finder에서 `Start Viewer.command`를 더블클릭하여 바로 실행할 수 있습니다.
- 내부적으로 `run.sh`를 호출하며, 기본적으로 `AUTO_INSTALL=1`이 설정되어 Python 자동 설치를 시도합니다.

4) 브라우저: `http://127.0.0.1:5001/` → 상태 “TF gloss 사용 가능” 확인

트러블슈팅
- Python 미설치: `brew install python`
- 포트 충돌: `PORT=5002 ./run.sh`처럼 다른 포트 지정
- TF 데이터 미탑재: `/api/tf/status` 확인 후, `data/text-fabric-data/etcbc/bhsa/tf/<version>`에 파일이 있는지 점검
- Gatekeeper(보안) 경고 발생 시:
  - 오른쪽 클릭 → “열기(Open)” → 확인 대화 상자에서 “열기” 선택
  - 또는 시스템 설정 → 보안 및 개인 정보 보호(Privacy & Security) → “차단된 앱 허용(Allow Anyway)” → 다시 실행 후 “열기”
  - 필요 시 격리 속성 제거: `xattr -d com.apple.quarantine "Start Viewer.command"` 및 `xattr -d com.apple.quarantine ./run.sh`
  - 실행 권한 부여: `chmod +x "Start Viewer.command" ./run.sh`

## 패키징/설치
- 로컬 설치(개발):
  - `pip install -e .`
  - 실행: `ctt-viewer` 또는 `python -m ctt_viewer`
- 정적 리소스 경로(설치 환경):
  - 기본적으로 패키지 내부 또는 저장소 루트의 `static/`을 자동 탐지합니다.
  - 필요 시 환경변수로 지정: `STATIC_DIR=/path/to/static`
  - 폰트/데이터도 지정 가능: `FONT_DIR`, `DATA_CTT_DIR`, `KNT_DIR`

## Docker 실행
이미지 빌드/실행 예시는 다음과 같습니다. 대용량 데이터(`data/`)는 이미지에 포함하지 않고 런타임에 마운트하는 것을 권장합니다.

1) 빌드
```
docker build -t ctt-viewer:local .
```

2) 실행 (호스트의 `./data`를 컨테이너 `/app/data`로 마운트)
```
docker run --rm -it \
  -p 5001:5001 \
  -e HOST=0.0.0.0 -e PORT=5001 \
  -e ENABLE_COMPRESSION=1 \
  -v $(pwd)/data:/app/data \
  ctt-viewer:local
```

선택 환경변수
- `STATIC_DIR=/app/static` (기본값) — 빌드에 포함된 정적 자원 사용
- `TF_LOCAL_DIR=/app/data/text-fabric-data` — Text‑Fabric 데이터 루트 힌트
- `TF_LOCATIONS=/app:/app/data/text-fabric-data` — 탐색 경로 우선순위 제어
- `GLOSS_KO_CSV=/app/data/gloss_ko.csv` — 영어→한글 gloss CSV 경로

### Docker Compose
`compose.yaml`을 제공하여 더 간단히 실행할 수 있습니다.

1) 빌드: `docker compose build`

2) 실행: `docker compose up -d`

3) 종료: `docker compose down`

기본 설정은 포트 5001 노출과 `./data` 마운트를 포함합니다. 환경변수는 `compose.yaml`의 `environment` 섹션에서 조정하세요.

## API 문서
- OpenAPI 스펙: `/openapi.yaml`
- 문서 UI(Redoc): `/api/docs`


## 데이터
- CTT: `data/ctt/<book>/<chapter>/*.CTT`
- BHSA(Text‑Fabric): `data/text-fabric-data/etcbc/bhsa/tf/<version>/` (서브모듈)

### BHSA 데이터 가져오기(서브모듈)
- 처음부터 서브모듈까지 함께 클론(추천):
  ```bash
  git clone --recurse-submodules https://github.com/BangKeonwoong/bhsa_KR.git
  ```
- 이미 레포를 클론했다면(서브모듈 초기화):
  ```bash
  git submodule update --init --recursive
  ```
- 서브모듈 갱신(최신 BHSA 반영):
  ```bash
  git submodule update --remote --merge
  # 갱신된 서브모듈 커밋을 부모 레포에 반영하려면 커밋 필요
  git add data/bhsa data/text-fabric-data/etcbc/bhsa
  git commit -m "chore: update BHSA submodules"
  ```
- 확인: 아래 경로에 TF 버전 디렉터리가 보여야 합니다(예: `tf/2021`, `tf/2020`, 또는 `tf/c`).
  ```bash
  ls -1 data/text-fabric-data/etcbc/bhsa/tf
  ```
- 주의(용량): 전체 히스토리를 포함한 서브모듈은 수백 MB 이상이 될 수 있습니다.

## 설치 순서(서브모듈 포함, TF 탑재 상태 보장)
아래 순서를 따르면 Text‑Fabric BHSA가 로컬에 탑재된 상태로 바로 실행됩니다.

1) 레포 클론(서브모듈 포함 필수)
```bash
git clone --recurse-submodules https://github.com/BangKeonwoong/bhsa_KR.git
cd bhsa_KR
```

2) 실행 스크립트로 의존성/환경 준비 및 서버 구동
- macOS/Linux: `./run.sh`
- Windows(PowerShell): `./start_viewer.ps1`

3) 확인(브라우저/상태 API)
- 브라우저: `http://127.0.0.1:5001/` (상단에 “TF gloss 사용 가능” 표시)
- API: `curl http://127.0.0.1:5001/api/tf/status` → `{"has_local_bhsa": true, "has_gloss": true}`

참고: 만약 서브모듈 없이 클론했다면 아래 한 번만 실행 후 다시 2단계로 진행하세요.
```bash
git submodule update --init --recursive
```

### 대안: Text‑Fabric가 자동으로 내려받도록 사용
- 로컬에 BHSA가 없을 경우 Text‑Fabric가 사용자 캐시(`~/text-fabric-data`)로 내려받을 수 있습니다. 이 레포의 실행 스크립트(run.sh/start_viewer.ps1)는 사용자 캐시에서 `data/text-fabric-data`로 복사 시도를 합니다.
- 수동으로 내려받기(예시):
  ```bash
  # 가상환경 등에서 실행
  python - <<'PY'
from tf.fabric import Fabric
TF = Fabric(locations='data/text-fabric-data', modules=['etcbc/bhsa/tf/2021'])
api = TF.load('otext otype oslots')
print('OK' if api else 'FAIL')
PY
  ```

## 주요 엔드포인트
- `/` 정적 UI
- `/api/tree` CTT 또는 TF 기반 트리 (query: `book`, `chapter`, `source=tf|ctt`, `lite=1|0`)
- `/api/tf/status` 로컬 BHSA 및 gloss 기능 가용성
- `/api/books`, `/api/books/chapters` KNT 기준 책/장 정보
- `/api/knt/verse` KNT 구절 텍스트 조회

## 설정 (환경변수)
- `CACHE_MAX_AGE`(기본 300), `CACHE_SWR`(기본 60)
- `LOG_LEVEL`(기본 INFO), `WERKZEUG_LOG_LEVEL`
- `ACCESS_LOG`(기본 1), `ACCESS_LOG_SKIP`(기본 `/healthz`)
- `TF_LOCATIONS`, `TF_LOCAL_DIR`(Text‑Fabric 데이터 탐색 경로)
- `GLOSS_KO_CSV`(영→한 gloss CSV 경로, 기본 `data/gloss_ko.csv` 자동 탐색)

## 개발 구조
- `ctt_viewer/`
  - `__init__.py` 앱 팩토리, 블루프린트 등록
  - `api.py` API 라우트
  - `paths.py` 경로 유틸
  - `http_utils.py` HTTP 캐시/응답 유틸
  - `logging_config.py` 로깅 설정
  - `errors.py` 전역 에러 핸들러(JSON)
  - `middleware.py` 요청 로깅
  - `__main__.py` 모듈 실행 엔트리
- `parser/` CTT/BHSA 파서 및 유틸
- `tests/` 간단 라우트 테스트

## 테스트
```
python -m unittest discover -s tests -p "test_*.py" -v
```

## 릴리즈(태그 기반)
태그 `v*`를 푸시하면 GitHub Actions가 자동으로 릴리즈를 생성합니다.

1) 버전 업데이트: `pyproject.toml`의 `version`
2) `CHANGELOG.md` 갱신
3) 커밋/푸시 후 태그 생성/푸시
```
git commit -am "Release: bump to vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main --tags
```
4) 릴리즈 확인: GitHub → Releases (자동 릴리즈 노트 생성)

### 릴리즈 ZIP 사용하기
- Releases 페이지에서 OS별 ZIP을 내려받아 압축 해제합니다.
  - Windows: `ctt_viewer-windows-vX.Y.Z.zip`
  - macOS: `ctt_viewer-macos-vX.Y.Z.zip`
- 포함 내용: 실행 스크립트/코드/정적 파일(대용량 TF 데이터 제외)
- Windows: `start_viewer.bat` 실행 (필요 시 `setup_windows.ps1 -AutoInstall`)
- macOS: 더블클릭 `Start Viewer.command` 또는 터미널에서 `./run.sh`
- 주의: 릴리즈 ZIP에는 BHSA 서브모듈 데이터가 포함되지 않습니다. TF가 자동으로 사용자 캐시로 내려받거나, 개발용으로는 서브모듈 포함 클론을 권장합니다.

## 참고
- 최초 실행 시 로컬 BHSA 데이터가 없으면 `run.sh`/`start_viewer.ps1`가 사용자 캐시(`~/text-fabric-data`)에서 복사 시도합니다.
- 대용량 데이터로 인해 일부 경로는 서브모듈로 관리됩니다.
