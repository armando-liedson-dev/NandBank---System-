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
          # Docker Compose pode escrever mensagens normais no stderr. Em
          # Windows PowerShell 5.1 isso pode gerar excecao com Stop.
          # A confirmacao depende do estado REAL e nao do texto da consola.
          $previousPreference = $ErrorActionPreference
          $ErrorActionPreference = 'Continue'
          try {
            if ($job.action -eq 'STOP_PRIMARY') {
              $output = & docker compose stop -t 30 $service 2>&1
            } else {
              $output = & docker compose up -d --no-build $service 2>&1
            }
            $exit = $LASTEXITCODE
          } finally {
            $ErrorActionPreference = $previousPreference
          }
          $stateAfter = ContainerState $service
          $ok = ($stateAfter -eq $desired)
          $result = "Docker exit=$exit; estado=$stateAfter; saida=$(($output | Out-String).Trim())"
          if ($exit -ne 0 -and $ok) { Log "Docker reportou erro mas $service atingiu estado=$desired" }
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
