@echo off
cd /d "%~dp0"
set "PATH=C:\Program Files\Graphviz\bin;%PATH%"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)
echo Diagram Studio: http://127.0.0.1:7860
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 7860
echo.
echo Server da dung.
pause
