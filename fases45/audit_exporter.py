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