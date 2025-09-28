@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

set "SCRIPT_DIR=%~dp0"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    set "PYTHON_CMD=%VENV_PY%"
) else (
    set "PYTHON_CMD=python"
)

"%PYTHON_CMD%" -m MusicPlayer %*
