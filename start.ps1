param(
    [ValidateSet('setup', 'test', 'firmware-build', 'firmware-flash', 'sensor-firmware-build', 'dashboard', 'dashboard-react', 'all')]
    [string]$Command = 'dashboard',
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
    try { & $Python -m platformio run }
    finally { Pop-Location }
}

function Flash-Firmware {
    if (-not $Port) { throw 'firmware-flash requires -Port COMx' }
    Push-Location $Firmware
    try { & $Python -m platformio run --target upload --upload-port $Port }
    finally { Pop-Location }
}

function Build-SensorFirmware {
    & $Python -m platformio run -d $SensorFirmware
}

function Start-Dashboard {
    Push-Location $Api
    try {
        if ($Port) { $env:IOT_BENCH_PORT = $Port }
        else { Remove-Item Env:IOT_BENCH_PORT -ErrorAction SilentlyContinue }
        & $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --timeout-graceful-shutdown 3
    }
    finally { Pop-Location }
}

function Start-ReactDashboard {
    Push-Location $ReactApp
    try { Invoke-Frontend @('run', 'dev') }
    finally { Pop-Location }
}

switch ($Command) {
    'setup' { Install-Tools }
    'test' { Test-Iot }
    'firmware-build' { Build-Firmware }
    'firmware-flash' { Flash-Firmware }
    'sensor-firmware-build' { Build-SensorFirmware }
    'dashboard' { Start-Dashboard }
    'dashboard-react' { Start-ReactDashboard }
    'all' {
        Install-Tools
        Test-Iot
        Build-Firmware
        Start-Dashboard
    }
}
