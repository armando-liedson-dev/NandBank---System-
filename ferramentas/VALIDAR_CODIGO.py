"""Validação independente de Docker: integridade dos artefactos e contratos estáticos."""
from pathlib import Path
import ast, subprocess, sys, yaml, tempfile
root = Path(__file__).resolve().parent
services = yaml.safe_load((root/'docker-compose.yml').read_text(encoding='utf8'))['services']
regions = ['af','eu','as','na','sa','oc']
for reg in regions:
    assert 'db-'+reg in services
    assert reg+'-primary' in services
    assert reg+'-standby' in services
    assert services[reg+'-primary']['environment']['DB_HOST']=='db-'+reg
    assert services[reg+'-standby']['environment']['DB_HOST']=='db-'+reg
assert all(n in services for n in ['gateway','legacy','router','db-global','cert-init'])
for src in (root/'backend'/'app').glob('*.py'):
    ast.parse(src.read_text(encoding='utf8'), filename=str(src))
ast.parse((root/'infra'/'certgen.py').read_text(encoding='utf8'))
print('PASSOU: Python AST e seis regioes com bases separadas e standby')
if subprocess.run(['node','--check',str(root/'frontend/static/app.js')],capture_output=True).returncode:
    raise RuntimeError('Frontend JavaScript inválido')
print('PASSOU: JavaScript')
with tempfile.TemporaryDirectory() as d:
    path=root/'infra/legacy/src/main/java/mz/globalscale/LegacyServer.java'
    subprocess.run(['javac','--add-modules','jdk.httpserver','-encoding','UTF-8','-d',d,str(path)],check=True)
print('PASSOU: Java legado')
for path in ['README.md','AGENTS.md','docs/ARQUITETURA.md','docs/TESTES_E_DEFESA.md','infra/sql/global.sql','infra/sql/regional.sql','infra/haproxy.cfg','INICIAR_WINDOWS.bat','TESTAR_TUDO_WINDOWS.bat','DEMO_FAILOVER_WINDOWS.bat']:
    assert (root/path).is_file(),path
print('PASSOU: documentacao, SQL, scripts Windows')
print('NOTA: Docker Compose/transferencias/failover real requerem execucao no Windows.')
