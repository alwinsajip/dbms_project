@echo off
cd /d "%~dp0.."
set PYBIN=%~dp0..\.venv\Scripts\python.exe
"%PYBIN%" main.py >> runtime.log 2>&1
