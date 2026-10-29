@echo off
rem Menu demo bao cao tien do. Bam dup file nay, hoac go  .\demo  trong terminal VS Code.
cd /d "%~dp0"
".venv\Scripts\python.exe" scripts\demo.py %*
