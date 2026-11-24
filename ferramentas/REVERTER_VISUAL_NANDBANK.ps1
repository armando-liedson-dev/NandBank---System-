$ErrorActionPreference = 'Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
try {
 $marker=Join-Path $root '.nandbank-visual-lastbackup.txt'
 if(-not(Test-Path -LiteralPath $marker)){throw 'Ainda nao foi criado nenhum backup visual.'}
 $backup=(Get-Content -LiteralPath $marker -Raw).Trim()
 if(-not(Test-Path -LiteralPath $backup)){throw "Copia de seguranca nao encontrada: $backup"}
 $dest=Join-Path $root 'frontend\static'
 $all=@('index.html','app.js','theme.css','premium.css','lion-mark.png','nandbank-hero.webp','region-africa.webp')
 foreach($f in $all){
   $original=Join-Path $backup $f
   $target=Join-Path $dest $f
   if(Test-Path -LiteralPath $original){Copy-Item -LiteralPath $original -Destination $target -Force}
   elseif($f -in @('premium.css','nandbank-hero.webp','region-africa.webp')){Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue}
 }
 & docker compose build gateway
 if($LASTEXITCODE -ne 0){throw 'Falha no build do Gateway durante reversao.'}
 & docker compose up -d --no-deps --force-recreate gateway
 if($LASTEXITCODE -ne 0){throw 'Falha ao recriar Gateway durante reversao.'}
 Write-Host 'VERSAO VISUAL ANTERIOR RESTAURADA. Reinicia o browser com Ctrl+F5.' -ForegroundColor Green
 exit 0
} catch {Write-Host ('ERRO: '+$_.Exception.Message) -ForegroundColor Red;exit 1}