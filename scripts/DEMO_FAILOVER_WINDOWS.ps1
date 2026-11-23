param(
    [ValidateSet('af','eu','as','na','sa','oc')][string]$Regiao='af',
    [switch]$PausaManual
)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$service="$Regiao-primary"
$standby="$Regiao-standby"
Write-Host "=== Simulacao de falha e failover: $Regiao ===" -ForegroundColor Cyan
Write-Host "Antes de continuar: deixa o gerente regional em Nos continentais e o cliente pronto para transferir."
Write-Host "`n1) Parar temporariamente o processo principal: $service"
docker compose stop $service
if($LASTEXITCODE -ne 0){throw "Nao foi possivel parar $service."}
Write-Host "`n2) Aguardar 8 segundos para o HAProxy e o monitor detectarem a falha." -ForegroundColor Yellow
Start-Sleep -Seconds 8
Write-Host "`n3) Estado dos processos durante a falha:" -ForegroundColor Cyan
docker compose ps $service $standby
Write-Host "`nO gerente deve receber o alerta e o cliente deve ver o aviso."
Write-Host "Tenta confirmar a transferencia agora. Durante 60 segundos sera recusada sem debito."
if($PausaManual){
    Read-Host "`nQuando terminares de observar a falha, pressiona ENTER para recuperar o principal"
} else {
    Write-Host "`nO principal sera reposto automaticamente pelo script em 7 segundos." -ForegroundColor Yellow
    Start-Sleep -Seconds 7
}
Write-Host "`n4) Repor o processo principal: $service" -ForegroundColor Cyan
docker compose start $service
if($LASTEXITCODE -ne 0){throw "Nao foi possivel iniciar $service."}
Start-Sleep -Seconds 6
docker compose ps $service $standby
Write-Host "`nO principal deve voltar a ficar operacional. O periodo de seguranca de 60 segundos continua a contar desde a deteccao da falha."
Write-Host "Depois do periodo terminar, o cliente pode repetir a transferencia."
Write-Host "`nA escolha do servidor secundario e automatica pelo HAProxy; este script apenas controla a falha de teste e a reposicao do principal."
