# NandBank — Relatório técnico de validação

Data de preparação: **22 de Novembro de 2026**.

## Resultado real neste ambiente de preparação

| Verificação | Resultado | Como foi executada |
|---|---|---|
| Ficheiros essenciais, recursos Pages e segurança do pacote | **PASSOU** | `python VALIDAR_NANDBANK.py` — 33/33 |
| Sintaxe Python (backend e certificados) | **PASSOU** | `ast.parse` de todos os módulos |
| Sintaxe JavaScript do frontend Docker | **PASSOU** | `node --check frontend/static/app.js` |
| Sintaxe JavaScript do GitHub Pages | **PASSOU** | `node --check pages/demo.js` |
| Compilação do Java legado (JDK existente) | **PASSOU** | `javac --add-modules jdk.httpserver ... LegacyServer.java` |
| Estrutura YAML do Compose | **PASSOU** | PyYAML: seis regiões, 12 aplicações, 7 DB e auxiliares |
| Contrato FastAPI sem base de dados real | **PASSOU** | `python -m unittest discover -s tests -p 'test_backend_contract.py' -v` — 9/9 |
| Navegação e cenários da demo Pages com DOM falso | **PASSOU** | `node tests/test_pages.cjs` — 8 verificações |
| Renderização do frontend Docker sem API | **PASSOU** | `node tests/test_live_frontend.cjs` — landing, login, cadastro |
| Servidor HTTP estático local para Pages | **PASSOU** | GET de `index.html`, JS, 3 CSS e logo: 6 respostas HTTP 200 |
| Docker Compose `config --quiet` | **NÃO EXECUTADO AQUI** | O motor Docker não está instalado neste ambiente |
| Arranque de todos os serviços no Docker Desktop Windows | **NÃO EXECUTADO AQUI** | Depende do PC do utilizador |
| Teste real 2PC, ACID, câmbio, PDF e idempotência | **NÃO EXECUTADO NESTA VERSÃO** | Automatizado em `TESTAR_TUDO_WINDOWS.bat` / `app.smoke` |
| Emissão/aprovação/congelamento em PostgreSQL real | **NÃO EXECUTADO NESTA VERSÃO** | Automatizado em `app.nandbank_smoke` |
| Gerente a desligar/ligar contentor via agente Windows | **NÃO EXECUTADO NESTA VERSÃO** | Validar manualmente na máquina Windows |
| Acesso de dois telemóveis em rede LAN e certificado HTTPS | **NÃO EXECUTADO NESTA VERSÃO** | Verificar na rede real |
| Publicação efectiva no GitHub Pages | **NÃO EXECUTADO AQUI** | Depende de criar/enviar o repositório e activar GitHub Pages |
| Perfil DFS/NFS no Docker Desktop | **NÃO EXECUTADO AQUI** | Configuração opcional dependente de WSL2 |

## O que **não** significa «PASSOU»

Verificar Python/JS/YAML/Java não demonstra que todos os contentores, certificados e fluxos distribuídos arrancam em conjunto. O fluxo real, a rede Windows, os alarmes e os saldos devem ser observados no PC de demonstração. Nenhuma captura de execução Docker foi fabricada.

## Como concluir a validação no Windows

1. Iniciar o Docker Desktop.
2. Executar `INICIAR_NANDBANK.bat` numa pasta sem segredos versionados.
3. Confirmar `docker compose ps`, a saúde das sete DB e acesso `https://localhost:8443`.
4. Executar `TESTAR_TUDO_WINDOWS.bat` e guardar **o terminal completo**.
5. Entrar no frontend, solicitar um cartão e aprovar como gerente regional.
6. Seleccionar um motivo e solicitar a paragem do nó principal através do painel; verificar o agente Windows, aviso aos clientes, standby e recuperação.
7. Realizar uma transferência entre Maputo e Lisboa e confirmar moedas, comissão e PDF.
8. Executar `DEMO_FAILOVER_WINDOWS.bat` para o teste histórico automatizado, se ainda desejado.
9. Publicar no GitHub, activar Pages, abrir a URL pública num dispositivo fora da rede e verificar que só mostra a demonstração estática.
10. Testar DFS/NFS separadamente antes de afirmar o requisito cumprido.

## Integridade e preservação

As migrações de `virtual_cards` e `node_control_jobs` usam `CREATE TABLE IF NOT EXISTS`. Não exigem apagar os volumes existentes. Os emails `@globalscale.local` originais são mantidos por compatibilidade, enquanto os novos emails NandBank são criados com a mesma palavra-passe de papel. O projecto Docker Compose continua identificado tecnicamente como `globalscale` para não alterar acidentalmente o nome dos volumes de instalações anteriores.
