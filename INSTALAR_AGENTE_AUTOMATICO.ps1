# NandBank - configuracao de arranque automatico do Agente Windows
# Executar UMA vez da raiz do projecto. Nao altera Docker, .env ou bases de dados.
param([switch]$Remover)
$ErrorActionPreference = 'Stop'
$raiz = (Get-Location).Path
$agente = Join-Path $raiz 'scripts\AGENTE_NOS_WINDOWS.ps1'
$lancador = Join-Path $raiz 'scripts\ARRANCAR_AGENTE_AUTOMATICO.ps1'
$nomeTarefa = 'NandBank-Agente-Windows'
if ($Remover) {
    Unregister-ScheduledTask -TaskName $nomeTarefa -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host 'Tarefa automatica removida. O agente original nao foi alterado.' -ForegroundColor Yellow
    exit
}
if (-not (Test-Path -LiteralPath $agente)) { throw "Agente nao encontrado: $agente. Executar na raiz do NandBank." }
if (-not (Test-Path -LiteralPath (Join-Path $raiz 'docker-compose.yml'))) { throw 'docker-compose.yml nao encontrado. Executar na raiz do NandBank.' }
if (-not (Test-Path -LiteralPath (Join-Path $raiz '.env'))) { throw '.env nao encontrado. Nenhuma chave sera recriada.' }
$launcherText = @'
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
'@
[System.IO.File]::WriteAllText($lancador, $launcherText, (New-Object System.Text.UTF8Encoding($false)))
$erroParse = $null
$tokensParse = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($lancador,[ref]$tokensParse,[ref]$erroParse)
if ($erroParse.Count -gt 0) { throw "Erro de sintaxe no lancador: $($erroParse[0])" }
$usuario = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$exe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$acao = New-ScheduledTaskAction -Execute $exe -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $lancador + '"') -WorkingDirectory $raiz
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $usuario
$trigger.Delay = 'PT45S'
$config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $usuario -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $nomeTarefa -Action $acao -Trigger $trigger -Settings $config -Principal $principal -Force | Out-Null
Write-Host 'Tarefa automatica criada.' -ForegroundColor Green
Write-Host "Utilizador: $usuario"
Write-Host "Tarefa: $nomeTarefa"
Write-Host "Arranque: ao iniciar sessao no Windows (45 segundos de atraso)"
Write-Host "Lancador: $lancador"
Write-Host "Log: $(Join-Path $raiz 'agente-arranque-automatico.log')"
Write-Host 'O instalador nao alterou nos, volumes, saldos, credenciais ou .env.' -ForegroundColor Green
Write-Host 'Configure tambem Docker Desktop > Settings > General > Start Docker Desktop when you sign in.' -ForegroundColor Yellow
Write-Host 'Pode iniciar a tarefa agora: Start-ScheduledTask -TaskName NandBank-Agente-Windows'
