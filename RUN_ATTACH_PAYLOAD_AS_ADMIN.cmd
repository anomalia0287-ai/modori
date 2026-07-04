@echo off
setlocal

set "SCRIPT=%~dp0scripts\attach_modori_payload_disk.ps1"
set "LOG=C:\VM\ModoriPayload\attach-payload-v2.log"

if not exist "%SCRIPT%" (
    echo Script was not found:
    echo %SCRIPT%
    echo.
    pause
    exit /b 2
)

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo This file must be run as Administrator.
    echo.
    echo Close this window, then:
    echo 1. Right-click RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd
    echo 2. Click "Run as administrator"
    echo 3. Click Yes in the Windows permission prompt
    echo.
    echo No VM changes were made.
    echo.
    pause
    exit /b 5
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -RebuildPayload
set "RC=%ERRORLEVEL%"
echo.
echo Attach script exit code: %RC%
echo Log: %LOG%
echo Press any key to close this window.
pause >nul
exit /b %RC%
