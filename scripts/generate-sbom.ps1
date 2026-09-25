$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$output = Join-Path $root "artifacts\sbom"
$localPython = Join-Path $root ".venv\Scripts\python.exe"
$python = if ($env:IOT_BENCH_PYTHON) {
    $env:IOT_BENCH_PYTHON
}
elseif (Test-Path $localPython) {
    $localPython
}
else {
    (Get-Command python -ErrorAction Stop).Source
}
$toolSitePackages = Join-Path $root ".tool-venv\Lib\site-packages"

if (-not (Test-Path $toolSitePackages)) {
    throw "Hardware-tool environment is missing. Run .\start.ps1 once before generating SBOMs."
}

New-Item -ItemType Directory -Force -Path $output | Out-Null

& $python -m pip_audit -r (Join-Path $root "ai-api\requirements.txt") `
    --format cyclonedx-json --output (Join-Path $output "python-api.cdx.json")
if ($LASTEXITCODE -ne 0) { throw "API SBOM generation failed." }

& $python -m pip_audit --path $toolSitePackages `
    --ignore-vuln PYSEC-2026-2132 `
    --ignore-vuln PYSEC-2026-1941 `
    --ignore-vuln PYSEC-2026-1942 `
    --ignore-vuln PYSEC-2026-161 `
    --ignore-vuln PYSEC-2026-2281 `
    --ignore-vuln PYSEC-2026-2280 `
    --ignore-vuln PYSEC-2026-249 `
    --ignore-vuln PYSEC-2026-248 `
    --format cyclonedx-json --output (Join-Path $output "python-tools.cdx.json")
if ($LASTEXITCODE -ne 0) { throw "Hardware-tool SBOM generation failed." }

Push-Location (Join-Path $root "react-app")
try {
    npm sbom --omit=dev --sbom-format cyclonedx |
        Out-File -FilePath (Join-Path $output "react.cdx.json") -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw "React SBOM generation failed." }
}
finally {
    Pop-Location
}

Get-ChildItem $output -Filter "*.cdx.json" | ForEach-Object {
    $document = Get-Content $_.FullName -Raw | ConvertFrom-Json
    if ($document.bomFormat -ne "CycloneDX" -or -not $document.components) {
        throw "$($_.Name) is not a populated CycloneDX document."
    }
    Write-Output "$($_.Name): $($document.components.Count) components, CycloneDX $($document.specVersion)"
}

& $python (Join-Path $root "scripts\dependency_inventory.py")
if ($LASTEXITCODE -ne 0) { throw "Dependency license inventory generation failed." }
