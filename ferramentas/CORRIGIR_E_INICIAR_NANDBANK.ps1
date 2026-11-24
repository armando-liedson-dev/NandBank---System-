# NandBank - recuperacao segura de download incompleto do PostgreSQL
# Executar na pasta raiz do NandBank. Nao remove volumes nem credenciais.
param([int]$Tentativas=6)
$ErrorActionPreference='Stop'
$raiz=Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $raiz
$log=Join-Path $raiz 'nandbank_arranque_diagnostico.log'
Start-Transcript -Path $log -Force | Out-Null
try {
    Write-Host '=== NandBank: diagnostico e recuperacao ===' -ForegroundColor Cyan
    if (-not (Test-Path (Join-Path $raiz 'docker-compose.yml'))) {throw 'docker-compose.yml nao encontrado. Coloque os dois scripts na raiz NandBank.'}
    if (-not (Test-Path (Join-Path $raiz 'scripts/INICIAR_WINDOWS.ps1'))) {throw 'scripts/INICIAR_WINDOWS.ps1 nao encontrado.'}
    & docker info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) {throw 'Docker Desktop nao esta a responder. Inicie-o e tente novamente.'}
    $ok=$false
    for ($i=1; $i -le $Tentativas; $i++) {
        Write-Host "`n=== PostgreSQL 16 Alpine: tentativa $i de $Tentativas ===" -ForegroundColor Cyan
        & docker pull postgres:16-alpine
        $pullExit=$LASTEXITCODE
        if ($pullExit -eq 0) {
            & docker image inspect postgres:16-alpine --format '{{.Id}}'
            if ($LASTEXITCODE -eq 0) {$ok=$true;break}
        }
        if ($i -lt $Tentativas) {
            $espera=[Math]::Min(15*$i,75)
            Write-Host "Download incompleto (codigo $pullExit). Nova tentativa em $espera segundos..." -ForegroundColor Yellow
            Start-Sleep -Seconds $espera
        }
    }
    if (-not $ok) {throw 'Nao foi possivel descarregar postgres:16-alpine. Verifique espaco livre, rede, VPN/proxy e Docker Desktop; consulte o log.'}
    Write-Host "`n=== Verificar imagens ja construidas ===" -ForegroundColor Cyan
    & docker image ls
    Write-Host "`n=== Iniciar com script original SEM reconstruir ===" -ForegroundColor Cyan
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $raiz 'scripts/INICIAR_WINDOWS.ps1')
    if ($LASTEXITCODE -ne 0) {throw 'O arranque do NandBank falhou. Consulte os logs abaixo.'}
    Write-Host "`n=== Estado final ===" -ForegroundColor Cyan
    & docker compose ps
    if ($LASTEXITCODE -ne 0) {throw 'Falha ao consultar docker compose ps.'}
    Write-Host "`n=== Testar resposta HTTPS do Gateway ===" -ForegroundColor Cyan
    try {
        & curl.exe -k -sS --max-time 20 -o NUL -w 'HTTP %{http_code}' https://localhost:8443/
        Write-Host ''
    } catch {Write-Host 'Gateway ainda nao respondeu; consulte os logs.' -ForegroundColor Yellow}
    Write-Host "`nArranque concluido. Abra https://localhost:8443" -ForegroundColor Green
    Write-Host 'Se os contentores nao estiverem saudaveis, execute .\TESTAR_NANDBANK.bat.'
} catch {
    Write-Host "`nERRO: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`n=== Estado e ultimos logs ===" -ForegroundColor Yellow
    & docker compose ps 2>&1 | Out-Host
    & docker compose logs --tail=35 gateway router db-global 2>&1 | Out-Host
    Write-Host 'Nao foram apagados volumes nem credenciais.' -ForegroundColor Yellow
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
