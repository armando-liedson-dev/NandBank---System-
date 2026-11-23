param(
    [ValidateSet('Diagnostico','Failover','DFS')][string]$Modo='Diagnostico',
    [ValidateSet('af','eu','as','na','sa','oc')][string]$Regiao='af'
)
$ErrorActionPreference='Stop'
$project=(Get-Location).Path
if(-not (Test-Path (Join-Path $project 'docker-compose.yml'))){throw 'Abra PowerShell na raiz do NandBank (docker-compose.yml nao encontrado).'}
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$out=Join-Path $project ".private-backups\evidencias-fases34-$stamp"
New-Item -ItemType Directory -Force -Path $out | Out-Null
function Invoke-DockerCmd([string[]]$ArgsList){
    $ErrorActionPreference='Continue'
    & docker.exe @ArgsList 2>&1 | ForEach-Object { "$($_)" }
    if($LASTEXITCODE -ne 0){throw "Docker falhou (codigo $LASTEXITCODE): docker $($ArgsList -join ' ')"}
}
function Snapshot([string]$Tag){
    $lines= Invoke-DockerCmd -ArgsList @('compose','ps','-a')
    $lines | Set-Content -Encoding UTF8 (Join-Path $out "$Tag-containers.txt")
    $lines | Out-Host
    foreach($svc in @('gateway','router','legacy',"$Regiao-primary","$Regiao-standby")){
        try { Invoke-DockerCmd -ArgsList @('compose','logs','--no-color','--tail','100',$svc) | Set-Content -Encoding UTF8 (Join-Path $out "$Tag-$svc.log") }
        catch { "Nao foi possivel recolher ${svc} : $_" | Add-Content (Join-Path $out 'avisos.txt') }
    }
}
function Ask([string]$msg){ [void](Read-Host $msg) }
try {
    "Data: $(Get-Date -Format o)`nModo: $Modo`nRegiao: $Regiao" | Set-Content -Encoding UTF8 (Join-Path $out 'contexto.txt')
    Write-Host "Evidencias: $out" -ForegroundColor Cyan
    Snapshot 'antes'
    if($Modo -eq 'Diagnostico'){
        Write-Host 'Diagnostico concluido. Nenhum servico alterado.' -ForegroundColor Green
    } elseif($Modo -eq 'DFS'){
        Write-Host 'DFS: somente diagnostico. Nao altera o compose nem instala modulos.' -ForegroundColor Yellow
        Invoke-DockerCmd -ArgsList @('compose','--profile','dfs','config','--services') | Set-Content -Encoding UTF8 (Join-Path $out 'dfs-servicos.txt')
        foreach($svc in @('nfs-server','nfs-client')){
            try { Invoke-DockerCmd -ArgsList @('compose','--profile','dfs','logs','--no-color','--tail','100',$svc) | Set-Content -Encoding UTF8 (Join-Path $out "dfs-$svc.log") }
            catch { "DFS ${svc} : $_" | Add-Content (Join-Path $out 'avisos.txt') }
        }
        Write-Host 'O NFS nao foi corrigido por este script. Necessita de servidor NFS compativel.' -ForegroundColor Yellow
    } else {
        $primary="$Regiao-primary"; $standby="$Regiao-standby"
        $running=(Invoke-DockerCmd -ArgsList @('compose','ps','--status','running','--services'))
        if($running -notcontains $primary -or $running -notcontains $standby){throw "Ambos os servicos ($primary e $standby) devem estar activos antes do teste."}
        Write-Host "Teste controlado: sera parado APENAS $primary. BD e volumes intocados." -ForegroundColor Yellow
        $confirm=Read-Host "Escreva TESTAR-$Regiao para continuar"
        if($confirm -cne "TESTAR-$Regiao"){throw 'Teste cancelado.'}
        $script:stopped=$true
        Invoke-DockerCmd -ArgsList @('compose','stop',$primary) | Out-Host
        Start-Sleep -Seconds 10
        Snapshot 'durante-falha'
        Write-Host "Agora teste manualmente uma consulta de saldo e uma transferencia ficticia via UI. Registe capturas. Nao encerre este PowerShell." -ForegroundColor Cyan
        Ask 'Prima ENTER depois de concluir os testes para repor o principal'
    }
} finally {
    if($script:stopped){
        Write-Host "A repor $Regiao-primary..." -ForegroundColor Yellow
        try { Invoke-DockerCmd -ArgsList @('compose','start',"$Regiao-primary") | Out-Host; Start-Sleep -Seconds 8; Snapshot 'apos-recuperacao' }
        catch { Write-Host "ATENCAO: reposicao falhou: $_" -ForegroundColor Red }
        $script:stopped=$false
    }
    Write-Host "Relatorio de evidencias: $out" -ForegroundColor Cyan
}
