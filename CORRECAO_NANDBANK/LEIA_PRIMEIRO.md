# NandBank — correcções integradas (23-11-2026)

## Como instalar

1. Extrair `NandBank_CORRECAO_FINAL.zip` **dentro** da pasta principal NandBank.
   O ZIP cria a pasta `CORRECAO_NANDBANK`.
2. Fechar operações bancárias em curso e manter o Docker Desktop ligado.
3. Executar no PowerShell a partir da pasta NandBank:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\CORRECAO_NANDBANK\INSTALAR_CORRECOES_NANDBANK.ps1
```

4. Aguardar a confirmação de `/internal/stats` para **as seis regiões**. Recarregar o navegador com Ctrl+Shift+R.
5. Consultar uma conta MZ-MPM, realizar depósito pequeno de demonstração e verificar saldo.

## Alterações

* Corrigida autenticação JWT interna nos participantes: bases regionais não têm tabela users.
* Corrigida apresentação de erros `503` e ampliado timeout de consultas e operações.
* Corrigido texto invisível em inputs dos painéis escuros e no login claro.
* Logótipo preto com canal alfa no formulário de entrada/cadastro.
* Adicionada eliminação definitiva de clientes a gerente regional/global, exigindo confirmação por email; só uma conta vazia, sem movimentos, cartões, depósitos ou transferências. Demais casos devem usar Conta expirada.
* Agente Windows passa a confirmar estado real de Docker para não marcar START_PRIMARY como FAILED devido a mensagens informativas.
* A interface esclarece casos em que uma antiga intervenção FAILED aparece apesar do servidor estar UP.

## Segurança / limitações

* **Nunca execute `docker compose down -v` nem remova volumes**. Este pacote não o faz.
* O instalador cria um backup em `.private-backups/correcao-integral-*` e não altera `.env`, `.credentials` ou esquemas SQL.
* Recria 12 processos de aplicação regional e o Gateway, mas não as bases nem seus volumes; evite operações durante essa janela.
* Os registos FAILED antigos continuam no histórico para auditoria, mesmo que actualmente ambos os nós estejam UP.
* Não foi possível executar a compilação Vite no ambiente Linux de preparação porque o `node_modules` fornecido contém componentes nativos apenas para Windows. A verificação TypeScript (`tsc --noEmit`) e 17 testes Python isolados passaram. A compilação Windows e o teste real com Docker serão executados pelo instalador.
* Os testes Python são isolados e não provam o sucesso end-to-end; o instalador faz prova real de acesso interno às seis regiões e aborta se algum acesso falhar.
* Eliminação definitiva distribuída inclui compensação de conta regional vazia se a remoção global falhar. Evitar operações concorrentes durante a eliminação.

## Se a instalação falhar

O instalador interrompe na etapa falhada e mostra o erro. Não apaga dados. Os arquivos originais estão no backup mencionado na consola. Se a falha ocorrer durante a reconstrução dos serviços, envie o erro e `docker compose ps` antes de tentar novamente.
