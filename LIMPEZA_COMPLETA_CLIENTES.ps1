# NandBank: reinicializacao dos dados de clientes de teste.
# Executar na pasta que contem docker-compose.yml. Preserva usuarios operacionais e FX.
$ErrorActionPreference = 'Stop'
$servicosDB = @('db-global','db-af','db-eu','db-as','db-na','db-sa','db-oc')
$servicosApp = @('gateway','af-primary','af-standby','eu-primary','eu-standby','as-primary','as-standby','na-primary','na-standby','sa-primary','sa-standby','oc-primary','oc-standby')
if (!(Test-Path './docker-compose.yml')) { throw 'Execute na pasta principal do NandBank.' }
if ((Read-Host 'Isto apaga TODOS os clientes, contas, saldos, movimentos, transferencias, cartoes, auditoria e historico de jobs. Escreva LIMPAR-NANDBANK') -cne 'LIMPAR-NANDBANK') { Write-Host 'Cancelado.'; exit }
$backup = Join-Path (Get-Location).Path ('.private-backups/limpeza-clientes-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $backup | Out-Null
$parados = $false
try {
  Write-Host 'A parar Gateway e nos regionais para impedir novas operacoes...'
  & docker compose stop @servicosApp
  if ($LASTEXITCODE -ne 0) { throw 'Falha ao parar aplicacoes.' }
  $parados = $true
  foreach ($svc in $servicosDB) {
    $container = (& docker compose ps -q $svc).Trim()
    if (!$container) { throw "Contentor nao encontrado: $svc" }
    $pendentes = & docker exec $container psql -U globalscale -d globalscale -At -c 'SELECT count(*) FROM pg_prepared_xacts;'
    if ($LASTEXITCODE -ne 0) { throw "Falha ao verificar transaccoes preparadas em $svc" }
    if (($pendentes | Select-Object -Last 1).Trim() -ne '0') { throw "Existem transaccoes preparadas em $svc. Limpeza bloqueada." }
  }
  Write-Host 'A criar backups PostgreSQL de todas as 7 bases...'
  foreach ($svc in $servicosDB) {
    $container = (& docker compose ps -q $svc).Trim()
    & docker exec $container pg_dump -U globalscale -d globalscale -Fc -f '/tmp/nandbank-pre-limpeza.dump'
    if ($LASTEXITCODE -ne 0) { throw "Falha no pg_dump: $svc" }
    & docker cp "${container}:/tmp/nandbank-pre-limpeza.dump" (Join-Path $backup "$svc.dump")
    if ($LASTEXITCODE -ne 0) { throw "Falha ao copiar backup: $svc" }
    & docker exec $container rm -f '/tmp/nandbank-pre-limpeza.dump'
  }
  Write-Host 'Backups guardados em:' $backup
  foreach ($svc in $servicosDB | Where-Object { $_ -ne 'db-global' }) {
    $container = (& docker compose ps -q $svc).Trim()
    & docker exec $container psql -v ON_ERROR_STOP=1 -U globalscale -d globalscale -c 'BEGIN; TRUNCATE TABLE ledger, accounts RESTART IDENTITY; COMMIT;'
    if ($LASTEXITCODE -ne 0) { throw "Limpeza regional falhou em $svc. Use backups antes de retomar testes." }
    Write-Host "Dados regionais limpos: $svc"
  }
  $global = (& docker compose ps -q db-global).Trim()
  $sql = "BEGIN; TRUNCATE TABLE virtual_cards, transfers, operation_registry, account_registry, audit_events, node_control_jobs RESTART IDENTITY; DELETE FROM users WHERE role = 'client'; COMMIT;"
  & docker exec $global psql -v ON_ERROR_STOP=1 -U globalscale -d globalscale -c $sql
  if ($LASTEXITCODE -ne 0) { throw 'Limpeza global falhou. Use backups antes de retomar testes.' }
  Write-Host 'Limpeza completa terminada. Utilizadores administrativos e operacionais preservados.' -ForegroundColor Green
} finally {
  if ($parados) {
    Write-Host 'A reiniciar servicos de aplicacao...'
    & docker compose up -d --no-build @servicosApp
  }
  Write-Host "BACKUPS: $backup"
}
