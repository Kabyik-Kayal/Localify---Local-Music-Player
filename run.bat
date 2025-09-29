@echo off
SETLOCAL ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

set "PYTHON_CMD="
if exist "%SCRIPT_DIR%.venv\Scripts\pythonw.exe" set "PYTHON_CMD=%SCRIPT_DIR%.venv\Scripts\pythonw.exe"
if not defined PYTHON_CMD if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" set "PYTHON_CMD=%SCRIPT_DIR%.venv\Scripts\python.exe"

if not defined PYTHON_CMD (
    for %%I in (pythonw.exe python.exe) do (
        if not defined PYTHON_CMD (
            where %%I >nul 2>&1
            if not errorlevel 1 set "PYTHON_CMD=%%I"
        )
    )
)

if not defined PYTHON_CMD (
    msg * "Python was not found. Please run install.bat first." >nul 2>&1
    if errorlevel 1 echo Python was not found. Please run install.bat first.
    goto :cleanup
)

start "Localify" "%PYTHON_CMD%" -m MusicPlayer %*

:cleanup
popd >nul
ENDLOCAL