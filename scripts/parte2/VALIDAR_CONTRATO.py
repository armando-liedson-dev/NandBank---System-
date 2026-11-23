#!/usr/bin/env python3
"""Valida sem dependências externas as rotas usadas pelo frontend NandBank.
Não executa backend, não acede a DB e não escreve ficheiros.
"""
from __future__ import annotations
import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
GATEWAY = ROOT / 'backend/app/gateway.py'
CLIENT = ROOT / 'frontend-premium-source/src/services/api/client.ts'
BUILD = ROOT / 'frontend-premium-source/scripts/build-gateway.mjs'
CONFIG = ROOT / 'backend/app/config.py'

# Contrato extraído das versões do Gateway e client existentes no projecto.
REQUIRED = {
    ('GET','/api/health'), ('GET','/api/config'),
    ('POST','/api/auth/register'), ('POST','/api/auth/login'), ('GET','/api/me'),
    ('POST','/api/accounts'), ('GET','/api/accounts/lookup/{account_id}'),
    ('GET','/api/accounts/{account_id}'), ('GET','/api/accounts/{account_id}/details'),
    ('GET','/api/accounts/{account_id}/ledger'),
    ('GET','/api/fx/rates'), ('GET','/api/fx/quote'),
    ('POST','/api/transfers'), ('GET','/api/transfers'), ('GET','/api/transfers/{tx_id}'),
    ('GET','/api/transactions/{tx_id}/receipt.pdf'),
    ('GET','/api/cards'), ('POST','/api/cards/request'),
    ('POST','/api/cards/{card_id}/{action}'),
    ('GET','/api/admin/cards'), ('POST','/api/admin/cards/{card_id}/review'),
    ('GET','/api/failover/status'), ('GET','/api/admin/stats'),
    ('GET','/api/admin/nodes'), ('GET','/api/admin/operations'),
    ('GET','/api/admin/accounts'), ('GET','/api/admin/node-actions'),
    ('POST','/api/admin/nodes/{code}/action'), ('GET','/api/admin/audit'),
}


def main() -> int:
    for path in (GATEWAY, CLIENT, BUILD, CONFIG):
        if not path.is_file():
            print(f'ERRO: falta ficheiro {path.relative_to(ROOT)}')
            return 2
    source = GATEWAY.read_text(encoding='utf-8')
    tree = ast.parse(source, filename=str(GATEWAY))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                if not isinstance(decorator.func.value, ast.Name) or decorator.func.value.id != 'app':
                    continue
                method = decorator.func.attr.upper()
                if method in ('GET','POST','PUT','DELETE','PATCH') and decorator.args:
                    arg = decorator.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        found.add((method,arg.value))
    missing = sorted(REQUIRED - found)
    client = CLIENT.read_text(encoding='utf-8')
    build = BUILD.read_text(encoding='utf-8')
    configs = CONFIG.read_text(encoding='utf-8')
    extra_errors = []
    for marker in ('/api/auth/login','/api/auth/register','/api/config','/api/me',
                   '/api/accounts','/api/transfers','/api/fx/quote','/api/cards',
                   '/api/admin/nodes','/api/transactions/'):
        if marker not in client:
            extra_errors.append(f'Frontend sem rota esperada: {marker}')
    if 'VITE_DEMO_MODE: "false"' not in build and "VITE_DEMO_MODE: 'false'" not in build:
        extra_errors.append('Build sem VITE_DEMO_MODE=false')
    if 'VITE_API_BASE_URL: ""' not in build and "VITE_API_BASE_URL: ''" not in build:
        extra_errors.append('Build sem API same-origin')
    if 'def region_config(' not in configs:
        extra_errors.append('Backend sem configuracao de filiais')
    if missing:
        print('ROTAS INEXISTENTES (confirmar versao local do backend):')
        for method, route in missing:
            print(f'  {method} {route}')
    for error in extra_errors:
        print('ERRO:', error)
    if missing or extra_errors:
        return 1
    print(f'OK: {len(REQUIRED)} endpoints esperados existem no Gateway; client e build coerentes.')
    print('Nota: esta verificacao estatica nao substitui testes de integracao com Docker.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
