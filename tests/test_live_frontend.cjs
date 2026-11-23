// Verifica o frontend React utilizado pelo Gateway, nao a antiga pagina app.js.
const fs = require('fs'), path = require('path'), assert = require('assert');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root,'frontend/static/index.html'),'utf8');
assert(html.includes('NandBank') && html.includes('/static/assets/'), 'index React servido pelo Gateway');
assert(/<div id="root"><\/div>/.test(html), 'React root');
const js = html.match(/\/static\/assets\/[^"\s]+\.js/);
const css = html.match(/\/static\/assets\/[^"\s]+\.css/);
assert(js && css, 'CSS e JavaScript compilados');
assert(fs.statSync(path.join(root,'frontend/static',js[0].replace('/static/',''))).size>0, 'JavaScript presente');
assert(fs.statSync(path.join(root,'frontend/static',css[0].replace('/static/',''))).size>0, 'CSS presente');
const src = path.join(root,'frontend-premium-source/src');
const api = fs.readFileSync(path.join(src,'services/api/client.ts'),'utf8');
const staff = fs.readFileSync(path.join(src,'components/nandbank/staff-pages.tsx'),'utf8');
assert(api.includes('"branch_manager"') && api.includes('"teller"'), 'roles encaminhados');
assert(api.includes('/api/teller/deposit') && api.includes('/api/teller/withdraw'), 'operacoes reais de balcao');
assert(staff.includes('TellerOperationsPage') && staff.includes('BranchOverviewPage'), 'areas do pessoal da filial');
assert(fs.existsSync(path.join(src,'routes/filial.clientes.tsx')), 'gestao de clientes por filial');
console.log('PASSOU: React SPA, assets, rotas e operacoes de balcao. Nao substitui os testes Docker.');
