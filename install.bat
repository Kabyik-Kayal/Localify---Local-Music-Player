@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

echo.
echo ==========================================
echo           Localify Installer
echo ==========================================
echo.
echo Starting installation...
echo.

REM Create VBScript for progress updates and final dialog
echo Dim objShell > progress.vbs
echo Set objShell = CreateObject("WScript.Shell") >> progress.vbs
echo. >> progress.vbs
echo ' Run installation >> progress.vbs
echo Set objExec = objShell.Exec("cmd /c install_worker.bat") >> progress.vbs
echo. >> progress.vbs
echo ' Show progress updates >> progress.vbs
echo Dim i, progressBar >> progress.vbs
echo i = 0 >> progress.vbs
echo Do While objExec.Status = 0 >> progress.vbs
echo     i = i + 1 >> progress.vbs
echo     If i Mod 5 = 0 Then >> progress.vbs
echo         Dim percent, barLength, filledLength, j >> progress.vbs
echo         percent = (i Mod 50) * 2 >> progress.vbs
echo         If percent = 0 Then percent = 98 >> progress.vbs
echo         barLength = 30 >> progress.vbs
echo         filledLength = Int((percent / 100) * barLength) >> progress.vbs
echo         progressBar = "[" >> progress.vbs
echo         For j = 1 To filledLength >> progress.vbs
echo             progressBar = progressBar ^& "=" >> progress.vbs
echo         Next >> progress.vbs
echo         For j = filledLength + 1 To barLength >> progress.vbs
echo             progressBar = progressBar ^& " " >> progress.vbs
echo         Next >> progress.vbs
echo         progressBar = progressBar ^& "] " ^& percent ^& "%%" >> progress.vbs
echo         WScript.Echo progressBar >> progress.vbs
echo     End If >> progress.vbs
echo     WScript.Sleep 200 >> progress.vbs
echo Loop >> progress.vbs
echo. >> progress.vbs
echo ' Final progress >> progress.vbs
echo WScript.Echo "[==============================] 100%%" >> progress.vbs
echo WScript.Echo "" >> progress.vbs
echo. >> progress.vbs
echo ' Show completion message >> progress.vbs
echo If objExec.ExitCode = 0 Then >> progress.vbs
echo     WScript.Echo "Installation completed successfully!" >> progress.vbs
echo     MsgBox "Installation completed successfully!" ^& vbCrLf ^& "You can now run Localify.", vbInformation + vbOKOnly, "Localify Installer" >> progress.vbs
echo Else >> progress.vbs
echo     WScript.Echo "Installation failed!" >> progress.vbs
echo     MsgBox "Installation failed." ^& vbCrLf ^& "Please check your system and try again.", vbCritical + vbOKOnly, "Localify Installer" >> progress.vbs
echo End If >> progress.vbs

REM Create the actual installation script
echo @echo off > install_worker.bat
echo SETLOCAL ENABLEDELAYEDEXPANSION >> install_worker.bat
echo. >> install_worker.bat
echo REM Check if Python is installed >> install_worker.bat
echo python --version ^>nul 2^>^&1 >> install_worker.bat
echo if errorlevel 1 ^( >> install_worker.bat
echo     curl -o python-installer.exe https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe ^>nul 2^>^&1 >> install_worker.bat
echo     if errorlevel 1 ^( >> install_worker.bat
echo         exit /b 1 >> install_worker.bat
echo     ^) >> install_worker.bat
echo     python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 >> install_worker.bat
echo     if errorlevel 1 ^( >> install_worker.bat
echo         exit /b 1 >> install_worker.bat
echo     ^) >> install_worker.bat
echo     del python-installer.exe ^>nul 2^>^&1 >> install_worker.bat
echo ^) >> install_worker.bat
echo. >> install_worker.bat
echo set "SCRIPT_DIR=%%~dp0" >> install_worker.bat
echo set "VENV_PY=%%SCRIPT_DIR%%.venv\Scripts\python.exe" >> install_worker.bat
echo if exist "%%VENV_PY%%" ^( >> install_worker.bat
echo     set "PYTHON_CMD=%%VENV_PY%%" >> install_worker.bat
echo ^) else ^( >> install_worker.bat
echo     set "PYTHON_CMD=python" >> install_worker.bat
echo ^) >> install_worker.bat
echo. >> install_worker.bat
echo "%%PYTHON_CMD%%" setup.py ^>nul 2^>^&1 >> install_worker.bat
echo exit /b %%ERRORLEVEL%% >> install_worker.bat

REM Run the installation with progress dialog
cscript //nologo progress.vbs

REM Cleanup temporary files
del install_worker.bat >nul 2>&1
del progress.vbs >nul 2>&1

ENDLOCAL
