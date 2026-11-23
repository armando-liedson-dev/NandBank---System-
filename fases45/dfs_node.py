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