> **Nota da revisão 2026-11-22:** o build original TanStack Start não deve ser copiado directamente para `/app/ui`. A distribuição actual inclui `vite.gateway.config.ts`, `src/gateway-main.tsx` e `scripts/build-gateway.mjs`; o comando `npm run build:gateway` cria `dist-gateway/index.html` e `dist-gateway/assets/`. Utilize preferencialmente `INSTALAR_NO_NANDBANK_WINDOWS.bat` incluído na raiz do ZIP de entrega, que cria backup e recria somente o serviço `gateway`. Não apague volumes PostgreSQL.

# Integração no Gateway NandBank para Windows

Este guia prepara os ficheiros estáticos do frontend para a instalação académica FastAPI já existente. Não modifica o PostgreSQL, Docker Compose, certificados, agentes de nós ou volumes.

## 1. Preparar a cópia

1. Faça uma cópia de segurança da pasta de interface actualmente montada em `/app/ui`.
2. Extraia o ZIP para uma pasta nova, fora da pasta do backend.
3. Instale Node.js 20 ou superior.
4. Abra PowerShell na pasta do frontend e execute:

```powershell
npm install
Copy-Item .env.example .env.local
```

Edite `.env.local` sem incluir segredos:

```dotenv
VITE_API_BASE_URL=
VITE_DEMO_MODE=false
VITE_LOCAL_ASSETS=true
```

Deixe `VITE_API_BASE_URL` vazio quando a aplicação e o Gateway forem servidos pela mesma origem. Se executar o Vite separado, configure uma origem HTTPS que o browser consiga alcançar e permita essa origem no CORS do Gateway. Não desactive a validação TLS do browser.

## 2. Criar a versão para o Gateway

```powershell
npm run build:gateway
```

O comando gera referências de ficheiros sob `/static/`, conforme o `app.mount('/static', ...)` presente no Gateway de referência. Os ícones, fotografia e recursos compilados ficam nesse caminho; o fallback de página continua na raiz e as rotas `/api/*` continuam pertencendo ao FastAPI.

Copie o conteúdo da pasta pública produzida pelo build para o directório que o Gateway monta como `/app/ui`. A saída exacta do build é indicada pelo Vite/TanStack Start e pode mudar entre versões; confirme que a pasta copiada contém `index.html`, os ficheiros compilados e `images/` antes de substituir a interface existente. Se o Gateway actual usar uma pasta diferente, ajuste apenas o caminho de publicação, não as rotas bancárias.

## 3. Confirmar a ligação

1. Inicie o ambiente que já utiliza, sem apagar volumes nem executar comandos de limpeza.
2. Abra a origem HTTPS do Gateway no browser e confirme que o certificado é aceite pelo computador.
3. Verifique `/api/health`, depois teste entrada, contas, cotação, transferência, cartões e permissões com contas académicas existentes.
4. Confirme o estado do agente Windows antes de solicitar uma intervenção de nó. A interface nunca chama `/api/agent/jobs` nem envia `CONTROL_AGENT_KEY`.
5. Teste os caminhos de página directa e actualização, por exemplo `/cliente/visao-geral`, e confirme que `/api/*` não é encaminhado para o HTML da aplicação.

## 4. Reverter

Se a interface não abrir, restaure a cópia da antiga pasta `/app/ui`. Não remova imagens Docker, volumes, dados PostgreSQL ou certificados. A compilação deste frontend não exige migrações nem alterações à base de dados.

## Criar o ZIP localmente

O ZIP de entrega contém o código-fonte, ficheiros de configuração, imagens necessárias, lockfiles, testes e documentação. Para gerar uma nova cópia no Windows, sem dependências instaladas nem segredos:

```powershell
$ficheiros = @('src','public','package.json','package-lock.json','bun.lock','vite.config.ts','tsconfig.json','README.md','README_WINDOWS.md','CONTRATO_API.md','LICENCAS_IMAGENS.md','RELATORIO_TESTES.md','.env.example') | Where-Object { Test-Path $_ }
Compress-Archive -Path $ficheiros -DestinationPath ..\NandBank_Frontend_Premium_Integravel.zip -Force
```