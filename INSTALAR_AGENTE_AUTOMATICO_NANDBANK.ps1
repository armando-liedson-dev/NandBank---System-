# Executar na raiz do NandBank. Windows PowerShell 5.1.
# Nao altera volumes, contentores ou saldos.
$ErrorActionPreference = 'Stop'
$raiz = $PSScriptRoot
$agente = Join-Path $raiz 'scripts\AGENTE_NOS_WINDOWS.ps1'
$envFile = Join-Path $raiz '.env'
$tarefa = 'NandBank-Agente-Nos'
if (-not (Test-Path -LiteralPath $agente)) { throw "Agente nao encontrado: $agente" }
if (-not (Test-Path -LiteralPath $envFile)) { throw 'Ficheiro .env inexistente.' }
if (-not (Select-String -Path $envFile -Pattern '^CONTROL_AGENT_KEY=\S+' -Quiet)) { throw 'CONTROL_AGENT_KEY em falta no .env.' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker nao encontrado no PATH.' }
& docker info --format '{{.ServerVersion}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop nao esta em execucao.' }
Write-Host 'A limpar apenas agentes NandBank anteriores...' -ForegroundColor Cyan
$anterior = @(Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe' OR Name = 'pwsh.exe'" | Where-Object {
    $_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine -match '(?i)AGENTE_NOS_WINDOWS\.ps1' -and $_.CommandLine -match '(?i)NandBank'
})
foreach ($p in $anterior) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $agente + '"') -WorkingDirectory $raiz
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$existing = Get-ScheduledTask -TaskName $tarefa -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $tarefa -Confirm:$false }
Register-ScheduledTask -TaskName $tarefa -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'NandBank: agente local de controlo dos nos Docker' | Out-Null
Start-ScheduledTask -TaskName $tarefa
Start-Sleep -Seconds 8
Write-Host '\n=== TAREFA ===' -ForegroundColor Cyan
Get-ScheduledTask -TaskName $tarefa | Select-Object TaskName,State
Write-Host '\n=== PROCESSO DO AGENTE ===' -ForegroundColor Cyan
Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { $_.CommandLine -match '(?i)AGENTE_NOS_WINDOWS\.ps1' } | Select-Object ProcessId,Name
Write-Host '\n=== API ===' -ForegroundColor Cyan
& curl.exe -k -sS --max-time 8 'https://127.0.0.1:8443/api/health'
Write-Host '\nVerifique o painel: https://localhost:8443/gerente/infraestrutura' -ForegroundColor Green
