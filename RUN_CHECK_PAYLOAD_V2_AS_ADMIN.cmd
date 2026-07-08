@echo off
setlocal

set "SCRIPT=%~dp0scripts\check_modori_payload_v2.ps1"

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
    echo 1. Right-click RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd
    echo 2. Click "Run as administrator"
    echo 3. Click Yes in the Windows permission prompt
    echo.
    echo No VM changes were made.
    echo.
    pause
    exit /b 5
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
set "RC=%ERRORLEVEL%"
echo.
echo Check script exit code: %RC%
echo.
echo Expected current-payload evidence:
echo - STATUS: Payload V2 is attached to VM
echo - STATUS: Payload V2 is current for the packaged app
echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%
