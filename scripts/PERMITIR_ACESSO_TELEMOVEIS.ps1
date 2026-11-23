#requires -Version 5.1
<# Permite apenas no perfil de rede privada e na sub-rede local.
   Execute voluntariamente como Administrador no seu proprio laboratorio. #>
$ErrorActionPreference = 'Stop'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw 'Abra o PowerShell como Administrador para configurar a Firewall.'
}
$connections=@(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address -and $_.InterfaceAlias -notmatch 'WSL|vEthernet|Docker|VirtualBox|Loopback' })
if ($connections.Count -eq 0) { throw 'Nenhuma interface de rede local com gateway activo.' }
$chosen=$null
foreach ($adapter in $connections) {
  $profile=Get-NetConnectionProfile -InterfaceIndex $adapter.InterfaceIndex -ErrorAction SilentlyContinue
  if ($profile -and $profile.NetworkCategory -eq 'Private') { $chosen=$adapter; break }
}
if (-not $chosen) { throw 'A rede actual não está marcada como Privada. Não vou abrir uma porta numa rede Pública.' }
$ip=($chosen.IPv4Address | Select-Object -First 1).IPAddress
$name='NandBank - HTTPS 8443 (apenas rede privada e sub-rede local)'
if (-not (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8443 -Profile Private -RemoteAddress LocalSubnet | Out-Null
}
Write-Host ('Regra limitada à rede privada activa: ' + $ip) -ForegroundColor Green
Write-Host ('Use no telemóvel da mesma LAN: https://' + $ip + ':8443')
Write-Host 'Se o navegador recusar o certificado, confie apenas na CA académica dos dispositivos de teste. Não desactive TLS.'
