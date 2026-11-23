# NandBank — Banco Digital Distribuído

**Projecto académico de Sistemas Distribuídos e Paralelos · ISUTC · 2026**

O NandBank demonstra operações financeiras **fictícias** entre seis continentes, com bases PostgreSQL regionais, transferências 2PC, autenticação, controlo de acessos, câmbio e recuperação de falhas de instâncias de aplicação.

> **Importante:** não é um banco verdadeiro. Não processa dinheiro real, não emite cartões Visa/Mastercard e não substitui um serviço financeiro regulado.

## Acesso: o que funciona em cada ambiente

| Ambiente | Acesso | O que é possível |
|---|---|---|
| **GitHub Pages** | Público pela Internet | Landing page, ecrãs de cliente/gerente, demonstração visual de contas, transferências, cartões e falhas **sem API**. Nada é gravado nos bancos de dados reais. |
| **Windows + Docker Desktop** | `https://localhost:8443` no PC; `https://IP-DO-PC:8443` em telemóveis na mesma rede | Login real do protótipo, contas fictícias persistidas, depósito autorizado, levantamento, transferência 2PC, PDF, cartões com aprovação, monitorização e controlo administrativo dos nós. |

O GitHub Pages **não executa Python, PostgreSQL, Docker nem coordenação 2PC**. O docente pode abrir a landing page e explorar a interface de qualquer lugar; para avaliar a execução distribuída deve executar o projecto no Windows e seguir o guia de demonstração. Não exponha a porta 8443 à Internet sem projecto de segurança adequado.

## Funcionalidades implementadas no backend

- **6 continentes:** África (AF), Europa (EU), Ásia (AS), América do Norte (NA), América do Sul (SA), Oceânia (OC).
- **12 instâncias de aplicação:** principal e reserva em cada região, com HAProxy e verificações de saúde.
- **7 bases PostgreSQL:** uma por continente e uma base global para utilizadores, directório, FX e decisões transaccionais.
- **Autenticação JWT RS256:** cliente, gerente de filial, operador de balcão, gerente regional e gerente global.
- **Contas:** abertura com moeda definida pela filial, consulta de saldos, movimentos e detalhes NIB/IBAN/SWIFT **demonstrativos**.
- **Operações:** depósitos/levantamentos por operadores autorizados; transferência ACID local e 2PC entre continentes, com idempotência.
- **Câmbio:** EUR, MZN, USD, CNY, ZAR e GHS; taxas iniciais fictícias, possibilidade de alteração por gerente global.
- **Comprovativos:** PDF apenas para transferência confirmada.
- **Cartões digitais académicos:** cliente solicita, gerente regional/global aprova ou recusa; titular congela e descongela. Apenas últimos quatro dígitos fictícios; não há PAN/CVV real, compras por cartão ou integração com bandeiras.
- **Nós:** gerente regional/global solicita desligar ou ligar o principal. Agente limitado no Windows executa `docker compose stop`/`up` para os seis serviços permitidos, com histórico e motivos. Em paragens programadas, Docker recebe tempo para término de pedidos. Falhas abruptas são cobertas pela recuperação transaccional conforme o estado durável.
- **Interoperação:** serviço legado Java 21 via HTTPS/mTLS e HMAC; API Python/FastAPI; PostgreSQL via TLS.

### Limites de resiliência

Principal e standby de cada região **partilham o mesmo PostgreSQL**. Assim o failover demonstrado é de aplicação, **não de base de dados**. O ambiente corre num único PC; uma falha total do PC ou Docker interrompe todos os nós. O 2PC é durável mas pode ficar temporariamente pendente se o coordenador ou participantes estiverem inacessíveis. Só afirmar um teste aprovado quando o executar e registar o resultado no Windows.

## Estrutura do repositório

```text
NandBank/
├── pages/                  # GitHub Pages: frontend público DEMO (sem API)
├── frontend/static/        # frontend servido pelo Gateway real no Docker
├── backend/app/            # Gateway, JWT, cartões, coordenador 2PC e nós
├── infra/sql/              # PostgreSQL global e regional
├── infra/legacy/           # serviço Java 21
├── infra/haproxy.cfg       # encaminhamento principal/standby
├── scripts/                # instalação, agente Windows, testes e failover
├── .github/workflows/      # CI e publicação GitHub Pages
├── docs/                   # arquitectura, defesa, segurança e limites
├── docker-compose.yml
├── INICIAR_WINDOWS.bat
├── INICIAR_NANDBANK.bat
├── TESTAR_TUDO_WINDOWS.bat
├── VALIDAR_NANDBANK.py
└── README.md
```

## Como executar no Windows

**Pré-requisitos:** Windows 10/11, Docker Desktop com Linux/WSL2, memória disponível e ligação para descarregar imagens na primeira execução. Os contentores podem consumir bastante RAM; recomenda-se 12–16 GB de memória total. Os telemóveis têm de estar na mesma rede do PC para a demonstração real.

1. Descarregar o repositório ou extrair o ZIP para uma pasta curta, por exemplo `C:\NandBank`.
2. Abrir Docker Desktop e aguardar até aparecer **Running**.
3. Executar **`INICIAR_WINDOWS.bat`** pela primeira vez (o script cria `.env` e `.credentials`, constrói as imagens, prepara certificados e inicia 6 nós + serviços auxiliares).
4. No Windows, abrir **https://localhost:8443**. No telemóvel, usar o IP real do PC, por exemplo **https://172.20.10.2:8443**, se esse for o endereço IPv4 actual.
5. O agente Windows deve iniciar com o sistema e aparecer ligado no painel **Nós continentais**. Para diagnosticar o agente, executar o script `scripts\AGENTE_NOS_WINDOWS.ps1` numa janela PowerShell do servidor.
6. Consultar credenciais com `Get-Content .credentials`. **Não as publicar nem enviar para o GitHub.**

Na primeira abertura em telemóveis, o certificado auto-assinado pode não ser reconhecido. É preciso confiar na CA de laboratório **apenas em dispositivos de teste autorizados**. O acesso pode exigir permissão da Firewall Windows na porta `8443`, apenas numa rede privada de confiança. Não remover TLS/mTLS para contornar o aviso.

Para alterações de código no Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\INICIAR_WINDOWS.ps1 -Rebuild
```

**Nunca** usar `docker compose down -v` se quiser preservar os dados de demonstração. `docker compose stop` pára sem eliminar volumes.

### Perfis de demonstração

| Papel | Email inicial | Âmbito |
|---|---|---|
| Gerente global | `admin@nandbank.local` | Todas as regiões e câmbio |
| Gerente África | `regional.af@nandbank.local` | África |
| Gerente Europa | `regional.eu@nandbank.local` | Europa |
| Gerente Ásia | `regional.as@nandbank.local` | Ásia |
| Gerente América do Norte | `regional.na@nandbank.local` | América do Norte |
| Gerente América do Sul | `regional.sa@nandbank.local` | América do Sul |
| Gerente Oceânia | `regional.oc@nandbank.local` | Oceânia |
| Gerente filial Maputo | `filial.maputo@nandbank.local` | Filial Maputo |
| Operador Maputo | `balcao.maputo@nandbank.local` | Balcão Maputo |
| Cliente | Registo pela interface | Apenas as suas contas |

As palavras-passe são geradas localmente durante a primeira instalação; o email e a palavra-passe correspondente aparecem em `.credentials`. Para compatibilidade com volumes antigos, os emails `@globalscale.local` anteriores continuam válidos enquanto os dados preexistentes forem conservados.

## Guia rápido: Maputo → Lisboa e failover

1. No PC, entrar como gerente África e depositar um montante fictício numa conta cliente de Maputo.
2. No telemóvel 1, entrar como cliente de Maputo; no telemóvel 2, entrar como cliente com conta na filial Lisboa.
3. Copiar o identificador da conta de Lisboa. No cliente Maputo, consultar câmbio e enviar uma transferência. O valor debitado é em **MZN**; o recebido é em **EUR**.
4. Gerente regional abre **Nós continentais** e solicita **Desligar nó principal** para África, escolhendo motivo. O agente Windows fará a alteração autorizada; o painel e clientes recebem o estado de falha, e a standby assume.
5. Durante o intervalo de recuperação, novos pedidos afectados podem devolver `503` com indicação para aguardar. Confirmar o estado de qualquer operação iniciada antes de reenviar. Depois do failover, tentar nova transferência com nova chave **apenas se não existiu operação pendente anterior**.
6. Gerente selecciona **Ligar nó principal**. O serviço só deve ser apresentado como operativo após health-check; operações no standby não devem ser interrompidas voluntariamente.

Se o agente estiver desligado, o backend recusa comandos pela interface; para um teste manual seguro, utilizar `docker compose stop af-primary` e `docker compose up -d --no-build af-primary` num PowerShell do servidor.

## Testes

**Sem Docker (sintaxe/estrutura):**

```powershell
python VALIDAR_NANDBANK.py
```

**Com Docker (transacções reais do protótipo e autorizações):**

```powershell
.\TESTAR_TUDO_WINDOWS.bat
```

Este script executa `app.smoke` (2PC, idempotência, ACID local, saldos e PDF) e `app.nandbank_smoke` (pedidos e aprovação de cartões, congelamento, autorização regional, acesso aos assets e protecção de nós). Os testes geram apenas contas fictícias.

**Failover automatizado original:**

```powershell
.\DEMO_FAILOVER_WINDOWS.bat
```

**Logs:**

```powershell
docker compose ps
docker compose logs --tail=70 gateway router af-primary af-standby db-af
```

**Nota sobre verificação:** o projecto pode passar verificações estáticas sem ter sido executado end-to-end neste ambiente. A execução real dos contentores e o comportamento da Firewall, certificados, telemóveis e host-agent têm de ser validados no Windows. Consultar `docs/RELATORIO_VALIDACAO.md`.

## Publicar no GitHub + GitHub Pages

1. Criar um **repositório público** para o NandBank.
2. Abrir a pasta `NandBank` no VS Code e fazer `git init`, `git add .`, `git commit -m "feat: estrutura inicial NandBank"`.
3. Associar o remoto do **teu próprio repositório** e fazer push para `main`.
4. No GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
5. Abrir **Actions** e verificar os workflows `NandBank — Verificações do código` e `NandBank — Publicar GitHub Pages`.
6. O GitHub apresentará o URL publicado do projecto. Nele funciona apenas `pages/`, um frontend ilustrativo. A ligação a dados do Docker não é pública.

Workflow `pages.yml` publica só a pasta `pages/` usando acções oficiais do GitHub. O workflow `tests.yml` compila Java, verifica estrutura e JavaScript e valida o Compose com segredos fictícios de CI. Não guarda qualquer `.env` real.

### Segurança ao publicar

Não enviar `.env`, `.credentials`, chaves JWT, certificados privados, backups, ficheiros de dados, capturas com passwords, credenciais pessoais ou um export PostgreSQL. A pasta `pages/` não contém JWT nem endpoints reais. A configuração de CORS não foi alargada para aceitar pedidos de origens públicas, propositadamente.

## Aspectos académicos a defender

- Diferença entre fragmentação geográfica de dados e replicação de BD.
- Transacções locais ACID e internacionais 2PC, bloqueios, commit durável, idempotência e recuperação.
- Disponibilidade de aplicação com HAProxy e standby; limitações na falha física e da BD.
- Interoperação de serviços (Python ↔ Java), TLS/mTLS, JWT, HMAC.
- OMA/CORBA como comparação conceptual com REST/HTTP e serviços independentes.
- Avaliação real no Docker versus demonstração visual no GitHub Pages.

## Fotografia, marca e direitos

A identidade foi inspirada nas referências de layout fornecidas para o projecto. A fotografia da landing page é carregada remotamente de uma imagem publicada sob a [licença Unsplash](https://unsplash.com/license): [fotografia utilizada](https://unsplash.com/photos/young-woman-smiling-while-holding-phone-and-credit-card-BKq_7oEvFN4). A imagem não significa que a pessoa retratada seja cliente ou endosse o banco. A marca de leão com coroa foi adaptada visualmente a partir da referência do projecto. **A equipa deve verificar direitos de utilização da marca antes de uso comercial**.

---

**NandBank · Projecto universitário · Moçambique, 2026.**
