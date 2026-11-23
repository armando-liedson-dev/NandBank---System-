# Executar na raiz NandBank. Diagnostico nao destrutivo.
$ErrorActionPreference='Continue'
Set-Location -LiteralPath $PSScriptRoot
Write-Host "`n=== FASE 1: TAREFA E AGENTE ===" -ForegroundColor Cyan
Get-ScheduledTask -TaskName 'NandBank-Agente-Nos' -ErrorAction SilentlyContinue | Select-Object TaskName,State
Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object {$_.CommandLine -match 'AGENTE_NOS_WINDOWS\.ps1'} | Select-Object ProcessId,Name
Write-Host "`n=== GATEWAY ===" -ForegroundColor Cyan
& curl.exe -k -sS --max-time 8 https://127.0.0.1:8443/api/health
Write-Host "`n=== FASES 2-4: SERVICOS ===" -ForegroundColor Cyan
& docker compose ps --format 'table {{.Service}}\t{{.Status}}'
Write-Host "`n=== FASES 2-4: LOGS DO GATEWAY ===" -ForegroundColor Cyan
& docker compose logs --tail 35 gateway
Write-Host "`n=== ALERTAS DE INTERVENCAO ===" -ForegroundColor Cyan
Write-Host 'No painel, faca uma accao de STOP_PRIMARY apenas quando o standby da regiao estiver UP.'
Write-Host 'Confirme que a intervencao aparece como COMPLETED, teste a operacao e depois START_PRIMARY.'
Write-Host 'Nunca use docker compose down -v nem docker volume rm para este teste.'
