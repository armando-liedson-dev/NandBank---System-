# Instruções para Codex / equipa de desenvolvimento

Este ficheiro organiza o projecto para uso no Codex quando o utilizador o abrir com essa ferramenta. Não diz que o Codex já executou o código.

## Contrato

- O enunciado é `Exame Normal - Pratica_032049.docx` (exame SDP, quatro partes). Implementar um banco **fictício**, sem acesso a instituições reais.
- Windows + Docker Compose, seis regiões, uma BD por região, 2 aplicações por região, Gateway, HAProxy, Java legado.
- Nunca remover volumes existentes, redefinir saldos ou apagar transacções para "corrigir" um problema.
- Alterações de SQL após o primeiro uso requerem script de migração incremental; ficheiros de `docker-entrypoint-initdb.d` só correm com volume vazio.
- O 2PC guarda `DECISION_COMMIT` duravelmente antes de enviar `COMMIT PREPARED`; depois de COMMIT decidido, jamais fazer ROLLBACK.
- Toda repetição de pedido de escrita deve levar a mesma `idempotency_key`; não aceitar duplicação silenciosa.
- Nenhum cliente pode efectuar depósitos arbitrários; apenas os perfis com acesso ao balcão.
- Dinheiro em inteiros de unidades mínimas e `Decimal`, não `float`. Se alterar moedas, verificar factor de unidades mínimas.
- Jamais afirmar disponibilidade perante falha física do PC único ou falha regional de PostgreSQL sem novas réplicas/eleição.
- HTTPS/mTLS em serviços, TLS PostgreSQL, JWT RS256 e HMAC na integração Java.
- Não usar npm nem Maven na imagem principal; interface está em `frontend/static` e Java compila directamente com JDK.
- Credenciais em `.env` e `.credentials`, ambos ignorados pelo Git.

## Testes obrigatórios antes de qualquer entrega

1. `python -m compileall backend/app infra/certgen.py`
2. `node tests/test_live_frontend.cjs`
3. `javac --add-modules jdk.httpserver -d <tmp> infra/legacy/src/main/java/mz/globalscale/LegacyServer.java`
4. `docker compose config --quiet`
5. `docker compose up -d --no-build` após as imagens.
6. `docker compose exec -T gateway python -m app.smoke`
7. `powershell -ExecutionPolicy Bypass -File scripts/DEMO_FAILOVER_WINDOWS.ps1 -Regiao as`
8. `powershell -ExecutionPolicy Bypass -File scripts/VERIFICAR_DFS_WINDOWS.ps1` para requisito NFS, verificando limitações WSL2.

## Questões a não falsear

- "2PC" não é consenso entre nós; é um protocolo de commit distribuído com possível bloqueio quando o coordenador cai.
- "standby" da aplicação não equivale a base de dados replicada.
- Polling de 3,5 segundos não equivale a push WebSocket; chamar actualização quase em tempo real.
- Cotações iniciais são fictícias; não inventar valores oficiais.
- Nenhum benchmark do Laboratório 6 deve ser apresentado como realizado neste novo projecto sem executar medições reais.


## Actualização NandBank (2026-11-22)
- Frontend real: `frontend/static/`; GitHub Pages apenas demo `pages/`.
- Cartões académicos exigem aprovação; não gerar PAN/CVV reais.
- Nó principal controlado por agente Windows restrito, sem `docker.sock` no Gateway.
- Migrações incrementais e preservação de volumes obrigatórias.
- Executar `ferramentas/VALIDAR_NANDBANK.py`, `node tests/test_pages.cjs`, testes unitários de contrato e os testes Docker reais na máquina Windows.
- Não afirmar testes integrados validados sem logs reais.
