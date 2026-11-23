"""Run inside gateway container only. Does not mutate data or print secrets."""
import os
import httpx
from app.security import service_token

print('\n== DIAGNOSTICO mTLS / Europa (sem mostrar credenciais) ==', flush=True)
proxy_vars = ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy')
print('Variaveis de proxy presentes:', [key for key in proxy_vars if os.environ.get(key)], flush=True)
endpoints=[('HAProxy','https://region-eu:9502'),
           ('Europa principal','https://eu-primary:9443'),
           ('Europa standby','https://eu-standby:9443')]
for label, base in endpoints:
    for path in ('/health', '/internal/stats'):
        print(label, path, ': ', end='', flush=True)
        try:
            headers={'Authorization':'Bearer '+service_token()} if path.startswith('/internal') else {}
            with httpx.Client(verify='/certs/ca.crt',cert=('/certs/client.crt','/certs/client.key'),timeout=7,trust_env=False) as client:
                result=client.get(base+path,headers=headers)
            print('HTTP',result.status_code,repr(result.text[:240]),flush=True)
        except Exception as exc:
            print(type(exc).__name__,str(exc)[:260],flush=True)
