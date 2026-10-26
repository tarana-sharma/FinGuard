
@echo off
cd /d "%~dp0backend"
call "venv\Scripts\python.exe" app.py
pause
