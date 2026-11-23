"""Verificador estrutural seguro: nao lê nem imprime credenciais e não executa Docker."""
from pathlib import Path
import ast, subprocess, sys, shutil, re
ROOT = Path(__file__).resolve().parents[1]
checks=[]
def check(label, condition):
    checks.append((label,bool(condition)))
    print(('[OK] ' if condition else '[ERRO] ')+label)

required = [
 'docker-compose.yml','infra/sql/global.sql','infra/sql/regional.sql','backend/app/gateway.py','backend/app/security.py',
 'backend/app/nandbank_smoke.py','backend/app/coordinator.py',
 'frontend/static/index.html','frontend/static/images/nandbank-lion-logo.png',
 'frontend-premium-source/src/components/nandbank/staff-pages.tsx',
 'frontend-premium-source/src/components/nandbank/customer-management.tsx',
 'frontend-premium-source/src/routes/balcao.operacoes.tsx',
 'frontend-premium-source/src/routes/filial.visao-geral.tsx',
 'pages/index.html','pages/demo.js',
 'scripts/AGENTE_NOS_WINDOWS.ps1','scripts/INICIAR_WINDOWS.ps1',
 'scripts/parte2/COMPILAR_E_PUBLICAR.ps1','.github/workflows/tests.yml','README.md']
for rel in required:check('Ficheiro '+rel,(ROOT/rel).is_file())
for path in sorted((ROOT/'backend/app').glob('*.py')):
 try:ast.parse(path.read_text(encoding='utf-8'));passed=True
 except SyntaxError:passed=False
 check('Sintaxe Python '+path.name,passed)
if shutil.which('node'):
 result=subprocess.run(['node','--check',str(ROOT/'pages/demo.js')],capture_output=True,text=True)
 check('JavaScript Pages',result.returncode==0)
try:
 import yaml
 compose=yaml.safe_load((ROOT/'docker-compose.yml').read_text(encoding='utf-8'))
 services=compose['services']
 check('6 continentes com primário/reserva',all(f'{c}-primary' in services and f'{c}-standby' in services for c in ('af','as','eu','na','sa','oc')))
 check('7 bases PostgreSQL',all(f'db-{c}' in services for c in ('global','af','as','eu','na','sa','oc')))
except Exception:check('Docker Compose YAML válido',False)
check('Frontend React com assets estáticos', bool(re.search(r'/static/assets/[^\" ]+\.js',(ROOT/'frontend/static/index.html').read_text(encoding='utf8'))))
check('API com gestao de clientes',"@app.patch('/api/admin/customers/{customer_id}/status')" in (ROOT/'backend/app/gateway.py').read_text(encoding='utf8'))
# Se houver Git, garantir que segredos não estão versionados; .env e .credentials
# devem existir localmente em instalacoes reais, por isso não reprovar por existirem.
if (ROOT/'.git').exists():
 p=subprocess.run(['git','ls-files','--','.env','.credentials'],cwd=ROOT,capture_output=True,text=True)
 check('Credenciais fora do Git',p.returncode==0 and not p.stdout.strip())
print(f'\n{sum(ok for _,ok in checks)}/{len(checks)} verificacoes estruturais aprovadas.')
sys.exit(0 if all(ok for _,ok in checks) else 1)
