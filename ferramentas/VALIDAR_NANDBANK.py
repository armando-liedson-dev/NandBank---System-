"""Verifica integridade, ficheiros e sintaxe do NandBank sem Docker nem credenciais.
Não substitui docker compose config, o smoke real e a validação no Windows.
"""
from pathlib import Path
import ast,subprocess,sys,shutil,json,re
root=Path(__file__).resolve().parent
errors=[];checks=[]
def result(label,passed,detail=''):
 checks.append((label,passed,detail))
 print(('[OK] ' if passed else '[ERRO] ')+label+(' — '+detail if detail else ''))
 if not passed:errors.append(label)
required=['docker-compose.yml','backend/app/gateway.py','backend/app/coordinator.py','backend/app/nandbank_smoke.py','infra/legacy/src/main/java/mz/globalscale/LegacyServer.java','frontend/static/index.html','frontend/static/theme.css','frontend/static/lion-mark.png','frontend/static/app.js','pages/index.html','pages/demo.js','.github/workflows/pages.yml','README.md','scripts/AGENTE_NOS_WINDOWS.ps1']
for file in required:result('Ficheiro: '+file,(root/file).is_file())
for file in list(root.glob('backend/app/*.py'))+list(root.glob('infra/*.py')):
 try:ast.parse(file.read_text(encoding='utf8')); result('Python: '+str(file.relative_to(root)),True)
 except Exception as e:result('Python: '+str(file.relative_to(root)),False,str(e))
if shutil.which('node'):
 for file in ['frontend/static/app.js','pages/demo.js']:
  r=subprocess.run(['node','--check',str(root/file)],capture_output=True,text=True)
  result('JavaScript: '+file,r.returncode==0,r.stderr[-500:])
else:print('[NOTA] Node.js ausente: verificação JavaScript omitida; CI verifica em GitHub Actions.')
try:
 import yaml
 data=yaml.safe_load((root/'docker-compose.yml').read_text())
 result('Compose: seis regiões',all(f'{reg}-primary' in data['services'] and f'{reg}-standby' in data['services'] and f'db-{reg}' in data['services'] for reg in ('af','eu','as','na','sa','oc')))
 result('Compose: sete PostgreSQL',sum(s.startswith('db-') for s in data['services'])==7)
 result('Compose: Gateway / router / legado',all(x in data['services'] for x in ('gateway','router','legacy')))
except ImportError:print('[NOTA] PyYAML ausente: usa docker compose config --quiet no Windows.')
except Exception as e:result('Compose YAML',False,repr(e))
js=(root/'pages/demo.js').read_text()
result('GitHub Pages: demo sem backend',"demonstração totalmente estática" in js and "api/" not in js)
result('Segurança: sem ficheiros secretos na raiz',not any((root/name).exists() for name in ('.env','.credentials')))
result('Frontend: marca NandBank','NandBank' in (root/'frontend/static/index.html').read_text())
result('Frontend: PWA restrita', 'cache' not in (root/'frontend/static/sw.js').read_text().replace('// Apenas PWA shell. Dados financeiros, tokens, APIs e comprovativos NÃO são guardados em cache.',''))
print('\n'+str(len(checks)-len(errors))+' de '+str(len(checks))+' verificações passaram.')
if errors:sys.exit(1)
