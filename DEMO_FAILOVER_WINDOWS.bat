@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\DEMO_FAILOVER_WINDOWS.ps1" -Regiao af
echo.
pause
