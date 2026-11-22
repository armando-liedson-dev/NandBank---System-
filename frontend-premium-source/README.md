# NandBank — Frontend Premium Integrável

Frontend académico para o Gateway FastAPI NandBank existente. O projecto não instala nem altera bases de dados, Docker, volumes ou serviços bancários.

## Requisitos

- Node.js 20 ou superior e npm; ou Bun para usar o lockfile incluído.
- Ligação ao Gateway existente para autenticação e dados reais.

## Desenvolvimento

```powershell
npm install
npm run dev
```

Copie `.env.example` para `.env.local` e configure:

| Variável | Valor inicial | Finalidade |
|---|---|---|
| `VITE_API_BASE_URL` | vazio | Vazio usa `/api` na mesma origem; uma origem completa serve para desenvolvimento separado. |
| `VITE_DEMO_MODE` | `false` | Só `true` apresenta exemplos fictícios claramente assinalados. |
| `VITE_LOCAL_ASSETS` | `false` | `true` usa os ficheiros locais preparados para o Gateway em `/static`. |

Não coloque palavras-passe, tokens ou chaves nestes ficheiros. O token de sessão é mantido apenas no `sessionStorage` e é removido ao terminar a sessão ou após uma resposta 401.

## Ecrãs

- Público: `/`, `/entrar`, `/criar-conta`.
- Cliente: `/cliente/visao-geral`, `/cliente/contas`, `/cliente/transferir`, `/cliente/movimentos`, `/cliente/cartoes`, `/cliente/servicos`, `/cliente/sistema`.
- Gestão: `/gerente/visao-geral`, `/gerente/infraestrutura`, `/gerente/operacoes`, `/gerente-global/visao-geral`, `/gerente-global/auditoria`.

## Testes e compilação

```powershell
npm test
npm run build
```

Para gerar ficheiros com a base pública `/static/` usada pelo Gateway Windows, consulte `README_WINDOWS.md`.

## Integração

Consulte `CONTRATO_API.md`, `README_WINDOWS.md` e `LICENCAS_IMAGENS.md`. Os contratos em `CONTRATO_API.md` foram conferidos contra o `REFERENCIA_gateway.py` fornecido; confirme-os com o OpenAPI do Gateway em execução antes de publicar. O modo normal mostra mensagens de ligação e estados vazios até o servidor responder.

## Modo de demonstração

`VITE_DEMO_MODE=true` activa amostras marcadas como fictícias. As acções que alterariam contas, cartões ou nós permanecem desactivadas; a transferência de demonstração apenas apresenta um resultado local, sem chamar o Gateway.