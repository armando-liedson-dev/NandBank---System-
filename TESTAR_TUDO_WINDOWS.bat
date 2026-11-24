@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\TESTAR_TUDO_WINDOWS.ps1"
echo.
pause
