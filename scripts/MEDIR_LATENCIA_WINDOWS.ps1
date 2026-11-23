$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
Write-Host 'Benchmark do GlobalScale: 10.000 consultas REST/HTTPS sequenciais.' -ForegroundColor Cyan
Write-Host 'Estes resultados NAO sao comparaveis directamente ao CORBA do Laboratorio 6.' -ForegroundColor Yellow
docker compose exec -T gateway python -m app.benchmark
if($LASTEXITCODE -ne 0){exit 1}
