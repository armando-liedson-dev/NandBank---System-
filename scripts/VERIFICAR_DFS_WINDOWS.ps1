$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
Write-Host 'TESTE NFS opcional: Docker Desktop deve suportar NFS kernel no WSL2.' -ForegroundColor Yellow
Write-Host 'Se a imagem/driver falhar, nao confunda volume Docker com DFS.' -ForegroundColor Yellow
docker compose --profile dfs up -d nfs-server nfs-client
if($LASTEXITCODE -ne 0){Write-Host 'DFS nao iniciou neste Windows/WSL. Consulte docs/DFS.md' -ForegroundColor Red;exit 1}
docker compose --profile dfs logs --tail=40 nfs-server nfs-client

Write-Host '`n=== Testar leitura e escrita NFS entre os contentores ===' -ForegroundColor Cyan
docker compose --profile dfs exec -T nfs-client sh -c 'echo gs-nfs-check >> /mnt/shared/auditoria.txt && cat /mnt/shared/auditoria.txt'
if($LASTEXITCODE -ne 0){Write-Host 'Montagem NFS sem escrita. Requisito nao validado.' -ForegroundColor Red;exit 1}
docker compose --profile dfs exec -T nfs-server sh -c 'test -f /exports/auditoria.txt && grep gs-nfs-check /exports/auditoria.txt'
if($LASTEXITCODE -ne 0){Write-Host 'NFS nao partilhou o ficheiro entre contentores.' -ForegroundColor Red;exit 1}
Write-Host 'NFS: leitura/escrita partilhada confirmada entre os contentores.' -ForegroundColor Green
