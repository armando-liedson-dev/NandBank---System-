# NandBank — Começar aqui

O ZIP contém um projecto académico **completo para publicação do código** e uma **demonstração estática** para GitHub Pages. O backend distribuído funciona **localmente no Windows + Docker**, não no GitHub Pages.

## No VS Code e GitHub

1. Extrai o ZIP. Abre a pasta `NandBank` no VS Code.
2. Cria um repositório no GitHub e associa-o à pasta. Exemplo no terminal:

```powershell
git init
git add .
git commit -m "feat: plataforma NandBank com frontend público e backend distribuído"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
git push -u origin main
```

3. Em **Settings > Pages > Build and deployment > Source**, escolhe **GitHub Actions**. O workflow `.github/workflows/pages.yml` publica automaticamente `pages/` após o push na branch `main`.
4. Abre a página indicada pelo GitHub Pages. Ela oferece **landing page e frontend de demonstração**, com operações fictícias que **não** modificam as bases de dados.

## No PC Windows com Docker Desktop

1. Abre o Docker Desktop e aguarda o motor Linux/WSL2 ficar operacional.
2. Executa `INICIAR_NANDBANK.bat` (recompila a versão NandBank) ou `INICIAR_WINDOWS.bat` para arranque normal.
3. Abre `https://localhost:8443` no PC. Nos telemóveis da **mesma rede**, usa `https://IP-DO-PC:8443`.
4. Em PowerShell no projecto, consulta **em privado** `Get-Content .credentials` para ler os emails e palavras-passe iniciais.
5. Executa `TESTAR_TUDO_WINDOWS.bat`. Guarda o resultado real para a defesa; o teste Docker integral só pode ser validado na tua máquina.

## Segurança e dados

- **Nunca publicar** `.env`, `.credentials`, chaves, certificados privados, `.private-backups` ou volumes PostgreSQL. Já constam de `.gitignore`.
- **Não utilizar** `docker compose down -v`: apaga os volumes e os dados do protótipo.
- O NandBank é **académico**: não movimenta dinheiro real nem emite cartões bancários reais.
- Para simular falhas pelo painel, o agente controlado `scripts/AGENTE_NOS_WINDOWS.ps1` deve estar em execução no servidor Windows.

Documentação completa: `README.md`; critérios e limitações: `docs/RELATORIO_VALIDACAO.md`; roteiro: `docs/GUIA_DEFESA_NANDBANK.md`.
