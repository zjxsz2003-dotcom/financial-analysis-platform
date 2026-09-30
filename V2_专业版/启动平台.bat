@echo off
cd /d "%~dp0"
title Financial Analysis Platform V2

set "PYEXE=D:\jiqixuexi1\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

echo Starting... browser will open http://localhost:8601
echo (Keep this window open. Close it to stop the server.)
timeout /t 2 >nul
start "" http://localhost:8601

"%PYEXE%" -m streamlit run app.py --server.port 8601 --server.headless true
pause
