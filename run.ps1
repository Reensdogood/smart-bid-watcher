$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
    & ".venv\Scripts\python.exe" -m pip install -r requirements.txt
}

& ".venv\Scripts\python.exe" main.py
