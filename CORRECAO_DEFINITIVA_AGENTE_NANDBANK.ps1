# NandBank - correcao do agente. Windows PowerShell 5.1
# Executar NA RAIZ DO PROJECTO. Nao altera volumes nem bases de dados.
$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$agent = Join-Path $root 'scripts\AGENTE_NOS_WINDOWS.ps1'
$envPath = Join-Path $root '.env'
$task = 'NandBank-Agente-Nos'
if (!(Test-Path -LiteralPath $agent) -or !(Test-Path -LiteralPath $envPath)) { throw 'Execute na raiz do NandBank, onde existem .env e scripts\AGENTE_NOS_WINDOWS.ps1' }
if (!(Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue)) { throw 'A tarefa NandBank-Agente-Nos nao existe.' }
$backup = "$agent.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
Copy-Item -LiteralPath $agent -Destination $backup -ErrorAction Stop
$agentCode = @'
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$regions = @('af','eu','as','na','sa','oc')
$envLine = Get-Content -LiteralPath (Join-Path $root '.env') | Where-Object { $_ -match '^CONTROL_AGENT_KEY=' } | Select-Object -First 1
if (-not $envLine) { throw 'CONTROL_AGENT_KEY ausente' }
$key = $envLine.Substring('CONTROL_AGENT_KEY='.Length).Trim().Trim('"').Trim("'")
if ([string]::IsNullOrWhiteSpace($key)) { throw 'CONTROL_AGENT_KEY vazio' }
$base = 'https://127.0.0.1:8443/api/agent'
$logFile = Join-Path $root 'agente-nandbank.log'
function Log([string]$message) {
  Add-Content -LiteralPath $logFile -Encoding UTF8 -Value ("$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $message")
}
# IMPORTANTE: nao chamar parametro $args (variavel automatica do PowerShell).
function Invoke-CurlNandBank {
  param([Parameter(Mandatory=$true)][string[]]$CurlArguments)
  $response = & curl.exe @CurlArguments 2>&1
  $exit = $LASTEXITCODE
  $out = ($response | Out-String).Trim()
  if ($exit -ne 0) { throw "curl falhou codigo=$exit texto=$out" }
  return $out
}
function ContainerState([string]$service) {
  $cid = (& docker compose ps -q -a $service 2>&1 | Out-String).Trim()
  if ($LASTEXITCODE -ne 0) { throw "Nao foi possivel consultar Docker $service" }
  if (-not $cid) { return 'missing' }
  $state = (& docker inspect --format '{{.State.Status}}' $cid 2>&1 | Out-String).Trim()
  if ($LASTEXITCODE -ne 0) { throw "Nao foi possivel inspeccionar $service" }
  return $state
}
Log 'NOVO AGENTE iniciado com parametros curl corrigidos'
while ($true) {
  try {
    $getParams = @('-k','-sS','--fail','--max-time','8','-H',("X-Agent-Key: " + $key),($base + '/jobs'))
    $raw = Invoke-CurlNandBank -CurlArguments $getParams
    $parsed = ConvertFrom-Json -InputObject $raw
    $jobs = @($parsed)
    foreach ($job in $jobs) {
      if ($null -eq $job -or $regions -notcontains $job.region -or $job.action -notin @('STOP_PRIMARY','START_PRIMARY')) { continue }
      $service = [string]$job.region + '-primary'
      $desired = if ($job.action -eq 'STOP_PRIMARY') { 'exited' } else { 'running' }
      $ok = $false
      $result = ''
      try {
        $state = ContainerState $service
        Log "job=$($job.id) action=$($job.action) actual=$state esperado=$desired"
        if ($state -eq $desired) {
          $ok = $true
          $result = "Estado ja confirmado via docker inspect: $service=$state. Sem repetir a operacao."
        } else {
          if ($job.action -eq 'STOP_PRIMARY') {
            $output = & docker compose stop -t 30 $service 2>&1
          } else {
            $output = & docker compose up -d --no-build $service 2>&1
          }
          $exit = $LASTEXITCODE
          $stateAfter = ContainerState $service
          $ok = ($exit -eq 0 -and $stateAfter -eq $desired)
          $result = "Docker exit=$exit; estado=$stateAfter; saida=$(($output | Out-String).Trim())"
        }
      } catch {
        $result = 'Falha Docker: ' + $_.Exception.Message
        Log $result
      }
      $body = @{ok=[bool]$ok; result=([string]$result).Substring(0,[Math]::Min(480,([string]$result).Length))} | ConvertTo-Json -Compress
      $jsonPath = Join-Path $env:TEMP ('nandbank-' + [guid]::NewGuid().ToString('N') + '.json')
      try {
        [System.IO.File]::WriteAllText($jsonPath,$body,(New-Object System.Text.UTF8Encoding($false)))
        $postParams = @('-k','-sS','--fail','--max-time','10','-X','POST','-H',('X-Agent-Key: ' + $key),'-H','Content-Type: application/json','--data-binary',('@' + $jsonPath),($base + '/jobs/' + $job.id + '/result'))
        $confirmed = $false
        for ($n=1; $n -le 3; $n++) {
          try {
            $reply = Invoke-CurlNandBank -CurlArguments $postParams
            Log "CONFIRMADO job=$($job.id) ok=$ok resposta=$reply"
            $confirmed = $true
            break
          } catch {
            Log "ERRO POST tentativa=$n job=$($job.id): $($_.Exception.Message)"
            Start-Sleep -Seconds 2
          }
        }
        if (-not $confirmed) { Log "FALHA FINAL job=$($job.id): permanece pendente" }
      } finally {
        Remove-Item -LiteralPath $jsonPath -Force -ErrorAction SilentlyContinue
      }
    }
  } catch {
    Log "ERRO CONSULTA: $($_.Exception.Message)"
  }
  Start-Sleep -Seconds 3
}
'@
[System.IO.File]::WriteAllText($agent,$agentCode,(New-Object System.Text.UTF8Encoding($false)))
Write-Host "Backup preservado: $backup" -ForegroundColor Green
Write-Host 'A reiniciar APENAS a tarefa do agente...' -ForegroundColor Cyan
Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object {
  $_.ProcessId -ne $PID -and $_.CommandLine -match 'AGENTE_NOS_WINDOWS\.ps1'
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-ScheduledTask -TaskName $task
Start-Sleep -Seconds 12
Write-Host "`n=== TAREFA ===" -ForegroundColor Cyan
Get-ScheduledTask -TaskName $task | Select-Object TaskName,State | Format-Table -AutoSize
Write-Host "`n=== LOGS ===" -ForegroundColor Cyan
if (Test-Path (Join-Path $root 'agente-nandbank.log')) { Get-Content -LiteralPath (Join-Path $root 'agente-nandbank.log') -Tail 15 }
Write-Host "`n=== AFRICA ===" -ForegroundColor Cyan
& docker compose ps -a af-primary af-standby
Write-Host "`nActualize o painel e procure COMPLETED. Se continuar PENDING envie as ultimas 15 linhas do log." -ForegroundColor Yellow
