$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$agente = Join-Path $PSScriptRoot 'AGENTE_NOS_WINDOWS.ps1'
$log = Join-Path $root 'agente-arranque-automatico.log'
Set-Location -LiteralPath $root
function Registar([string]$texto) {
    try { Add-Content -LiteralPath $log -Encoding UTF8 -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $texto" } catch {}
}
# Se o Docker ainda nao iniciou, aguardar sem alterar quaisquer contentores.
while ($true) {
    try {
        $null = & docker.exe info '--format' '{{.ServerVersion}}' 2>$null
        if ($LASTEXITCODE -eq 0) { break }
    } catch {}
    Start-Sleep -Seconds 15
}
Registar 'Docker disponivel; a recuperar servicos normais do NandBank sem build nem volumes removidos.'
while ($true) {
    try {
        $null = & docker.exe compose up -d --no-build 2>&1
        if ($LASTEXITCODE -eq 0) { break }
        Registar "Compose up falhou (exit=$LASTEXITCODE); nova tentativa em 20 segundos."
    } catch { Registar "Compose indisponivel: $($_.Exception.Message)" }
    Start-Sleep -Seconds 20
}
Registar 'Servicos do projecto iniciados; iniciando agente original.' 
while ($true) {
    try {
        # O agente existente faz polling do Gateway e executa apenas ordens autorizadas.
        & "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $agente
        Registar "Agente terminou (codigo=$LASTEXITCODE). Reinicio em 15 segundos."
    } catch { Registar "Falha ao iniciar agente: $($_.Exception.Message)" }
    Start-Sleep -Seconds 15
}