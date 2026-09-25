param(
    [ValidateSet('1', '2', '3', 'help', 'setup', 'test', 'firmware-build', 'firmware-flash', 'sensor-firmware-build', 'react', 'html', 'both', 'status', 'stop', 'dashboard', 'dashboard-react', 'all')]
    [string]$Command = 'help',
    [string]$Port = ''
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Api = Join-Path $Root 'ai-api'
$Firmware = Join-Path $Root 'firmware'
$SensorFirmware = Join-Path $Firmware 'nano33ble-sense-diagnostics'
$ReactApp = Join-Path $Root 'react-app'
$Venv = Join-Path $Root '.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'
$ToolVenv = Join-Path $Root '.tool-venv'
$ToolPython = Join-Path $ToolVenv 'Scripts\python.exe'
$Tools = Join-Path $Root '.tools'

function Invoke-Frontend([string[]]$Arguments) {
    if (Get-Command bun -ErrorAction SilentlyContinue) { & bun @Arguments }
    elseif (Get-Command npm -ErrorAction SilentlyContinue) { & npm @Arguments }
    else { throw 'React setup requires Bun or Node.js/npm.' }
}

function Install-ArduinoCli {
    $Version = '1.5.1'
    $Destination = Join-Path $Tools 'arduino-cli'
    $Executable = Join-Path $Destination 'arduino-cli.exe'
    if (Test-Path $Executable) { return }
    $Archive = Join-Path $Tools "arduino-cli-$Version.zip"
    $Url = "https://github.com/arduino/arduino-cli/releases/download/v$Version/arduino-cli_${Version}_Windows_64bit.zip"
    $ExpectedSha256 = 'fabe42e0eb04d00e776a66178299ff95a46c623dbc260f997e58fd514853dd40'
    New-Item -ItemType Directory -Force -Path $Tools, $Destination | Out-Null
    Invoke-WebRequest -Uri $Url -OutFile $Archive
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $Archive).Hash.ToLowerInvariant() -ne $ExpectedSha256) {
        Remove-Item -LiteralPath $Archive -Force
        throw 'Arduino CLI archive checksum did not match the pinned release.'
    }
    Expand-Archive -LiteralPath $Archive -DestinationPath $Destination -Force
    Remove-Item -LiteralPath $Archive -Force
}

function Install-Tools {
    if (-not (Test-Path $Python)) {
        python -m venv $Venv
    }
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -r (Join-Path $Api 'requirements-dev.txt')
    if (-not (Test-Path $ToolPython)) {
        python -m venv $ToolVenv
    }
    & $ToolPython -m pip install --upgrade pip
    & $ToolPython -m pip install -r (Join-Path $Api 'requirements-tools.txt')
    Install-ArduinoCli
    Push-Location $ReactApp
    try { Invoke-Frontend @('install') }
    finally { Pop-Location }
}

function Test-Iot {
    Push-Location $Api
    try { & $Python -m pytest -q }
    finally { Pop-Location }
    Push-Location $ReactApp
    try { Invoke-Frontend @('run', 'build') }
    finally { Pop-Location }
}

function Build-Firmware {
    Push-Location $Firmware
    try { & $ToolPython -m platformio run }
    finally { Pop-Location }
}

function Flash-Firmware {
    if (-not $Port) { throw 'firmware-flash requires -Port COMx' }
    Push-Location $Firmware
    try { & $ToolPython -m platformio run --target upload --upload-port $Port }
    finally { Pop-Location }
}

function Build-SensorFirmware {
    & $ToolPython -m platformio run -d $SensorFirmware
}

function Start-Api {
    Push-Location $Api
    try {
        $env:IOT_BENCH_SERVE_HTML = 'false'
        if ($Port) { $env:IOT_BENCH_PORT = $Port }
        else { Remove-Item Env:IOT_BENCH_PORT -ErrorAction SilentlyContinue }
        & $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3 --ws wsproto
    }
    finally { Pop-Location }
}

function Test-ApiReady {
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2
        return [bool]$health.ok
    }
    catch { return $false }
}

function Get-ApiHealth {
    try { return Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2 }
    catch { return $null }
}

function Start-ApiBackground([bool]$ServeHtml = $false) {
    $health = Get-ApiHealth
    if ($health) {
        if ($ServeHtml -and -not $health.html_enabled) {
            throw 'The API on port 8765 was started without legacy HTML. Run .\start.ps1 stop, then .\start.ps1 both.'
        }
        Write-Host 'Hardware API already running at http://127.0.0.1:8765'
        return $null
    }
    $previousHtml = $env:IOT_BENCH_SERVE_HTML
    $previousPort = $env:IOT_BENCH_PORT
    try {
        $env:IOT_BENCH_SERVE_HTML = if ($ServeHtml) { 'true' } else { 'false' }
        if ($Port) { $env:IOT_BENCH_PORT = $Port }
        else { Remove-Item Env:IOT_BENCH_PORT -ErrorAction SilentlyContinue }
        $process = Start-Process -FilePath $Python `
            -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765','--timeout-graceful-shutdown','3','--ws','wsproto' `
            -WorkingDirectory $Api -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $Api 'server.out.log') `
            -RedirectStandardError (Join-Path $Api 'server.err.log') -PassThru
    }
    finally {
        if ($null -eq $previousHtml) { Remove-Item Env:IOT_BENCH_SERVE_HTML -ErrorAction SilentlyContinue }
        else { $env:IOT_BENCH_SERVE_HTML = $previousHtml }
        if ($null -eq $previousPort) { Remove-Item Env:IOT_BENCH_PORT -ErrorAction SilentlyContinue }
        else { $env:IOT_BENCH_PORT = $previousPort }
    }
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if (Test-ApiReady) {
            Write-Host 'Hardware API ready at http://127.0.0.1:8765'
            return $process
        }
        Start-Sleep -Milliseconds 250
    }
    throw 'Hardware API did not become ready. See ai-api/server.err.log.'
}

function Start-ReactDashboard([bool]$ServeHtml = $false) {
    $apiProcess = Start-ApiBackground -ServeHtml $ServeHtml
    Write-Host 'React bench starting at http://127.0.0.1:5173'
    Push-Location $ReactApp
    try { Invoke-Frontend @('run', 'dev') }
    finally {
        Pop-Location
        if ($apiProcess -and -not $apiProcess.HasExited) {
            Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
            Write-Host 'Stopped the API process started by this React session.'
        }
    }
}

function Start-HtmlDashboard {
    Push-Location $Api
    try {
        $env:IOT_BENCH_SERVE_HTML = 'true'
        if ($Port) { $env:IOT_BENCH_PORT = $Port }
        & $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3 --ws wsproto
    }
    finally { Pop-Location }
}

function Show-BenchStatus {
    $listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -in 5173, 5174, 8765 } |
        Sort-Object LocalPort
    if (-not $listeners) {
        Write-Host 'IoT bench is stopped.'
        return
    }
    $listeners | ForEach-Object {
        $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        Write-Host ("http://127.0.0.1:{0}  PID {1}  {2}" -f $_.LocalPort, $_.OwningProcess, $process.ProcessName)
    }
}

function Stop-Bench {
    $processIds = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -in 5173, 5174, 8765 } |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processIds) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
    Write-Host 'Stopped IoT bench listeners on ports 5173, 5174, and 8765.'
}

function Show-LaunchMenu {
    Write-Host 'IoT Hardware Connect Bench'
    Write-Host '  1  React        React on 5173 + hardware API/WebSocket on 8765'
    Write-Host '  2  HTML         HTML on 8765 + hardware API/WebSocket on 8765'
    Write-Host '  3  Both         React on 5173 + HTML/API/WebSocket on 8765'
    Write-Host ''
    Write-Host 'Run: .\start.ps1 <1|2|3>'
    Write-Host 'Other commands: status, stop, setup, test, firmware-build, firmware-flash, sensor-firmware-build'
}

if (-not $PSBoundParameters.ContainsKey('Command')) {
    Show-LaunchMenu
    $selection = Read-Host 'Select option [1-3] (or q to quit)'
    if ($selection -in 'q', 'Q', 'quit', 'exit') { return }
    if ($selection -notin '1', '2', '3') {
        Write-Error 'Invalid selection. Enter 1, 2, or 3.'
        exit 2
    }
    $Command = $selection
}

switch ($Command) {
    'help' { Show-LaunchMenu }
    '1' { Start-ReactDashboard }
    '2' { Start-HtmlDashboard }
    '3' { Start-ReactDashboard -ServeHtml $true }
    'setup' { Install-Tools }
    'test' { Test-Iot }
    'firmware-build' { Build-Firmware }
    'firmware-flash' { Flash-Firmware }
    'sensor-firmware-build' { Build-SensorFirmware }
    'react' { Start-ReactDashboard }
    'html' { Start-HtmlDashboard }
    'both' { Start-ReactDashboard -ServeHtml $true }
    'status' { Show-BenchStatus }
    'stop' { Stop-Bench }
    'dashboard' { Start-ReactDashboard }
    'dashboard-react' { Start-ReactDashboard }
    'all' {
        Install-Tools
        Test-Iot
        Build-Firmware
        Start-ReactDashboard
    }
}
