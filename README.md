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
- 빠른(얕은) 다운로드로 용량/시간 절약(네트워크 여건에 따라 권장):
  ```bash
  git submodule update --init --depth 1 --recommend-shallow --recursive
  # 이후 업데이트 시도 시에도 동일하게 얕게 유지하려면 아래처럼 실행
  git submodule update --remote --merge --depth 1 --recommend-shallow
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
- 주의(용량): 전체 히스토리를 포함한 서브모듈은 수백 MB 이상이 될 수 있습니다. 얕은 클론(`--depth 1`)을 사용하면 속도/용량을 줄일 수 있습니다.

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

## 참고
- 최초 실행 시 로컬 BHSA 데이터가 없으면 `run.sh`/`start_viewer.ps1`가 사용자 캐시(`~/text-fabric-data`)에서 복사 시도합니다.
- 대용량 데이터로 인해 일부 경로는 서브모듈로 관리됩니다.
