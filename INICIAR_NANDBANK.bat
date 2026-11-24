@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\INICIAR_WINDOWS.ps1" -Rebuild
if errorlevel 1 (echo ARRANQUE FALHOU. Consulta os logs. & pause & exit /b 1)
echo.
echo NandBank iniciado. Consulta README.md para credenciais e acesso.
pause
