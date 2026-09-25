#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT/ai-api"
exec "$ROOT/.venv/bin/python" mcp_server.py
