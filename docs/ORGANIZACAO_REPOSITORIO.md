# Organização do repositório — NandBank

Este documento explica a limpeza da branch `Parte2` sem modificar a infraestrutura bancária.

## Estrutura preservada

- `backend/`, `frontend/`, `frontend-premium-source/`: aplicações e interface reais.
- `infra/`, `docker-compose.yml`, `docker-compose.fases45.yml`: configuração e persistência.
- `fases45/`: agentes SeaweedFS e exportação de auditoria.
- `pages/`: demonstração web pública, diferente do frontend real.
- `scripts/`, `ferramentas/`, `tests/`, `.github/`: arranque, validação e automação.
- `docs/`: documentação funcional e técnica.

## Materiais históricos retirados da indexação Git

A limpeza retira **apenas do controlo de versões** (com `git rm --cached`), quando existirem, os seguintes materiais de transição:

- `CORRECAO_NANDBANK/`: cópia temporária de código já integrado.
- `VISUAL_NOVO/`: instantâneo histórico de interface.
- `documentacao/`: documentação preliminar, substituída por `docs/`.
- Scripts de correcção provisórios e respectivos `.bak`.
- Lançadores `.bat` históricos, quando já existe alternativa operacional mantida.

Os ficheiros permanecem no disco local. Os scripts **não eliminam ficheiros ou volumes Docker**.

## Ficheiros cuja localização não deve mudar

- `docker-compose.yml` e `docker-compose.fases45.yml`: mantidos na raiz por razões de caminhos relativos.
- `INSTALAR_E_TESTAR_FASES_4_E_5.ps1`: usa `$PSScriptRoot` como pasta raiz e é mantido aí.
- `fases45/dfs_node.py`, `fases45/audit_exporter.py`: montagens previstas no Compose.
- `scripts/AGENTE_NOS_WINDOWS.ps1` e `scripts/INICIAR_WINDOWS.ps1`: caminhos utilizados pelo Windows.
- `INICIAR_WINDOWS.bat`, `INICIAR_NANDBANK.bat`, `TESTAR_TUDO_WINDOWS.bat`: atalhos oficiais da raiz.
- `pages/`: pasta utilizada pelo workflow de publicação no GitHub Pages.

## Regras de segurança

1. Executar a reorganização apenas com a branch `Parte2` limpa e sincronizada.
2. Não executar `git clean -fdx`, `docker compose down -v` nem comandos de remoção de volumes.
3. Não enviar `.env`, `.credentials`, `fases45/.env`, certificados ou backups.
4. Inspeccionar `git diff --cached --stat` e `git status` antes de `git commit`.
5. Testar o arranque e as operações depois da reorganização; a mudança documental, por si só, não valida a aplicação.
6. Manter as evidências das fases do projecto fora do repositório público.

## Reversão antes do commit

O organizador não cria commits automaticamente. Para cancelar as **alterações preparadas** e restaurar os ficheiros anteriormente indexados sem apagar as cópias locais, guardar primeiro a nova documentação fora do projecto e executar:

```powershell
git restore --staged .
git restore README.md .gitignore
```

Se existirem ficheiros untracked após esta reversão, não usar `git clean`: removê-los manualmente apenas depois de os rever.
