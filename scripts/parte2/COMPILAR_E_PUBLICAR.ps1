#requires -Version 5.1
<#
Build React no directorio frontend-premium-source, testa e publica em frontend/static.
Reconstroi apenas o servico Docker gateway, preservando os volumes PostgreSQL.
#>
param([switch]$SoCompilar, [switch]$SemTestes)
$ErrorActionPreference = 'Stop'
$env:GIT_PAGER = 'cat'
function Assert-OK([string]$Etapa) { if ($LASTEXITCODE -ne 0) { throw "$Etapa falhou (codigo $LASTEXITCODE)." } }
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$frontend = Join-Path $raiz 'frontend-premium-source'
$novo = Join-Path $frontend 'dist-gateway'
$destino = Join-Path $raiz 'frontend\static'
$temporario = Join-Path $raiz 'frontend\static-parte2-temporario'
$backup = Join-Path $raiz ('.private-backups\parte2-static-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if ((git -C $raiz branch --show-current).Trim() -cne 'Parte2') { throw 'Execute apenas na branch Parte2.' }
if (-not (Test-Path (Join-Path $raiz 'backend\app\gateway.py'))) { throw 'Falta backend existente.' }
if (-not (Test-Path (Join-Path $raiz 'backend\Dockerfile'))) { throw 'Falta Dockerfile do Gateway.' }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Instale Node.js e npm antes de compilar.' }
if (Test-Path $temporario) { throw 'Ja existe publicacao temporaria. Verifique antes de continuar.' }
Push-Location $raiz
try {
    Write-Host "`n1. Verificar contrato FastAPI" -ForegroundColor Cyan
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 .\scripts\parte2\VALIDAR_CONTRATO.py }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { & python .\scripts\parte2\VALIDAR_CONTRATO.py }
    else { throw 'Python nao encontrado para validar o contrato.' }
    Assert-OK 'Validar contrato'
    Push-Location $frontend
    try {
        Write-Host "`n2. Instalar dependencias com package-lock" -ForegroundColor Cyan
        npm ci --no-audit --no-fund
        Assert-OK 'npm ci'
        if (-not $SemTestes) {
            Write-Host "`n3. Testes criticos do frontend" -ForegroundColor Cyan
            npm run test:critical
            Assert-OK 'Testes criticos'
        }
        Write-Host "`n4. Compilar React (API real, same-origin)" -ForegroundColor Cyan
        npm run build:gateway
        Assert-OK 'Build gateway'
    } finally { Pop-Location }
    foreach ($exigido in @('index.html','assets','images\nandbank-lion-logo.png')) {
        if (-not (Test-Path (Join-Path $novo $exigido))) { throw "Build incompleto: $exigido" }
    }
    $html = Get-Content -Raw (Join-Path $novo 'index.html')
    if ($html -notmatch '/static/assets/') { throw 'Build nao utiliza o caminho /static/assets.' }
    if ($SoCompilar) { Write-Host "`nBuild criado em $novo. Nenhum servico Docker foi alterado." -ForegroundColor Green; return }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop nao encontrado.' }
    docker compose config --quiet
    Assert-OK 'Validacao Docker Compose'
    New-Item -ItemType Directory -Path (Split-Path $temporario -Parent) -Force | Out-Null
    New-Item -ItemType Directory -Path $temporario -Force | Out-Null
    Copy-Item -Path (Join-Path $novo '*') -Destination $temporario -Recurse -Force
    if (-not (Test-Path (Join-Path $temporario 'index.html'))) { throw 'Falha ao preparar publicacao.' }
    $alterou = $false
    try {
        New-Item -ItemType Directory -Path (Split-Path $backup -Parent) -Force | Out-Null
        if (Test-Path $destino) { Move-Item -LiteralPath $destino -Destination $backup }
        $alterou = $true
        Move-Item -LiteralPath $temporario -Destination $destino
        Write-Host "`n5. Reconstruir somente gateway sem apagar volumes" -ForegroundColor Cyan
        docker compose build gateway
        Assert-OK 'docker compose build gateway'
        docker compose up -d --no-deps gateway
        Assert-OK 'docker compose up gateway'
        docker compose ps gateway
        Assert-OK 'docker compose ps gateway'
        Write-Host "`nPublicacao aplicada. Backup anterior: $backup" -ForegroundColor Green
        Write-Host 'Abra https://localhost:8443 e execute TESTAR_GATEWAY.py.'
    } catch {
        $erro = $_
        if ($alterou) {
            Write-Warning 'Falha na publicacao. Tentando restaurar os assets anteriores.'
            if (Test-Path $destino) { Remove-Item -LiteralPath $destino -Recurse -Force }
            if (Test-Path $backup) { Move-Item -LiteralPath $backup -Destination $destino }
            try {
                docker compose build gateway
                docker compose up -d --no-deps gateway
            } catch { Write-Warning "Nao foi possivel reiniciar Gateway: $($_.Exception.Message)" }
        }
        throw $erro
    }
} finally {
    if (Test-Path $temporario) { Remove-Item -LiteralPath $temporario -Recurse -Force }
    Pop-Location
}
