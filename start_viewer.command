#!/bin/bash
# ETCBC CTT Viewer launcher for macOS (double-clickable)
set -euo pipefail

# Move to project directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[CTT Viewer] 프로젝트 디렉터리: $SCRIPT_DIR"

find_python() {
  candidates=(
    "python3"
    "python"
    "/usr/bin/python3"
    "/opt/homebrew/bin/python3"
    "/usr/local/bin/python3"
  )
  for c in "${candidates[@]}"; do
    if command -v "$c" >/dev/null 2>&1; then echo "$c"; return 0; fi
    if [ -x "$c" ]; then echo "$c"; return 0; fi
  done
  return 1
}

# Ensure Python and venv
PYTHON_BIN="$(find_python || true)"
if [ -z "${PYTHON_BIN:-}" ]; then
  echo "[CTT Viewer] Python3를 찾을 수 없습니다. python.org 또는 Homebrew로 Python 3를 설치하세요."
  exit 1
fi

# Ensure chosen interpreter is Python 3; fallback to python3 if needed
if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import sys; raise SystemExit(0 if sys.version_info[:1] >= (3,) else 1)
PY
then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
    echo "[CTT Viewer] 'python'이 Python 3가 아닙니다. python3로 대체합니다."
  fi
fi

recreate_venv() {
  echo "[CTT Viewer] 가상환경 재생성(.venv)"
  rm -rf .venv || true
  "$PYTHON_BIN" -m venv .venv
}

# Optionally force reset
if [ "${RESET_VENV:-}" = "1" ]; then
  recreate_venv
fi

# Create venv if missing
if [ ! -d ".venv" ] || [ ! -f ".venv/bin/activate" ]; then
  echo "[CTT Viewer] 가상환경 생성(.venv)"
  "$PYTHON_BIN" -m venv .venv
fi

echo "[CTT Viewer] 가상환경 활성화(.venv)"
# shellcheck disable=SC1091
source .venv/bin/activate

find_venv_python() {
  candidates=(
    ".venv/bin/python"
    ".venv/bin/python3"
  )
  for f in .venv/bin/python3* .venv/bin/python*; do
    [ -e "$f" ] && candidates+=("$f")
  done
  for c in "${candidates[@]}"; do
    if [ -x "$c" ]; then echo "$c"; return 0; fi
  done
  return 1
}

# Decide python executable inside venv (prefer venv python)
PY="$(find_venv_python || true)"
if [ -z "${PY:-}" ]; then
  echo "[CTT Viewer] .venv 내부 python 실행 파일을 찾지 못했습니다. 재생성합니다."
  recreate_venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  PY="$(find_venv_python || true)"
fi
if [ -z "${PY:-}" ]; then PY="python"; fi
echo "[CTT Viewer] 사용 중인 Python: $PY"

# Prefer local TF data inside project if present; also import from user cache once
PROJECT_DIR="$SCRIPT_DIR"
LOCAL_TF_DIR="$PROJECT_DIR/data/text-fabric-data"
USER_TF_DIR="$HOME/text-fabric-data"
if [ ! -d "$LOCAL_TF_DIR/etcbc/bhsa" ] && [ -d "$USER_TF_DIR/etcbc/bhsa" ]; then
  echo "[CTT Viewer] 로컬 TF 데이터가 없어 사용자 캐시에서 복사합니다."
  mkdir -p "$LOCAL_TF_DIR/etcbc" 2>/dev/null || true
  cp -R "$USER_TF_DIR/etcbc/bhsa" "$LOCAL_TF_DIR/etcbc/" 2>/dev/null || true
fi
export TF_LOCAL_DIR="$LOCAL_TF_DIR"
# Prefer project dir first so ./bhsa is used when present
export TF_LOCATIONS="$PROJECT_DIR:$LOCAL_TF_DIR"

# Optional: check TF updates each launch (default OFF). Enable by setting TF_UPDATE_ON_START=1
# if [ -z "${TF_UPDATE_ON_START:-}" ]; then export TF_UPDATE_ON_START=0; fi

repair_pip() {
  echo "[CTT Viewer] pip 복구 시도(ensurepip)"
  "$PY" -m ensurepip --upgrade --default-pip || true
}

# Install dependencies if needed (fast, offline-aware)
if [ -f "requirements.txt" ]; then
  echo "[CTT Viewer] 의존성 설치 확인(pip)"
  if [ "${SKIP_PIP:-}" != "1" ]; then
    # Quick module check to skip pip when already satisfied
    if "$PY" - >/dev/null 2>&1 <<'PY'
import importlib, sys
ok = True
for m in ("flask", "tf.fabric"):
    try:
        importlib.import_module(m)
    except Exception:
        ok = False
        break
raise SystemExit(0 if ok else 1)
PY
    then
      echo "[CTT Viewer] 요구 모듈이 이미 설치되어 pip 건너뜀"
    else
      if ! "$PY" -m pip --version >/dev/null 2>&1; then
        repair_pip
      fi
      if ! "$PY" -m pip --version >/dev/null 2>&1; then
        echo "[CTT Viewer] pip 부트스트랩(get-pip) 시도"
        TMPPIP="$(mktemp -t get-pip.XXXXXX.py)"
        CURL_BIN="$(command -v curl || echo /usr/bin/curl)"
        if [ -x "$CURL_BIN" ]; then
          "$CURL_BIN" -fsSL https://bootstrap.pypa.io/get-pip.py -o "$TMPPIP" || true
          "$PY" "$TMPPIP" || true
          rm -f "$TMPPIP"
        else
          echo "[CTT Viewer] curl 미존재로 pip 자동 설치를 생략합니다."
        fi
      fi
      export PIP_DISABLE_PIP_VERSION_CHECK=1
      export PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT:-10}
      # Install from local wheels if available
      if ls data/wheels/*.whl >/dev/null 2>&1; then
        echo "[CTT Viewer] 로컬 휠에서 설치 시도(data/wheels)"
        "$PY" -m pip install --no-index --find-links data/wheels -r requirements.txt || true
      fi
      # If still missing flask, attempt online best-effort
      if ! "$PY" - >/dev/null 2>&1 <<'PY'
import importlib, sys
ok = True
for m in ("flask",):
    try:
        importlib.import_module(m)
    except Exception:
        ok = False
        break
raise SystemExit(0 if ok else 1)
PY
      then
        if command -v curl >/dev/null 2>&1 && ! curl -sI --max-time 5 https://pypi.org/simple/ >/dev/null; then
          echo "[CTT Viewer] 네트워크 연결이 원활하지 않아 의존성 설치를 건너뜁니다."
          echo "               인터넷 연결 후 재실행하거나, data/wheels 폴더에 휠을 준비하세요."
        else
          if [ "${UPGRADE_PIP:-}" = "1" ]; then
            "$PY" -m pip install --upgrade "pip<25" || true
          fi
          "$PY" -m pip install -r requirements.txt || true
        fi
      fi
    fi
  else
    echo "[CTT Viewer] SKIP_PIP=1 설정으로 pip 설치를 건너뜀"
  fi
fi

# Ensure data dir
mkdir -p data

# Auto-detect/copy Korean gloss CSV into project data if not set
if [ -z "${GLOSS_KO_CSV:-}" ]; then
  # Prefer already bundled file
  if [ -f "data/gloss_ko.csv" ]; then
    export GLOSS_KO_CSV="data/gloss_ko.csv"
  else
    dl="$HOME/Downloads"
    hit=""
    for f in "$dl"/all_gloss*.csv "$dl"/*/all_gloss*.csv; do
      if [ -f "$f" ]; then hit="$f"; break; fi
    done
    if [ -n "$hit" ]; then
      cp "$hit" data/gloss_ko.csv 2>/dev/null || true
      export GLOSS_KO_CSV="data/gloss_ko.csv"
      echo "[CTT Viewer] 한글 gloss 파일 복사: $hit -> data/gloss_ko.csv"
    fi
  fi
fi

# Prefetch 기능 제거됨(패키징 스크립트 삭제). 최초 실행 시 필요한 범위만 자동 캐시합니다.

# Start server
export PYTHONUNBUFFERED=1
HOST=127.0.0.1
# Fixed port: 5001 (user request)
PORT=5001
export HOST PORT
URL="http://$HOST:$PORT/"
PORT_FILE="$SCRIPT_DIR/data/server_port.txt"
export PORT_FILE

echo "[CTT Viewer] 서버 시작: $URL"
"$PY" app.py &
SERVER_PID=$!

# Graceful shutdown on exit
cleanup() { echo "\n[CTT Viewer] 서버 중지..."; kill "$SERVER_PID" 2>/dev/null || true; }
trap cleanup INT TERM EXIT

# Wait briefly for server to come up (best-effort)
for i in {1..25}; do
  sleep 0.2
  if command -v curl >/dev/null 2>&1; then
    if curl -s -o /dev/null "$URL"; then break; fi
  else
    # If curl not available, just wait a bit longer and continue
    :
  fi
done
if ! curl -s -o /dev/null "$URL" 2>/dev/null; then
  if [ -f "$PORT_FILE" ]; then
    ACTUAL_PORT="$(cat "$PORT_FILE" 2>/dev/null || true)"
    if [ -n "$ACTUAL_PORT" ]; then
      PORT="$ACTUAL_PORT"; URL="http://$HOST:$PORT/"
    fi
  fi
fi

# Open browser
if command -v open >/dev/null 2>&1; then
  echo "[CTT Viewer] 브라우저 열기: $URL"
  open "$URL"
else
  echo "[CTT Viewer] 'open' 명령을 찾을 수 없음. 수동으로 $URL 접속하세요."
fi

echo "[CTT Viewer] 실행 중... (중지: Ctrl+C)"
wait "$SERVER_PID"
