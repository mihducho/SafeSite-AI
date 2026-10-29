@echo off
rem Bat ung dung web SafeGate. Go  .\web  trong terminal VS Code (hoac bam dup file nay). Ctrl+C: dung.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000 --timeout-graceful-shutdown 3 %*
