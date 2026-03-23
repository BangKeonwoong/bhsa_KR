# CTT Viewer (BHSA/Text-Fabric)

플라스크 기반 웹 앱으로 CTT 파일과 BHSA(Text-Fabric) 데이터를 트리 형태로 탐색합니다.

## Windows

### 준비물
- Git (<https://git-scm.com/downloads>)
- Python 3.9 이상 (<https://www.python.org/downloads/>)

### 우측 ‘역본’ 패널(KNT/NKRV/BHS)
- 상단 바의 `역본` 버튼으로 우측 패널을 열고 닫습니다.
- 버전을 선택하면 해당 장의 모든 절이 패널에 표시됩니다.
- 절 위에 마우스를 올리면 트리뷰의 해당 절에 속하는 절/절요소가 1.25배로 확대됩니다.
- 절을 클릭하면 상세 패널이 열리고, 해당 절의 첫 번째 clause가 자동 선택됩니다.
- 키보드 지원: Enter/Space로 절 선택, Esc로 패널 닫기, 포커스는 패널 내에서 순환(Tab/Shift+Tab).

## 비개발자용 빠른 실행 (권장 순서)

### 설치 및 실행
```powershell
git clone --recurse-submodules https://github.com/BangKeonwoong/bhsa_KR.git
cd bhsa_KR
start_viewer.bat        # 또는 PowerShell: .\setup_windows.ps1 -AutoInstall
```
실행 후 브라우저에서 <http://127.0.0.1:5001/> 를 열어 “TF gloss 사용 가능” 메시지를 확인하세요.

## macOS / Linux

### 준비물
- Git (<https://git-scm.com/downloads>)
- Python 3.9 이상 (<https://www.python.org/downloads/> , macOS는 `brew install python` 도 가능)

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
  - 폰트/데이터도 지정 가능: `FONT_DIR`, `DATA_CTT_DIR`
  - 역본 데이터 경로 지정(선택): `VERSIONS_DIR`(루트), 또는 개별 `KNT_DIR`, `NKRV_DIR`, `BHS_DIR`

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
- 정적 배포 산출물에도 `openapi.yaml`, `api-docs.html`이 포함되지만, 내용은 로컬 Flask API 기준 참고 문서입니다.

## 정적 배포

이 프로젝트는 이제 로컬 Flask 서버 모드와 별도로 정적 호스트용 export를 지원합니다.

### 정적 사이트 export
```bash
python3 scripts/export_static.py --out dist
```

선택 옵션
- 특정 책만 export: `--books genesis`
- 책당 장 수 제한: `--max-chapters 1`

### 로컬 정적 스모크 테스트
```bash
python3 scripts/export_static.py --out dist
python3 -m http.server 8000 -d dist
```

브라우저에서 `http://127.0.0.1:8000/`를 열고 확인하세요.
- 책/장 선택
- TF/CTT source 전환
- 상세 패널
- 역본 패널
- 브라우저 네트워크 탭에서 `/api/*` 요청이 없는지 확인

### GitHub Pages
- `.github/workflows/pages.yml` 이 `main` 브랜치 push 또는 수동 실행 시 `dist/`를 생성해 Pages에 배포합니다.
- Pages는 저장소 서브패스를 사용하므로, 정적 모드 자산과 데이터는 모두 상대 경로로 로드됩니다.


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

1) 레포 클론(서브모듈 포함 필수) 및 실행
```bash
git clone --recurse-submodules https://github.com/BangKeonwoong/bhsa_KR.git
cd bhsa_KR
./run.sh                # 최초 실행 시 venv 및 의존성 자동 설치
```
권한 오류가 발생하면 `chmod +x run.sh` 후 다시 실행하세요. 서버가 뜨면 브라우저에서 <http://127.0.0.1:5001/> 를 확인합니다.

## Docker (선택)

```bash
docker build -t ctt-viewer .
docker run --rm -p 5001:5001 -v $(pwd)/data:/app/data ctt-viewer
```

## 추가 문서

- `README-RUN.txt` : 실행 스크립트 상세
- `README-RUN-windows.txt`, `README-RUN-macOS.txt` : 운영체제별 안내
