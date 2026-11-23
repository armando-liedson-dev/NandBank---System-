$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$payload = Join-Path $root 'VISUAL_NOVO\frontend\static'
$dest = Join-Path $root 'frontend\static'
$files = @('index.html','app.js','theme.css','premium.css','lion-mark.png','nandbank-hero.webp','region-africa.webp')
function RunDocker([string]$title, [string[]]$argsDocker) {
    Write-Host "`n=== $title ===" -ForegroundColor Cyan
    & docker @argsDocker
    if ($LASTEXITCODE -ne 0) { throw "$title falhou (exit $LASTEXITCODE)." }
}
try {
    Write-Host 'NANDBANK - ACTUALIZACAO VISUAL COM BACKUP' -ForegroundColor Yellow
    if (-not (Test-Path -LiteralPath (Join-Path $root 'docker-compose.yml'))) {
       throw 'Extrai os ficheiros desta actualizacao dentro da pasta principal NandBank (onde esta docker-compose.yml).'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $root '.env'))) {
       throw 'Nao encontrei .env. Executa a instalacao original do NandBank antes desta actualizacao.'
    }
    if (-not (Test-Path -LiteralPath $dest)) {throw 'Pasta frontend\static nao encontrada.'}
    foreach ($f in $files) {if (-not (Test-Path -LiteralPath (Join-Path $payload $f))) {throw "Ficheiro em falta: $f"}}
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {throw 'Docker Desktop nao instalado.'}
    RunDocker 'Verificar Docker Desktop' @('info','--format','{{.ServerVersion}}')
    RunDocker 'Validar configuracao Compose' @('compose','config','--quiet')
    $backupsDir = Join-Path $root 'backups'
    if (-not (Test-Path -LiteralPath $backupsDir)) {New-Item -ItemType Directory -Path $backupsDir | Out-Null}
    $backupName='visual_'+(Get-Date -Format 'yyyyMMdd_HHmmss')
    $backup = Join-Path $backupsDir $backupName
    New-Item -ItemType Directory -Path $backup | Out-Null
    foreach ($f in $files) {
       $original=Join-Path $dest $f
       if(Test-Path -LiteralPath $original) {Copy-Item -LiteralPath $original -Destination (Join-Path $backup $f) -Force}
    }
    Set-Content -Path (Join-Path $root '.nandbank-visual-lastbackup.txt') -Value $backup -Encoding UTF8
    # Impedir que os backups e o caminho local sejam incluidos num futuro commit Git.
    $gitignore = Join-Path $root '.gitignore'
    if (Test-Path -LiteralPath $gitignore) {
        $ignored = Get-Content -LiteralPath $gitignore -Raw
        if ($ignored -notmatch '(?m)^backups/$') {Add-Content -LiteralPath $gitignore -Value 'backups/' -Encoding UTF8}
        if ($ignored -notmatch '(?m)^\.nandbank-visual-lastbackup\.txt$') {Add-Content -LiteralPath $gitignore -Value '.nandbank-visual-lastbackup.txt' -Encoding UTF8}
    }
    Write-Host "Backup: $backup" -ForegroundColor Yellow
    foreach ($f in $files) {Copy-Item -LiteralPath (Join-Path $payload $f) -Destination (Join-Path $dest $f) -Force}
    $env:COMPOSE_PARALLEL_LIMIT='1'
    RunDocker 'Construir apenas imagem do Gateway e frontend' @('compose','build','gateway')
    RunDocker 'Actualizar apenas contentor Gateway, preservar BD e outros nos' @('compose','up','-d','--no-deps','--force-recreate','gateway')
    RunDocker 'Estado do Gateway' @('compose','ps','gateway')
    Write-Host "`nA verificar o HTTPS interno do Gateway..." -ForegroundColor Cyan
    $ready=$false
    $py='import ssl,urllib.request; print(urllib.request.urlopen("https://127.0.0.1:8443/",context=ssl._create_unverified_context(),timeout=7).status)'
    for ($i=1; $i -le 8; $i++) {
        try {
            & docker compose exec -T gateway python -c $py 2>$null
            if ($LASTEXITCODE -eq 0) {$ready=$true;break}
        } catch { # O Gateway pode ainda estar a arrancar.
        }
        Start-Sleep -Seconds 3
    }
    if ($ready) {Write-Host 'Gateway acessivel por HTTPS dentro do Docker.' -ForegroundColor Green}
    else {Write-Warning 'Gateway ainda nao respondeu ao teste interno. Consultar: docker compose logs --tail=60 gateway'}
    Write-Host "`nACTUALIZACAO VISUAL APLICADA. Abre https://localhost:8443 e usa Ctrl+F5." -ForegroundColor Green
    Write-Host "Se necessario, reverter com: .\REVERTER_VISUAL_NANDBANK.bat" -ForegroundColor Yellow
    exit 0
} catch {
    Write-Host ('ERRO: '+$_.Exception.Message) -ForegroundColor Red
    Write-Host 'Os volumes e as bases de dados nao foram apagados.' -ForegroundColor Yellow
    Write-Host 'Para diagnostico: docker compose logs --tail=60 gateway' -ForegroundColor Yellow
    exit 1
}