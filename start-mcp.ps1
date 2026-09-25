$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Run .\start.ps1 once to install the local environment." }
Set-Location (Join-Path $root "ai-api")
& $python "mcp_server.py"
