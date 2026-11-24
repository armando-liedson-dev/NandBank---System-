@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CORRIGIR_E_INICIAR_NANDBANK.ps1"
if errorlevel 1 (
  echo.
  echo FALHA. Envie nandbank_arranque_diagnostico.log para diagnostico.
  pause
  exit /b 1
)
echo.
echo NandBank iniciado. Abra https://localhost:8443
pause
