@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0APLICAR_VISUAL_NANDBANK.ps1"
if errorlevel 1 (echo Atualizacao falhou. & pause & exit /b 1)
echo Atualizacao finalizada.
pause
