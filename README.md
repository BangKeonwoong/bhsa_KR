# CTT Viewer (BHSA/Text-Fabric)

간단한 플라스크 기반 뷰어로, CTT 파일과 BHSA(Text‑Fabric) 데이터를 트리 형태로 탐색할 수 있습니다.

## 빠른 시작
- 파이썬 3.9+ 권장, 가상환경 사용 권장
- 의존성: `Flask`, `text-fabric`
- 실행:
  - macOS/Linux: `./run.sh` 또는 `python app.py`
  - Windows: `start_viewer.bat` 또는 PowerShell `./start_viewer.ps1`
  - 모듈 실행: `python -m ctt_viewer`

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
