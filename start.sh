#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND="${1:-dashboard}"
PORT="${IOT_BENCH_PORT:-${2:-}}"
VENV="$ROOT/.venv"
PYTHON="$VENV/Scripts/python.exe"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$VENV/bin/python"
fi

run_frontend() {
  if command -v bun >/dev/null 2>&1; then bun "$@"
  elif command -v npm >/dev/null 2>&1; then npm "$@"
  else echo "React setup requires Bun or Node.js/npm." >&2; return 2
  fi
}

case "$COMMAND" in
  setup)
    python -m venv "$VENV"
    "$PYTHON" -m pip install --upgrade pip
    "$PYTHON" -m pip install -r "$ROOT/ai-api/requirements-dev.txt"
    cd "$ROOT/react-app" && run_frontend install
    ;;
  test)
    cd "$ROOT/ai-api" && "$PYTHON" -m pytest -q
    cd "$ROOT/react-app" && run_frontend run build
    ;;
  firmware-build)
    cd "$ROOT/firmware" && "$PYTHON" -m platformio run
    ;;
  firmware-flash)
    if [[ -z "$PORT" ]]; then echo "firmware-flash requires a serial port" >&2; exit 2; fi
    cd "$ROOT/firmware" && "$PYTHON" -m platformio run --target upload --upload-port "$PORT"
    ;;
  sensor-firmware-build)
    "$PYTHON" -m platformio run -d "$ROOT/firmware/nano33ble-sense-diagnostics"
    ;;
  dashboard)
    cd "$ROOT/ai-api"
    if [[ -n "$PORT" ]]; then
      IOT_BENCH_PORT="$PORT" "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3
    else
      "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3
    fi
    ;;
  dashboard-react)
    cd "$ROOT/react-app" && run_frontend run dev
    ;;
  *)
    echo "Usage: bash start.sh {setup|test|firmware-build|firmware-flash|sensor-firmware-build|dashboard|dashboard-react} [port]" >&2
    exit 2
    ;;
esac
