# Parte2 — Integração React + FastAPI + PostgreSQL

Projecto académico NandBank | Windows / PowerShell / Docker Desktop.

## Arquitectura (com o sistema existente)

```text
Browser (HTTPS 8443)
    |  /, /entrar, /cliente/*, /gerente/*
    v
FastAPI gateway (serviço Docker "gateway")
    |  /static/* -> React compilado em frontend/static/
    |  /api/*    -> APIs protegidas por JWT/âmbito
    +--> PostgreSQL global (identidade, directorio, FX, decisões 2PC)
    +--> HAProxy -> region-af, region-eu, region-as, region-na, region-sa, region-oc
    |              cada regiao: primary/standby e PostgreSQL regional
    +--> agente Windows para gestão dos nos (segredo apenas no backend)
```

A integração usa mesma origem (`VITE_API_BASE_URL` vazio). O build `npm run build:gateway` força `VITE_DEMO_MODE=false`, pelo que os ecrãs usam dados da API em vez de apresentar resultados fictícios sem ligação.

## Instalação segura do patch

1. Confirme que a branch é `Parte2` (`git branch --show-current`).
2. Extraia o pacote entregue *fora* da pasta do projecto.
3. Na pasta extraída, execute `powershell -NoProfile -ExecutionPolicy Bypass -File .\APLICAR_PARTE2.ps1 -Projeto "C:\caminho\NandBank"`.
4. Em NandBank, execute `py -3 .\scripts\parte2\VALIDAR_CONTRATO.py`.
5. Compile e publique: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\parte2\COMPILAR_E_PUBLICAR.ps1`.
6. Abra https://localhost:8443. Não contorne erros de certificado no browser; configure a CA de laboratório quando necessário.
7. Teste com `py -3 .\scripts\parte2\TESTAR_GATEWAY.py --insecure-local` (o parâmetro somente para localhost e apenas no teste automatizado).
8. Teste login de perfil autorizado: `py -3 .\scripts\parte2\TESTAR_GATEWAY.py --insecure-local --email admin@nandbank.local`. A password é pedida sem aparecer no ecrã.

Para compilar sem modificar o Docker use `-SoCompilar`. Para dispensar temporariamente testes críticos use `-SemTestes`, mas não considere a validação concluída.

## Mapeamento existente — UI -> Gateway

| Fluxo | Endpoint real | Comportamento esperado |
|---|---|---|
| Filiais/registo | `GET /api/config`, `POST /api/auth/register` | Selecção de códigos aceites pelo servidor; registo sem saldo inicial |
| Entrada e perfil | `POST /api/auth/login`, `GET /api/me` | JWT temporário em sessionStorage; perfil e contas do utilizador |
| Contas | `POST /api/accounts`, `GET /api/accounts/{id}/details` | Moeda definida pelo backend e saldos reais do protótipo |
| Transferências | `GET /api/fx/quote`, `POST /api/transfers`, `GET /api/transfers/{id}` | Cotação do servidor, chave de idempotência, estado 2PC confirmado |
| Movimentos | `GET /api/transfers`, `GET /api/accounts/{id}/ledger` | Só os registos autorizados |
| Comprovativo | `GET /api/transactions/{id}/receipt.pdf` | PDF somente se `COMMITTED` |
| Cartões | `GET /api/cards`, `POST /api/cards/request`, `POST .../freeze`, `POST .../unfreeze` | Pedido, aprovação por gestor, congelamento pelo titular |
| Gestão | `GET /api/admin/stats`, `/api/admin/operations`, `/api/admin/cards` | Dados filtrados pelo papel/âmbito no servidor |
| Infraestrutura | `GET /api/admin/nodes`, `/api/failover/status`, `POST /api/admin/nodes/{code}/action` | Estado real, submissão de pedido 202; agente Windows executa |
| Auditoria | `GET /api/admin/audit` | Apenas gerente global |

### O que este pacote altera

- **Frontend:** adiciona selector de filiais a partir de `/api/config` em *Criar conta* e *Conta adicional*, sem valores inventados ou codificados no navegador.
- **Ferramentas:** verificador estático de contratos, testes de leitura HTTPS e build/publicação com backup.
- **Não altera:** backend existente, `docker-compose.yml`, `infra/`, credenciais, certificados, volumes PostgreSQL ou mecanismo 2PC.

### Funcionalidades do backend ainda sem ecrã próprio

Os papéis `branch_manager` e `teller` e respectivas operações `/api/teller/deposit` e `/api/teller/withdraw` existem no backend fornecido, mas **não têm área própria nesta interface React**. Também não há painel próprio para editar cotações. Não os apresente como integrados visualmente antes de desenvolver e testar as páginas correspondentes. Este pacote integra integralmente os fluxos já representados no frontend (cliente, gestor regional/global).

## Testes de ponta a ponta (manuais, com dados académicos)

- [ ] Landing, login, nova conta, logout, refresh de página e sessão expirada (`401`).
- [ ] `GET /api/config` oferece filiais válidas como `MZ-MPM`, `PT-LIS`, `CN-SHA`, sem hard-code.
- [ ] Cliente vê apenas as suas contas; o seu saldo corresponde ao PostgreSQL regional.
- [ ] Transferência Maputo -> Lisboa: cotação devolvida pelo servidor; estado `COMMITTED` ou estado pendente explícito, nunca sucesso falso.
- [ ] Repetição após timeout usa **mesma chave de idempotência**; diferente pedido usa chave nova. Não repita manualmente sem confirmar estado da transacção.
- [ ] PDF só para transferência `COMMITTED`.
- [ ] Cartão solicitado por cliente, aprovado por gerente, visto apenas pelo titular.
- [ ] Tentativa de cliente entrar em rotas administrativas recebe `403`.
- [ ] Gerente regional vê apenas a sua região e não a auditoria global.
- [ ] No failover, testar principal offline, standby online e transacção real com estados registados; repetir após recuperação sem duplicados.
- [ ] Gestão de nós somente por papel autorizado e com agente Windows online.

**Nota:** o script `TESTAR_GATEWAY.py` faz apenas consultas e login; não testa operações que alteram saldo, aprovação de cartão nem falhas intencionais de nós. Esses fluxos devem ser comprovados separadamente com dados académicos. Não use `docker compose down -v`.

## Git — commits em Parte2

Só depois de verificar os ficheiros e segredos:

```powershell
git status --short
git diff --stat
# Primeiro commit: melhorias de integração (sem backend ainda)
git add -- frontend-premium-source/src/services/api/types.ts frontend-premium-source/src/components/nandbank/auth-pages.tsx frontend-premium-source/src/components/nandbank/client-pages.tsx frontend-premium-source/src/components/nandbank/branch-picker.tsx frontend-premium-source/.gitignore scripts/parte2 docs/PARTE2_INTEGRACAO.md
git commit -m "feat(integration): connect branch selection to FastAPI configuration"
git push -u origin Parte2
```

Para versionar o backend existente depois de **rever** ficheiros e possíveis credenciais, acrescente explicitamente apenas os directórios/fichários aprovados. Não faça `git add .` de forma indiscriminada; verifique também scripts `.ps1`, `.bat`, configs Docker e ficheiros SQL por passwords e tokens reais. Nunca publique `.env`, `.credentials`, backups, certificados `.key`, `.pem` ou dados DB.

## Reverter a interface

O script de publicação coloca a versão anterior em `.private-backups/parte2-static-DATA-HORA` (pasta ignorada pelo Git). Em caso de erro no build/restart, tenta restauro automático. Para reversão manual, desligue apenas o Gateway, copie o backup para `frontend/static`, depois execute `docker compose build gateway` e `docker compose up -d --no-deps gateway`. Não mexa em volumes PostgreSQL.
