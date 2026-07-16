@echo off
cd /d "%~dp0.."
set PYBIN=C:\Users\johnp\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
"%PYBIN%" main.py >> runtime.log 2>&1
