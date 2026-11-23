param([string]$LanIP='', [switch]$Rebuild)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
function Secret([int]$count=24) {
    $bytes=New-Object byte[] $count
    $random=[System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {$random.GetBytes($bytes)} finally {$random.Dispose()}
    return ([Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_') + 'Aa1')
}
function Run-Docker([string]$step,[string[]]$cmd){
    Write-Host "`n=== $step ===" -ForegroundColor Cyan
    & docker @cmd
    if ($LASTEXITCODE -ne 0){throw "$step falhou (exit $LASTEXITCODE)."}
}
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {throw 'Docker Desktop nao encontrado.'}
    Run-Docker 'Verificar Docker Desktop' @('info','--format','{{.ServerVersion}}')
    if (-not $LanIP) {
        try {
            $adapter=Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway -and $_.IPv4Address} | Select-Object -First 1
            $LanIP=($adapter.IPv4Address | Select-Object -First 1).IPAddress
        } catch {}
    }
    if (-not $LanIP){$LanIP='127.0.0.1'}
    $changedIP=$false
    if (-not (Test-Path .env)) {
        $pg=Secret;$admin=Secret;$regional=Secret;$teller=Secret;$branch=Secret;$integrity=Secret 48;$cert=Secret
        $managerAF=Secret;$managerAS=Secret;$managerNA=Secret;$managerSA=Secret;$managerOC=Secret
        @(
          "PG_PASSWORD=$pg", "ADMIN_PASSWORD=$admin", "REGIONAL_PASSWORD=$regional",
          "TELLER_PASSWORD=$teller", "BRANCH_PASSWORD=$branch",
          "MANAGER_AF_PASSWORD=$managerAF", "MANAGER_AS_PASSWORD=$managerAS",
          "MANAGER_NA_PASSWORD=$managerNA", "MANAGER_SA_PASSWORD=$managerSA", "MANAGER_OC_PASSWORD=$managerOC",
          "INTEGRITY_KEY=$integrity", "CERT_PASSWORD=$cert", "CONTROL_AGENT_KEY=$(Secret 48)",
          "LAN_IP=$LanIP", 'POSTGRES_DB=globalscale', 'POSTGRES_USER=globalscale', 'BIND_IP=0.0.0.0'
        ) | Set-Content -Encoding ASCII .env
        @(
          'NandBank - Credenciais iniciais (NAO PARTILHAR NEM PUBLICAR)',
          "Painel: https://localhost:8443", "Telemoveis: https://${LanIP}:8443",
          "Gerente global: admin@nandbank.local / $admin",
          "Gerente Europa: regional.eu@nandbank.local / $regional",
          "Gerente Africa: regional.af@nandbank.local / $managerAF",
          "Gerente Asia: regional.as@nandbank.local / $managerAS",
          "Gerente America do Norte: regional.na@nandbank.local / $managerNA",
          "Gerente America do Sul: regional.sa@nandbank.local / $managerSA",
          "Gerente Oceania: regional.oc@nandbank.local / $managerOC",
          "Gerente Filial Maputo: filial.maputo@nandbank.local / $branch",
          "Operador Maputo: balcao.maputo@nandbank.local / $teller",
          'Clientes: criar conta atraves da interface web (saldo inicial zero).'
        ) | Set-Content -Encoding UTF8 .credentials
        $changedIP=$true
    } else {
        $envtxt=Get-Content -Raw .env
        if ($envtxt -match '(?m)^LAN_IP=([^\r\n]*)') {
            if($Matches[1] -ne $LanIP){$changedIP=$true;$envtxt=[regex]::Replace($envtxt,'(?m)^LAN_IP=.*$',"LAN_IP=$LanIP")}
        } else {$envtxt += "`nLAN_IP=$LanIP`n";$changedIP=$true}
        Set-Content -Path .env -Value $envtxt -Encoding ASCII
    }
    # Garantir chave do agente ao actualizar uma instalação antiga (sem recriar os segredos existentes).
    $envtxt = Get-Content -Raw .env
    if ($envtxt -notmatch '(?m)^CONTROL_AGENT_KEY=') {
      Add-Content -Path .env -Value ('CONTROL_AGENT_KEY=' + (Secret 48)) -Encoding ASCII
    }
    $env:COMPOSE_PARALLEL_LIMIT='1'
    Run-Docker 'Validar Compose' @('compose','config','--quiet')
    $images = ((& docker image ls --format '{{.Repository}}:{{.Tag}}') -join "`n")
    $buildBank=($images -notmatch 'globalscale-bank:1\.0') -or $Rebuild
    $buildLegacy=($images -notmatch 'globalscale-legacy:1\.0') -or $Rebuild
    if ($buildBank){Run-Docker 'Construir imagem Python e interface offline (sem npm)' @('compose','build','gateway')}
    if ($buildLegacy){Run-Docker 'Construir modulo legado Java (sem Maven)' @('compose','build','legacy')}
    if ($changedIP){
        Run-Docker 'Actualizar certificados do IP LAN' @('compose','run','--rm','--no-deps','cert-init')
    }
    Run-Docker 'Iniciar sistema completo' @('compose','up','-d','--no-build')
    if($changedIP){Run-Docker 'Reiniciar Gateway com certificado renovado' @('compose','restart','gateway')}
    Run-Docker 'Estado dos contentores' @('compose','ps')
    # O agente corre no HOST, apenas com seis serviços permitidos; não expomos docker.sock ao Gateway.
    $agentPidFile = Join-Path (Get-Location) '.nandbank-agent.pid'
    $running=$false
    if (Test-Path $agentPidFile) {
        $oldPid=0
        if ([int]::TryParse(((Get-Content $agentPidFile -ErrorAction SilentlyContinue) -join ''),[ref]$oldPid)) {
            if (Get-Process -Id $oldPid -ErrorAction SilentlyContinue) {$running=$true}
        }
    }
    if (-not $running) {
        $agentScript = Join-Path $PSScriptRoot 'AGENTE_NOS_WINDOWS.ps1'
        $proc=Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$agentScript+'"')) -PassThru -WindowStyle Hidden
        Set-Content -Path $agentPidFile -Value $proc.Id
        Write-Host ('Agente de nos NandBank iniciado (PID '+$proc.Id+').') -ForegroundColor Green
    }
    Write-Host "`nAbra no PC: https://localhost:8443" -ForegroundColor Green
    Write-Host "Telemoveis na mesma rede: https://${LanIP}:8443" -ForegroundColor Green
    Write-Host 'Credenciais de gerente: Get-Content .credentials' -ForegroundColor Yellow
    Write-Host 'Nota: certificados academicos exigem confiar na CA de teste nos telemoveis.' -ForegroundColor Yellow
} catch {
    Write-Host "`nERRO: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Para diagnostico: docker compose ps; docker compose logs --tail=40 gateway router db-global' -ForegroundColor Yellow
    exit 1
}
