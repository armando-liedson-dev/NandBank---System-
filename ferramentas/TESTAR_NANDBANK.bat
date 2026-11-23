@echo off
cd /d "%~dp0"
call TESTAR_TUDO_WINDOWS.bat
if errorlevel 1 exit /b 1
echo.
echo Concluido. Se tiver Python instalado, pode executar: python VALIDAR_NANDBANK.py
echo O teste de falhas e efectuado separadamente: DEMO_FAILOVER_WINDOWS.bat
pause
