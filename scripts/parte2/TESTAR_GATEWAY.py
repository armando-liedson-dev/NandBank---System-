#!/usr/bin/env python3
"""Smoke tests HTTP de leitura do NandBank (sem movimentar fundos ou modificar dados).
Exemplos:
  py -3 scripts/parte2/TESTAR_GATEWAY.py --insecure-local
  py -3 scripts/parte2/TESTAR_GATEWAY.py --insecure-local --email admin@nandbank.local
  py -3 scripts/parte2/TESTAR_GATEWAY.py --base https://banco.interno:8443 --email cliente@exemplo.com
Use --insecure-local APENAS em https://localhost/127.0.0.1 com CA auto-assinada de laboratório.
"""
from __future__ import annotations
import argparse
import getpass
import json
import re
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


class Probe:
    def __init__(self, base, insecure):
        self.base = base.rstrip('/')
        if insecure:
            host = urlsplit(self.base).hostname
            if host not in ('localhost', '127.0.0.1', '::1'):
                raise ValueError('--insecure-local permitido somente em localhost/127.0.0.1/::1')
            print('AVISO: certificado TLS nao validado apenas neste teste local.')
        self.context = ssl._create_unverified_context() if insecure else ssl.create_default_context()
        self.passed = 0
        self.failed = 0

    def request(self, method, path, token=None, payload=None, accept='application/json'):
        body = json.dumps(payload).encode('utf-8') if payload is not None else None
        headers = {'Accept': accept}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = Request(self.base + path, headers=headers, data=body, method=method)
        try:
            with urlopen(req, timeout=20, context=self.context) as resp:
                data = resp.read(2_000_000)
                return resp.status, resp.headers, data
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read(10000)

    def check(self, label, method, path, expect=200, token=None, payload=None, parse_json=True, accept='application/json'):
        try:
            status, headers, raw = self.request(method, path, token, payload, accept)
            if status not in (expect if isinstance(expect, tuple) else (expect,)):
                raise ValueError(f'HTTP {status}; esperado {expect}')
            data = json.loads(raw) if parse_json else raw.decode('utf-8', errors='replace')
            self.passed += 1
            print('OK  ', label)
            return data
        except (ValueError, OSError, URLError, json.JSONDecodeError) as exc:
            self.failed += 1
            print('FALHA', label, '-', str(exc)[:220])
            return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='https://localhost:8443')
    ap.add_argument('--insecure-local', action='store_true')
    ap.add_argument('--email', help='Email academico; a palavra-passe e pedida sem eco no terminal')
    args = ap.parse_args()
    if urlsplit(args.base).scheme != 'https':
        ap.error('URL deve usar HTTPS.')
    try:
        p = Probe(args.base, args.insecure_local)
    except ValueError as exc:
        ap.error(str(exc))
    health = p.check('Gateway /api/health', 'GET', '/api/health')
    if health and health.get('status') != 'ok':
        p.failed += 1
        print('FALHA status de health diferente de ok')
    config = p.check('Configuracao e filiais reais', 'GET', '/api/config')
    if config and not any(region.get('branches') for region in config.get('regions', [])):
        p.failed += 1
        print('FALHA backend nao devolveu filiais')
    p.check('OpenAPI FastAPI', 'GET', '/openapi.json')
    html = p.check('Landing React SPA', 'GET', '/', parse_json=False, accept='text/html')
    p.check('Rota directa de login', 'GET', '/entrar', parse_json=False, accept='text/html')
    p.check('Rota SPA do cliente', 'GET', '/cliente/visao-geral', parse_json=False, accept='text/html')
    p.check('Favicon estatico', 'GET', '/static/favicon.png', parse_json=False, accept='image/png')
    p.check('API nao devolve HTML em rota desconhecida', 'GET', '/api/rota-inexistente-parte2', expect=404)
    p.check('JWT exigido para /api/me', 'GET', '/api/me', expect=(401, 403))
    if html and '/static/assets/' not in html:
        p.failed += 1
        print('FALHA HTML inicial nao aponta para os assets React de /static/assets/')
    if html:
        for asset in sorted(set(re.findall(r'(?:src|href)=["\'](/static/assets/[^"\']+)["\']', html)))[:6]:
            p.check('Asset ' + asset.rsplit('/', 1)[-1], 'GET', asset, parse_json=False, accept='*/*')
    rates = p.check('Cambio /api/fx/rates', 'GET', '/api/fx/rates')
    if config:
        currencies = config.get('currencies') or []
        if len(currencies) > 0:
            code = currencies[0]
            q = urlencode({'source': code, 'destination': code, 'amount': '10.00'})
            p.check('Cotacao dinamica', 'GET', '/api/fx/quote?' + q)
    if args.email:
        print('\nTESTES AUTENTICADOS — apenas consultas, nenhuma escrita')
        password = getpass.getpass('Palavra-passe academica (nao sera guardada): ')
        result = p.check('Autenticacao JWT', 'POST', '/api/auth/login', payload={'email':args.email,'password':password})
        password = ''
        if result and isinstance(result.get('access_token'), str):
            token = result['access_token']
            me = p.check('Perfil autenticado e contas', 'GET', '/api/me', token=token)
            role = (me or {}).get('user',{}).get('role') or result.get('role')
            p.check('Failover de nos (scope autenticado)', 'GET', '/api/failover/status', token=token)
            if role == 'client':
                p.check('Cliente sem acesso a auditoria global', 'GET', '/api/admin/audit', expect=403, token=token)
                p.check('Lista de transferencias', 'GET', '/api/transfers', token=token)
                p.check('Cartoes do cliente', 'GET', '/api/cards', token=token)
                for account in (me or {}).get('accounts',[])[:1]:
                    account_id = quote(str(account['id']), safe='')
                    p.check('Detalhes da conta', 'GET', '/api/accounts/'+account_id+'/details', token=token)
                    p.check('Movimentos (ledger)', 'GET', '/api/accounts/'+account_id+'/ledger', token=token)
            elif role in ('regional_manager','global_manager','branch_manager','teller'):
                p.check('Estatisticas autorizadas', 'GET', '/api/admin/stats', token=token)
                p.check('Estado dos nos', 'GET', '/api/admin/nodes', token=token)
                p.check('Operacoes regionais', 'GET', '/api/admin/operations', token=token)
                p.check('Contas administrativas', 'GET', '/api/admin/accounts', token=token)
                if role in ('regional_manager','global_manager'):
                    p.check('Pedidos de cartao', 'GET', '/api/admin/cards', token=token)
                    p.check('Intervencoes autorizadas', 'GET', '/api/admin/node-actions', token=token)
                if role == 'global_manager':
                    p.check('Auditoria global', 'GET', '/api/admin/audit', token=token)
        else:
            print('Nao foi possivel continuar os testes autenticados.')
    print(f'\nRESULTADO: {p.passed} OK; {p.failed} falha(s).')
    if p.failed:
        print('As operacoes de escrita, 2PC sob falha e agente Windows devem ser testados manualmente.')
        return 1
    print('Testes HTTP de leitura aprovados. Nao constituem prova de 2PC/failover.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
