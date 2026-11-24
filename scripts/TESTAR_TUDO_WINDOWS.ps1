$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
Write-Host '=== CONTENTORES ===' -ForegroundColor Cyan
docker compose ps
if($LASTEXITCODE -ne 0){exit 1}
Write-Host "`n=== TESTE INTEGRADO REAL DO PROTOTIPO ===" -ForegroundColor Cyan
docker compose exec -T gateway python -m app.smoke
if($LASTEXITCODE -ne 0){Write-Host 'TESTE FALHOU: ver logs do Gateway/Regioes/Legacy.' -ForegroundColor Red;exit 1}
Write-Host "`n=== TESTES NANDBANK / CARTOES E CONTROLO DE ACESSO ===" -ForegroundColor Cyan
docker compose exec -T gateway python -m app.nandbank_smoke
if($LASTEXITCODE -ne 0){Write-Host 'TESTE NANDBANK FALHOU.' -ForegroundColor Red;exit 1}
Write-Host 'TESTES PASSARAM. Guarde capturas do terminal para a defesa.' -ForegroundColor Green
