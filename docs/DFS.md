# Sistema de Ficheiros Distribuído (NFS) no Windows + Docker Desktop

**Estado do requisito:** opção NFS preparada para ensaio, ainda não certificada em WSL2. Não confundir um volume Docker local com um DFS validado.

O novo exame pede NFS/GlusterFS/HDFS ou equivalente para logs de auditoria e relatórios entre servidores. Em Windows, um NFS server em contentor Linux pode exigir suporte de kernel/privileged e configuração especial de WSL2. Por isso o serviço `nfs-server` e `nfs-client` estão no perfil `dfs` e não bloqueiam o arranque bancário normal.

### Teste

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\VERIFICAR_DFS_WINDOWS.ps1
# Se iniciar e montar:
docker compose --profile dfs exec nfs-client sh -c "echo globalscale-nfs-ok >> /mnt/shared/auditoria.txt; cat /mnt/shared/auditoria.txt"
```

Confirmar que o NFS server consegue ler o mesmo ficheiro e que não está apenas a utilizar outro volume interno. Se `mount` falhar, recolher logs, verificar suporte NFS no kernel do Docker Desktop/WSL2 e escolher uma VM Ubuntu com NFS se necessário. Um segundo nó Ubuntu no mesmo PC é aceitável como simulação de sistema operativo, mas não equivale a alta disponibilidade física.

**Por implementar para fechar 100% este requisito:** redireccionar os logs de auditoria e os relatórios do Gateway e dos participantes para a montagem NFS partilhada, validar escrita concorrente e recuperação após desligar o processo consumidor. Actualmente os registos de auditoria transaccional são duráveis no PostgreSQL global e os movimentos nas bases regionais, sem sincronização para NFS.
