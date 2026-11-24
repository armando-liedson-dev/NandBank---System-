param(
    [ValidateSet('InstalarETestar','Testar','Estado')]
    [string]$Modo = 'InstalarETestar'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$composeBase = Join-Path $root 'docker-compose.yml'
$composeExtra = Join-Path $root 'docker-compose.fases45.yml'
$dir = Join-Path $root 'fases45'
$backup = Join-Path $root ('.private-backups\fases45-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$evidence = Join-Path $root ('.private-backups\evidencias-fases45-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$baseArgs = @('compose','-f',$composeBase,'-f',$composeExtra)
$regions = @('af','eu','as','na','sa','oc')

function Invoke-DockerExe {
    param([string[]]$Arguments, [switch]$Quiet)
    $old = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $result = @(& docker.exe @Arguments 2>&1 | ForEach-Object { [string]$_ })
        $status = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $old
    }
    $message = ($result -join "`n").Trim()
    if (-not $Quiet -and $message) { Write-Host $message }
    if ($status -ne 0) {
        throw "Docker falhou (exit=$status): $($Arguments -join ' ')`n$message"
    }
    return $message
}

function Run-Compose {
    param([string[]]$Arguments, [switch]$Quiet)
    $all = @($script:baseArgs) + @($Arguments)
    return Invoke-DockerExe -Arguments $all -Quiet:$Quiet
}

function Save-EmbeddedFile {
    param([string]$Path, [string]$Content)
    if (Test-Path -LiteralPath $Path) {
        $short = Split-Path -Leaf $Path
        Copy-Item -LiteralPath $Path -Destination (Join-Path $script:backup $short) -Force
    }
    [System.IO.File]::WriteAllText($Path, $Content, (New-Object System.Text.UTF8Encoding($false)))
}

function Test-One {
    param([string]$Region, [string[]]$Commands)
    $args = @('exec','-T',('dfs-node-' + $Region),'python','/opt/fases45/dfs_node.py') + @($Commands)
    return Run-Compose -Arguments $args
}

function Ensure-Running {
    if (-not (Test-Path -LiteralPath $composeExtra)) { throw 'Extensao nao instalada. Execute -Modo InstalarETestar.' }
    if (-not (Test-Path -LiteralPath (Join-Path $dir '.env'))) { throw 'Chave DFS nao encontrada.' }
    Run-Compose -Arguments @('config','--quiet') -Quiet | Out-Null
}

function Write-Evidence {
    New-Item -ItemType Directory -Path $script:evidence -Force | Out-Null
    try {
        $ps = Run-Compose -Arguments @('ps','-a') -Quiet
        [System.IO.File]::WriteAllText((Join-Path $script:evidence 'containers.txt'),$ps)
    } catch {}
    foreach ($service in @('dfs-master','dfs-volume-af','dfs-volume-eu','dfs-filer','dfs-audit-exporter','dfs-node-af','dfs-node-eu')) {
        try {
            $logs = Run-Compose -Arguments @('logs','--tail','30',$service) -Quiet
            [System.IO.File]::WriteAllText((Join-Path $script:evidence ($service+'.log')),$logs)
        } catch {}
    }
    Write-Host "Evidencias: $script:evidence" -ForegroundColor Cyan
}

try {
    if (-not (Test-Path -LiteralPath $composeBase)) { throw 'Coloque este script na pasta principal do NandBank (docker-compose.yml).' }
    if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) { throw 'Docker Desktop nao encontrado.' }
    if ($Modo -eq 'InstalarETestar') {
        Write-Host "`n=== FASE 4 + 5: INSTALACAO ISOLADA ===" -ForegroundColor Cyan
        New-Item -ItemType Directory -Path $dir,$backup -Force | Out-Null
        # Guardar chave de autenticacao DOS AGENTES em ficheiro separado.
        $secretFile = Join-Path $dir '.env'
        if (-not (Test-Path -LiteralPath $secretFile)) {
            $random = [byte[]]::new(32)
            $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
            try { $generator.GetBytes($random) } finally { $generator.Dispose() }
            $hex = -join ($random | ForEach-Object { $_.ToString('x2') })
            [System.IO.File]::WriteAllText($secretFile,"DFS_AGENT_KEY=$hex`n",(New-Object System.Text.UTF8Encoding($false)))
        }
        $overlayText = @'
# NandBank fases 4 e 5 - extensao isolada, sem modificar os servicos bancarios.
services:
  dfs-master:
    image: chrislusf/seaweedfs:latest
    command: 'master -ip=dfs-master -port=9333 -mdir=/data -defaultReplication=001'
    restart: unless-stopped
    volumes:
      - nb_dfs_master:/data
    networks: [dfsnet]

  dfs-volume-af:
    image: chrislusf/seaweedfs:latest
    command: 'volume -ip=dfs-volume-af -port=8080 -dir=/data -master=dfs-master:9333 -max=10 -dataCenter=dc1 -rack=rack1'
    restart: unless-stopped
    volumes:
      - nb_dfs_volume_af:/data
    networks: [dfsnet]

  dfs-volume-eu:
    image: chrislusf/seaweedfs:latest
    command: 'volume -ip=dfs-volume-eu -port=8080 -dir=/data -master=dfs-master:9333 -max=10 -dataCenter=dc1 -rack=rack1'
    restart: unless-stopped
    volumes:
      - nb_dfs_volume_eu:/data
    networks: [dfsnet]

  dfs-filer:
    image: chrislusf/seaweedfs:latest
    command: 'filer -ip=dfs-filer -port=8888 -master=dfs-master:9333 -defaultStoreDir=/data -defaultReplicaPlacement=001'
    restart: unless-stopped
    volumes:
      - nb_dfs_filer:/data
    networks: [dfsnet]

  dfs-node-af:
    image: python:3.12-alpine
    command: ['python', '-u', '/opt/fases45/dfs_node.py', 'server']
    environment:
      NODE_REGION: af
      DFS_FILER: http://dfs-filer:8888
    env_file: ./fases45/.env
    volumes: ['./fases45/dfs_node.py:/opt/fases45/dfs_node.py:ro']
    restart: unless-stopped
    networks: [dfsnet]

  dfs-node-eu:
    image: python:3.12-alpine
    command: ['python', '-u', '/opt/fases45/dfs_node.py', 'server']
    environment:
      NODE_REGION: eu
      DFS_FILER: http://dfs-filer:8888
    env_file: ./fases45/.env
    volumes: ['./fases45/dfs_node.py:/opt/fases45/dfs_node.py:ro']
    restart: unless-stopped
    networks: [dfsnet]

  dfs-node-as:
    image: python:3.12-alpine
    command: ['python', '-u', '/opt/fases45/dfs_node.py', 'server']
    environment:
      NODE_REGION: as
      DFS_FILER: http://dfs-filer:8888
    env_file: ./fases45/.env
    volumes: ['./fases45/dfs_node.py:/opt/fases45/dfs_node.py:ro']
    restart: unless-stopped
    networks: [dfsnet]

  dfs-node-na:
    image: python:3.12-alpine
    command: ['python', '-u', '/opt/fases45/dfs_node.py', 'server']
    environment:
      NODE_REGION: na
      DFS_FILER: http://dfs-filer:8888
    env_file: ./fases45/.env
    volumes: ['./fases45/dfs_node.py:/opt/fases45/dfs_node.py:ro']
    restart: unless-stopped
    networks: [dfsnet]

  dfs-node-sa:
    image: python:3.12-alpine
    command: ['python', '-u', '/opt/fases45/dfs_node.py', 'server']
    environment:
      NODE_REGION: sa
      DFS_FILER: http://dfs-filer:8888
    env_file: ./fases45/.env
    volumes: ['./fases45/dfs_node.py:/opt/fases45/dfs_node.py:ro']
    restart: unless-stopped
    networks: [dfsnet]

  dfs-node-oc:
    image: python:3.12-alpine
    command: ['python', '-u', '/opt/fases45/dfs_node.py', 'server']
    environment:
      NODE_REGION: oc
      DFS_FILER: http://dfs-filer:8888
    env_file: ./fases45/.env
    volumes: ['./fases45/dfs_node.py:/opt/fases45/dfs_node.py:ro']
    restart: unless-stopped
    networks: [dfsnet]

  dfs-audit-exporter:
    image: globalscale-bank:1.0
    command: ['python', '-u', '/opt/fases45/audit_exporter.py']
    environment:
      PG_PASSWORD: ${PG_PASSWORD:?Falta PG_PASSWORD}
      POSTGRES_USER: globalscale
      POSTGRES_DB: globalscale
      DB_HOST: db-global
      DFS_FILER: http://dfs-filer:8888
    volumes:
      - ./fases45/audit_exporter.py:/opt/fases45/audit_exporter.py:ro
      - certs:/certs:ro
    restart: unless-stopped
    networks: [mesh, dfsnet]

volumes:
  nb_dfs_master: {}
  nb_dfs_volume_af: {}
  nb_dfs_volume_eu: {}
  nb_dfs_filer: {}

networks:
  dfsnet:
    internal: true
'@
        $nodeText = @'
#!/usr/bin/env python3
"""NandBank Fases 4/5: agente regional de troca de ficheiros, sem tocar no banco."""
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

REGION = os.environ.get('NODE_REGION', 'af')
FILER = os.environ.get('DFS_FILER', 'http://dfs-filer:8888').rstrip('/')
KEY = os.environ.get('DFS_AGENT_KEY', '').encode('utf-8')
VALID_REGIONS = {'af', 'eu', 'as', 'na', 'sa', 'oc'}
MAX_BYTES = 1024 * 1024


def valid_name(name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', name) or name in ('.', '..'):
        raise ValueError('Nome de ficheiro invalido')
    return name


def valid_region(value):
    if value not in VALID_REGIONS:
        raise ValueError('Regiao invalida')
    return value


def request(url, method='GET', data=None, headers=None, attempts=3):
    if data is not None and len(data) > MAX_BYTES:
        raise ValueError('Ficheiro excede 1 MiB')
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
            with urllib.request.urlopen(req, timeout=12) as res:
                payload = res.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise ValueError('Resposta demasiado grande')
                return payload
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == attempts - 1:
                raise RuntimeError('%s %s: %s' % (method, url, exc)) from exc
            time.sleep(2)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_path(region, name):
    return '/nandbank/ficheiros/%s/%s' % (valid_region(region), valid_name(name))


def dest_path(region, sender, name):
    return '/nandbank/transferencias/%s/de-%s/%s' % (
        valid_region(region), valid_region(sender), valid_name(name))


def put(path, data):
    request(FILER + path + '?replication=001', 'PUT', data,
            {'Content-Type': 'application/octet-stream'})
    received = request(FILER + path)
    if digest(received) != digest(data):
        raise RuntimeError('Falha de integridade no armazenamento distribuido')
    return digest(received)


def get(path):
    return request(FILER + path)


def signature(sender, name, hexdigest):
    message = ('%s:%s:%s' % (sender, name, hexdigest)).encode('utf-8')
    return hmac.new(KEY, message, hashlib.sha256).hexdigest()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stdout.write('%s %s\n' % (REGION, fmt % args))
        sys.stdout.flush()

    def response(self, status, obj):
        body = json.dumps(obj, sort_keys=True).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/health':
            self.response(200, {'ok': True, 'region': REGION})
        else:
            self.response(404, {'error': 'not found'})

    def do_POST(self):
        try:
            pieces = self.path.strip('/').split('/')
            if len(pieces) != 3 or pieces[0] != 'receive':
                return self.response(404, {'error': 'not found'})
            sender, name = valid_region(pieces[1]), valid_name(pieces[2])
            count = int(self.headers.get('Content-Length', '0'))
            if count < 1 or count > MAX_BYTES:
                return self.response(413, {'error': 'invalid size'})
            body = self.rfile.read(count)
            sha = digest(body)
            claimed = self.headers.get('X-Content-SHA256', '')
            supplied = self.headers.get('X-NandBank-Signature', '')
            if not KEY or not hmac.compare_digest(sha, claimed) or not hmac.compare_digest(supplied, signature(sender, name, sha)):
                return self.response(403, {'error': 'integrity/authentication failure'})
            path = dest_path(REGION, sender, name)
            stored = put(path, body)
            self.response(200, {'ok': True, 'saved_at': path, 'sha256': stored, 'bytes': len(body), 'receiver': REGION})
        except Exception as exc:
            self.response(500, {'error': str(exc)[:180]})


def cli(args):
    if not KEY:
        raise RuntimeError('DFS_AGENT_KEY nao configurada')
    if len(args) < 1:
        raise ValueError('Comando ausente')
    command = args[0]
    if command == 'write' and len(args) == 3:
        name, content = valid_name(args[1]), args[2].encode('utf-8')
        sha = put(source_path(REGION, name), content)
        print('FASE4 WRITE OK node=%s file=%s bytes=%s sha256=%s' % (REGION, name, len(content), sha))
    elif command == 'send' and len(args) == 3:
        dest, name = valid_region(args[1]), valid_name(args[2])
        if dest == REGION:
            raise ValueError('Destino deve ser outro no')
        content = get(source_path(REGION, name))
        sha = digest(content)
        url = 'http://dfs-node-%s:8700/receive/%s/%s' % (dest, REGION, quote(name))
        raw = request(url, 'POST', content, {
            'Content-Type': 'application/octet-stream',
            'X-Content-SHA256': sha,
            'X-NandBank-Signature': signature(REGION, name, sha),
        })
        result = json.loads(raw)
        if not result.get('ok') or result.get('sha256') != sha:
            raise RuntimeError('Transferencia nao confirmada pelo destinatario: %s' % result)
        print('FASE5 SEND OK %s -> %s file=%s sha256=%s' % (REGION, dest, name, sha))
    elif command == 'read-from' and len(args) == 3:
        sender, name = valid_region(args[1]), valid_name(args[2])
        content = get(dest_path(REGION, sender, name))
        print('FASE5 READ OK receiver=%s sender=%s file=%s bytes=%s sha256=%s' %
              (REGION, sender, name, len(content), digest(content)))
        if len(content) < 2000:
            print('CONTEUDO=' + content.decode('utf-8', errors='replace'))
    elif command == 'read-report' and len(args) == 1:
        raw = get('/nandbank/relatorios/estado-global.json')
        obj = json.loads(raw)
        if obj.get('origin') != 'NandBank-db-global':
            raise RuntimeError('Relatorio global nao identificado')
        print('FASE4 AUDITORIA REAL OK node=%s source=%s at=%s' %
              (REGION, obj['origin'], obj.get('captured_at')))
        print(json.dumps(obj, sort_keys=True, ensure_ascii=True))
    elif command == 'health' and len(args) == 1:
        print(request('http://127.0.0.1:8700/health').decode('utf-8'))
    else:
        raise ValueError('Uso: write nome texto | send regiao nome | read-from regiao nome | read-report | health')


if __name__ == '__main__':
    try:
        if len(sys.argv) >= 2 and sys.argv[1] == 'server':
            valid_region(REGION)
            print('DFS node %s ready on :8700' % REGION, flush=True)
            ThreadingHTTPServer(('0.0.0.0', 8700), Handler).serve_forever()
        else:
            cli(sys.argv[1:])
    except Exception as exc:
        print('ERRO DFS: %s' % exc, file=sys.stderr)
        sys.exit(1)
'@
        $exporterText = @'
#!/usr/bin/env python3
"""Exporta por leitura eventos reais do NandBank para o SeaweedFS; nenhum INSERT/UPDATE/DELETE."""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
import psycopg
from psycopg.rows import dict_row

FILER = os.environ.get('DFS_FILER', 'http://dfs-filer:8888').rstrip('/')


def store(path, payload):
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')
    req = urllib.request.Request(FILER + path + '?replication=001', data=body,
                                 method='PUT', headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=12) as response:
        response.read()
    with urllib.request.urlopen(FILER + path, timeout=12) as response:
        if response.read() != body:
            raise RuntimeError('DFS: verificacao do ficheiro falhou: ' + path)


def snapshot(cursor, last_id):
    # Apenas SELECT; nao interage com o protocolo bancario nem com os saldos.
    cursor.execute('SELECT id,actor_id,type,details,created_at FROM audit_events WHERE id > %s ORDER BY id ASC LIMIT 100', (last_id,))
    events = cursor.fetchall()
    for event in events:
        store('/nandbank/auditoria/eventos/%020d.json' % event['id'], event)
        last_id = event['id']
    cursor.execute('SELECT status,count(*) AS quantidade FROM transfers GROUP BY status ORDER BY status')
    transfer_counts = {row['status']: row['quantidade'] for row in cursor.fetchall()}
    cursor.execute('SELECT count(*) AS n FROM audit_events')
    audit_count = cursor.fetchone()['n']
    cursor.execute('SELECT count(*) AS n FROM operation_registry')
    operation_count = cursor.fetchone()['n']
    report = {
        'origin': 'NandBank-db-global',
        'captured_at': datetime.now(timezone.utc).isoformat(),
        'audit_events': audit_count,
        'operations': operation_count,
        'transfers_by_status': transfer_counts,
        'latest_exported_audit_id': last_id,
        'note': 'Relatorio de leitura; transaccoes e saldos mantidos no PostgreSQL',
    }
    store('/nandbank/relatorios/estado-global.json', report)
    print('AUDITORIA DFS OK ultimo_id=%s eventos=%s operacoes=%s transferencias=%s' %
          (last_id, audit_count, operation_count, transfer_counts), flush=True)
    return last_id


def main():
    last_id = 0
    while True:
        try:
            with psycopg.connect(
                host=os.environ.get('DB_HOST', 'db-global'), port=5432,
                dbname=os.environ.get('POSTGRES_DB', 'globalscale'),
                user=os.environ.get('POSTGRES_USER', 'globalscale'),
                password=os.environ['PG_PASSWORD'],
                sslmode='verify-full', sslrootcert='/certs/ca.crt',
                connect_timeout=6, autocommit=True, row_factory=dict_row) as connection:
                with connection.cursor() as cursor:
                    last_id = snapshot(cursor, last_id)
        except Exception as exc:
            print('AUDITORIA DFS RETRY: %s: %s' % (type(exc).__name__, str(exc)[:250]), flush=True)
        time.sleep(20)


if __name__ == '__main__':
    main()
'@
        Save-EmbeddedFile -Path $composeExtra -Content $overlayText
        Save-EmbeddedFile -Path (Join-Path $dir 'dfs_node.py') -Content $nodeText
        Save-EmbeddedFile -Path (Join-Path $dir 'audit_exporter.py') -Content $exporterText
        Ensure-Running
        Write-Host '[1/3] Iniciar SeaweedFS master (sem tocar no NandBank)...' -ForegroundColor Cyan
        Run-Compose -Arguments @('up','-d','--no-deps','dfs-master') | Out-Null
        Write-Host '[2/3] Iniciar 2 servidores de volumes + filer...' -ForegroundColor Cyan
        Run-Compose -Arguments @('up','-d','--no-deps','dfs-volume-af','dfs-volume-eu','dfs-filer') | Out-Null
        Write-Host '[3/3] Iniciar agentes das 6 regioes e exportador de auditoria...' -ForegroundColor Cyan
        Run-Compose -Arguments @('up','-d','--no-deps','dfs-node-af','dfs-node-eu','dfs-node-as','dfs-node-na','dfs-node-sa','dfs-node-oc','dfs-audit-exporter') | Out-Null
        Write-Host 'Servicos adicionais criados com restart: unless-stopped.' -ForegroundColor Green
    }
    Ensure-Running
    if ($Modo -eq 'Estado') {
        Write-Host "`n=== ESTADO DA EXTENSAO DFS ===" -ForegroundColor Cyan
        Run-Compose -Arguments @('ps','-a') | Out-Null
        Write-Evidence
        exit 0
    }
    New-Item -ItemType Directory -Path $evidence -Force | Out-Null
    Write-Host "`n=== TESTES AUTOMATICOS DAS FASES 4 E 5 ===" -ForegroundColor Cyan
    $testId = Get-Date -Format 'yyyyMMddHHmmss'
    $pairs = @(
        @{From='af';To='eu'}, @{From='eu';To='as'}, @{From='as';To='na'},
        @{From='na';To='sa'}, @{From='sa';To='oc'}, @{From='oc';To='af'}
    )
    $results = New-Object System.Collections.Generic.List[string]
    foreach ($pair in $pairs) {
        $from = $pair.From
        $to = $pair.To
        $filename = "prova-$from-$testId.txt"
        $payload = "NandBank Fases 4/5: ficheiro de $from para $to, teste $testId"
        $done = $false
        for ($attempt = 1; $attempt -le 12 -and -not $done; $attempt++) {
            try {
                $write = Test-One -Region $from -Commands @('write',$filename,$payload)
                if ($write -notmatch 'FASE4 WRITE OK') { throw "Escrita nao confirmada: $write" }
                $done = $true
                $results.Add($write)
            } catch {
                if ($attempt -eq 12) { throw }
                if ($attempt -eq 1) { Write-Host 'Aguardar volumes replicados e Filer iniciarem...' -ForegroundColor Yellow }
                Start-Sleep -Seconds 5
            }
        }
        $send = Test-One -Region $from -Commands @('send',$to,$filename)
        $read = Test-One -Region $to -Commands @('read-from',$from,$filename)
        if ($send -notmatch 'FASE5 SEND OK' -or $read -notmatch 'FASE5 READ OK') {
            throw "Falhou transferencia: $from -> $to"
        }
        $sourceSha = [regex]::Match($write, 'sha256=([0-9a-f]{64})').Groups[1].Value
        $targetSha = [regex]::Match($read, 'sha256=([0-9a-f]{64})').Groups[1].Value
        if (-not $sourceSha -or $sourceSha -ne $targetSha) { throw "SHA256 diferente: $from -> $to" }
        $results.Add($send)
        $results.Add($read)
        Write-Host "PASS: $from -> $to | SHA256 verificado" -ForegroundColor Green
    }
    $reportOk = $false
    for ($attempt = 1; $attempt -le 12 -and -not $reportOk; $attempt++) {
        try {
            $report = Test-One -Region 'eu' -Commands @('read-report')
            if ($report -notmatch 'FASE4 AUDITORIA REAL OK') { throw "Relatorio nao confirmado: $report" }
            $reportOk = $true
            $results.Add($report)
            Write-Host 'PASS: relatorio gerado a partir da BD global lido pelo no da Europa' -ForegroundColor Green
        } catch {
            if ($attempt -eq 12) { throw }
            Start-Sleep -Seconds 5
        }
    }
    [System.IO.File]::WriteAllLines((Join-Path $evidence 'TESTES_FASES45_OK.txt'),$results.ToArray())
    Write-Host "`n=== SUCESSO: FASE 4 (DFS) E FASE 5 (TRANSFERENCIA) ===" -ForegroundColor Green
    Write-Host '6 transferencias inter-regionais confirmadas com SHA256.' -ForegroundColor Green
    Write-Host 'Auditoria e relatorio real do PostgreSQL exportados para SeaweedFS.' -ForegroundColor Green
    Write-Host 'Fase 3, agente Windows, Gateway e bases de dados NAO foram alterados.' -ForegroundColor Cyan
} catch {
    Write-Host ("FALHA NA EXTENSAO FASES 4/5: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'NandBank bancario nao foi modificado. Consulte os logs da extensao.' -ForegroundColor Yellow
    $global:LASTEXITCODE = 1
    $script:failed = $true
} finally {
    if (Test-Path -LiteralPath $composeExtra) { Write-Evidence }
}
if ($script:failed) { exit 1 }
