$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$graphviz = "C:\Program Files\Graphviz\bin"
if (Test-Path "$graphviz\dot.exe") {
    $env:PATH = "$graphviz;" + $env:PATH
}
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}
Write-Host "Diagram Studio: http://127.0.0.1:7860"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 7860
