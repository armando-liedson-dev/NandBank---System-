# NandBank — Análise de Resultados.docx e correcções consolidadas

ISUTC · Sistemas Distribuídos e Paralelos · 23 de Novembro de 2026

Este pacote baseia-se no documento de ensaios e no código `NandBank.zip`. **Não inclui** `.env`, `.credentials`, chaves, volumes ou o relatório original, que continha dados sensíveis. Os testes nesta preparação são estruturais e unitários. Os testes de integração Docker, telemóveis e failover precisam de execução no Windows.

## Diagnóstico e intervenção

| Etapa relatada | Evidência | Intervenção |
|---|---|---|
| 1, preparação | `Parte2`, Compose válido e Docker Desktop activo | Manter o fluxo de arranque e os volumes |
| 2, arranque | Principal/reserva de 6 regiões e 7 PostgreSQL | Manter e reforçar a verificação da infraestrutura |
| 3, testes | 2PC/ACID/idempotência aprovados; teste de cartões parou ao pedir `/lion-mark.png` (HTML em vez de imagem) | Smoke test revisto para os assets React actuais `/static/images/nandbank-lion-logo.png` e JS/CSS `/static/assets` |
| 4, telemóvel | Utilizado `172.26.144.1` (adaptador WSL) e URL antigo `192.168.100.2` | Iniciador escolhe IP com gateway físico e actualiza indicação em `.credentials`; firewall opcional estrita em `PERMITIR_ACESSO_TELEMOVEIS.ps1` |
| 5, JWT/credenciais | Pedido anónimo HTTP 401 correcto, mas relatório apresentava palavras-passe em texto claro | README explica segredos locais, a primeira geração, e proíbe publicação; não divulgar passwords em capturas |
| 6, clientes e CRUD | Gerentes pedem registos completos, actividades, edição e justificação para desactivar | Novos endpoints protegidos com gestão de estados, edição, auditoria e bloqueio de sessões/novas operações; apagamento físico substituído por expiração lógica |
| 7, balcão | Conversão FX devolve cotações; teller/branch_manager reconhecidos mas sem interfaces | Novas rotas e painéis de filial e balcão; formulários de depósito e levantamento usam endpoints existentes e idempotência |
| CI e repositório | Testes referiam scripts/ficheiros de frontend antigo; SQL ignorado por `.gitignore` | Actualizados testes/CI/validador e adicionadas excepções para os dois ficheiros SQL de esquema |

## Permissões resultantes

- `global_manager`: lista todos os clientes e gere qualquer um. Consulta auditoria global.
- `regional_manager`: lista somente clientes com contas na sua região. Só altera um cliente se **todas** as contas deste pertencerem à sua região.
- `branch_manager`: lista clientes e operações da sua filial. Só altera um cliente se todas as suas contas pertencerem à filial.
- `teller`: consulta contas da sua filial e pode efectuar depósito ou levantamento autorizado, sem gerir estados de clientes nem nós.
- `client`: continua com contas, transferências e cartões próprios; sessões de clientes suspensos, suspeitos ou expirados recebem HTTP 403.

O histórico financeiro **não é eliminado** em nenhuma alteração de estado. A mudança tem uma justificação mínima e registo de auditoria. A reactivação exige nova justificação. As operações 2PC já iniciadas permanecem sujeitas ao protocolo e à decisão durável.

## Testes executados nesta preparação

- Sintaxe Python `compileall` — passou.
- Contrato da API (33 endpoints) — passou.
- 13 testes de contrato FastAPI sem DB — passaram.
- 5 testes críticos React — passaram.
- `tsc --noEmit` — passou.
- 34 verificações estruturais — passaram.
- Tests estáticos GitHub Pages e React SPA — passaram.
- **Compilação React**: não executada neste Linux porque as dependências `node_modules` do ZIP são Windows-only. O instalador corre `npm ci` para descarregar as dependências apropriadas do Windows e recompila o Gateway.
- **Docker e transacções reais desta revisão**: não executados neste ambiente. Executar `TESTAR_TUDO_WINDOWS.bat` e verificar o agente/telemóvel depois de aplicar a correcção.

## Instalação sem perda de dados

1. Conserva o projecto original NandBank, `.env`, `.credentials` e os volumes existentes.
2. Extrai `NandBank_FINAL_Corrigido.zip` dentro da pasta original `NandBank` para formar `NandBank_FINAL`.
3. Executa `powershell -NoProfile -ExecutionPolicy Bypass -File .\NandBank_FINAL\APLICAR_NO_PROJECTO_EXISTENTE.ps1` na pasta original.
4. Espera até o instalador terminar e acede a `https://localhost:8443`.
5. Testa login de `filial.maputo@nandbank.local` e `balcao.maputo@nandbank.local`, depósitos/levantamentos, clientes e cartões.
6. Executa `TESTAR_TUDO_WINDOWS.bat` para validar integração e gestões lógicas. Em seguida, repete `DEMO_FAILOVER_WINDOWS.bat` com captura de evidência.
7. Se precisares de telemóvel: usa o IP LAN físico do PC. Corre opcionalmente `PERMITIR_ACESSO_TELEMOVEIS.ps1` como Administrador **apenas na rede privada**.
8. Só depois dos testes, usa Git para criar um commit e actualizar a branch `Parte2`; **inclui `infra/sql/global.sql` e `infra/sql/regional.sql`**.

Não executes `docker compose down -v`, `docker volume rm`, `TRUNCATE`, `DROP TABLE` ou `docker system prune --volumes`.

## Limitações honestas

- O failover de aplicação não é failover de PostgreSQL. Não foi acrescentado outro banco regional nem criado consenso entre máquinas.
- O NFS/DFS não foi transformado em armazenamento obrigatório dos logs de auditoria; continua a necessitar de demonstração/implementação específica.
- O acesso móvel depende do mesmo segmento de rede, da Firewall local e da confiança na CA académica. Não pode ser validado de dentro deste ZIP.
- As palavras-passe reveladas no documento original devem ser substituídas com um procedimento que actualize **também os hashes guardados em PostgreSQL**; mudar apenas `.env` não é suficiente.
- O fluxo de 2PC com nós desligados deve ser validado no Windows com capturas. Não afirmar que transferências entre duas bases indisponíveis são automaticamente confirmadas.
