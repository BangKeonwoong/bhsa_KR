# CTT Viewer (BHSA/Text-Fabric)

간단한 플라스크 기반 뷰어로, CTT 파일과 BHSA(Text‑Fabric) 데이터를 트리 형태로 탐색할 수 있습니다.

## 빠른 시작
- 파이썬 3.9+ 권장, 가상환경 사용 권장
- 의존성: `Flask`, `text-fabric`
- 실행:
  - macOS/Linux: `./run.sh` 또는 `python app.py`
  - Windows: `start_viewer.bat` 또는 PowerShell `./start_viewer.ps1`
  - 모듈 실행: `python -m ctt_viewer`

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
- BHSA: `data/text-fabric-data/etcbc/bhsa/tf/<version>/` (서브모듈)
  - 최초 클론 후:
    - `git submodule update --init --recursive`
  - 갱신:
    - `git submodule update --remote --merge`

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
