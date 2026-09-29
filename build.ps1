$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
& ".venv\Scripts\python.exe" -m pytest
if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
& ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean SmartBidWatcher.spec
if ($LASTEXITCODE -ne 0) {
    throw "EXE build failed. If Smart Bid Watcher is running, exit it from the tray and run build.ps1 again."
}

Write-Host ""
Write-Host "Build complete: dist\Smart Bid Watcher.exe"
