#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND="${1:-}"
PORT="${IOT_BENCH_PORT:-${2:-}}"
VENV="$ROOT/.venv"
PYTHON="$VENV/Scripts/python.exe"
TOOL_VENV="$ROOT/.tool-venv"
TOOL_PYTHON="$TOOL_VENV/Scripts/python.exe"
TOOLS="$ROOT/.tools"

resolve_python_paths() {
  PYTHON="$VENV/Scripts/python.exe"
  TOOL_PYTHON="$TOOL_VENV/Scripts/python.exe"
  [[ -x "$PYTHON" ]] || PYTHON="$VENV/bin/python"
  [[ -x "$TOOL_PYTHON" ]] || TOOL_PYTHON="$TOOL_VENV/bin/python"
}

resolve_python_paths

find_powershell() {
  if command -v powershell.exe >/dev/null 2>&1; then
    command -v powershell.exe
  elif [[ -x /c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe ]]; then
    printf '%s\n' /c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
  elif command -v pwsh.exe >/dev/null 2>&1; then
    command -v pwsh.exe
  elif command -v pwsh >/dev/null 2>&1; then
    command -v pwsh
  fi
}

run_frontend() {
  if command -v bun >/dev/null 2>&1; then bun "$@"
  elif command -v npm >/dev/null 2>&1; then npm "$@"
  else echo "React setup requires Bun or Node.js/npm." >&2; return 2
  fi
}

install_arduino_cli() {
  local version="1.5.1"
  local destination="$TOOLS/arduino-cli"
  local executable="$destination/arduino-cli.exe"
  local archive="$TOOLS/arduino-cli-$version.zip"
  local expected_sha256="fabe42e0eb04d00e776a66178299ff95a46c623dbc260f997e58fd514853dd40"
  local url="https://github.com/arduino/arduino-cli/releases/download/v$version/arduino-cli_${version}_Windows_64bit.zip"
  local actual_sha256

  [[ -f "$executable" ]] && return
  mkdir -p "$TOOLS" "$destination"
  curl -fL "$url" -o "$archive"
  actual_sha256="$(sha256sum "$archive" | awk '{print tolower($1)}')"
  if [[ "$actual_sha256" != "$expected_sha256" ]]; then
    rm -f "$archive"
    echo "Arduino CLI archive checksum did not match the pinned release." >&2
    return 1
  fi
  unzip -oq "$archive" -d "$destination"
  rm -f "$archive"
}

show_launch_menu() {
  cat <<'EOF'
IoT Hardware Connect Bench
  1  React        React on 5173 + hardware API/WebSocket on 8765
  2  HTML         HTML on 8765 + hardware API/WebSocket on 8765
  3  Both         React on 5173 + HTML/API/WebSocket on 8765

Run: ./start.sh <1|2|3>
Other commands: status, stop, setup, test, firmware-build, firmware-flash, sensor-firmware-build
EOF
}

choose_launch_mode() {
  show_launch_menu
  if [[ ! -t 0 ]]; then
    return 1
  fi

  printf '\nSelect option [1-3] (or q to quit): '
  read -r COMMAND
  case "$COMMAND" in
    1|2|3) return 0 ;;
    q|Q|quit|exit) return 1 ;;
    *)
      echo "Invalid selection. Enter 1, 2, or 3." >&2
      return 2
      ;;
  esac
}

start_api() {
  local serve_html="${1:-false}"
  if command -v curl >/dev/null 2>&1 && curl -fsS http://127.0.0.1:8765/api/health >/dev/null 2>&1; then
    if [[ "$serve_html" == "true" ]] && ! curl -fsS http://127.0.0.1:8765/api/health | grep -Eq '"html_enabled"[[:space:]]*:[[:space:]]*true'; then
      echo "The API on port 8765 was started without legacy HTML. Run ./start.sh stop, then ./start.sh both." >&2
      exit 2
    fi
    echo "Hardware API already running at http://127.0.0.1:8765"
    return
  fi
  cd "$ROOT/ai-api"
  if [[ -n "$PORT" ]]; then
    IOT_BENCH_SERVE_HTML="$serve_html" IOT_BENCH_PORT="$PORT" "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3 --ws wsproto >server.out.log 2>server.err.log &
  else
    IOT_BENCH_SERVE_HTML="$serve_html" "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3 --ws wsproto >server.out.log 2>server.err.log &
  fi
  API_PID=$!
  trap 'kill "$API_PID" 2>/dev/null || true' EXIT
  for _ in {1..30}; do
    if command -v curl >/dev/null 2>&1 && curl -fsS http://127.0.0.1:8765/api/health >/dev/null 2>&1; then
      echo "Hardware API ready at http://127.0.0.1:8765"
      return
    fi
    sleep 0.25
  done
  echo "Hardware API did not become ready. See ai-api/server.err.log." >&2
  exit 1
}

if [[ -z "$COMMAND" ]]; then
  if choose_launch_mode; then
    :
  else
    selection_status=$?
    [[ "$selection_status" -eq 1 ]] && exit 0
    exit "$selection_status"
  fi
fi

case "$COMMAND" in
  help|-h|--help)
    show_launch_menu
    ;;
  1)
    start_api false
    echo "React bench starting at http://127.0.0.1:5173"
    cd "$ROOT/react-app" && run_frontend run dev
    ;;
  2)
    cd "$ROOT/ai-api"
    if [[ -n "$PORT" ]]; then
      IOT_BENCH_SERVE_HTML=true IOT_BENCH_PORT="$PORT" "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3 --ws wsproto
    else
      IOT_BENCH_SERVE_HTML=true "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3 --ws wsproto
    fi
    ;;
  3)
    start_api true
    echo "React: http://127.0.0.1:5173 | HTML: http://127.0.0.1:8765"
    cd "$ROOT/react-app" && run_frontend run dev
    ;;
  setup)
    if [[ ! -x "$PYTHON" ]]; then python -m venv "$VENV"; resolve_python_paths; fi
    "$PYTHON" -m pip install --upgrade pip
    "$PYTHON" -m pip install -r "$ROOT/ai-api/requirements-dev.txt"
    if [[ ! -x "$TOOL_PYTHON" ]]; then python -m venv "$TOOL_VENV"; resolve_python_paths; fi
    "$TOOL_PYTHON" -m pip install --upgrade pip
    "$TOOL_PYTHON" -m pip install -r "$ROOT/ai-api/requirements-tools.txt"
    install_arduino_cli
    cd "$ROOT/react-app" && run_frontend install
    ;;
  test)
    cd "$ROOT/ai-api" && "$PYTHON" -m pytest -q
    cd "$ROOT/react-app" && run_frontend run build
    ;;
  firmware-build)
    cd "$ROOT/firmware" && "$TOOL_PYTHON" -m platformio run
    ;;
  firmware-flash)
    if [[ -z "$PORT" ]]; then echo "firmware-flash requires a serial port" >&2; exit 2; fi
    cd "$ROOT/firmware" && "$TOOL_PYTHON" -m platformio run --target upload --upload-port "$PORT"
    ;;
  sensor-firmware-build)
    "$TOOL_PYTHON" -m platformio run -d "$ROOT/firmware/nano33ble-sense-diagnostics"
    ;;
  react|dashboard|dashboard-react)
    start_api false
    echo "React bench starting at http://127.0.0.1:5173"
    cd "$ROOT/react-app" && run_frontend run dev
    ;;
  html)
    cd "$ROOT/ai-api"
    if [[ -n "$PORT" ]]; then
      IOT_BENCH_SERVE_HTML=true IOT_BENCH_PORT="$PORT" "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3 --ws wsproto
    else
      IOT_BENCH_SERVE_HTML=true "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3 --ws wsproto
    fi
    ;;
  both)
    start_api true
    echo "React: http://127.0.0.1:5173 | HTML: http://127.0.0.1:8765"
    cd "$ROOT/react-app" && run_frontend run dev
    ;;
  status)
    POWERSHELL="$(find_powershell || true)"
    if [[ -n "$POWERSHELL" ]]; then
      "$POWERSHELL" -NoProfile -Command '$listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -in 5173,5174,8765 | Sort-Object LocalPort; if ($listeners) { $listeners | ForEach-Object { $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "http://127.0.0.1:$($_.LocalPort)  PID $($_.OwningProcess)  $($process.ProcessName)" } } else { "IoT bench is stopped." }'
    else
      lsof -nP -iTCP:5173 -iTCP:5174 -iTCP:8765 -sTCP:LISTEN 2>/dev/null || true
    fi
    ;;
  stop)
    POWERSHELL="$(find_powershell || true)"
    if [[ -n "$POWERSHELL" ]]; then
      "$POWERSHELL" -NoProfile -Command 'Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -in 5173,5174,8765 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }'
    else
      for port in 5173 5174 8765; do fuser -k "${port}/tcp" 2>/dev/null || true; done
    fi
    echo "Stopped IoT bench listeners on ports 5173, 5174, and 8765."
    ;;
  all)
    "$0" setup
    "$0" test
    "$0" firmware-build
    "$0" react "${PORT:-}"
    ;;
  *)
    show_launch_menu >&2
    exit 2
    ;;
esac
