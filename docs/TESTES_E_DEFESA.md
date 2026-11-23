# Testes obrigatórios e defesa prática

## 1. Instalar e registar evidências

Executar `INICIAR_WINDOWS.bat`, abrir https://localhost:8443 e capturar `docker compose ps`. Verificar que as bases e a rede de seis regiões foram iniciadas. Registar o IP local utilizado pelos telemóveis (não confundir com estar realmente a alojar servidores em continentes físicos).

## 2. Testes automatizados (antes de abrir a apresentação)

Executar `TESTAR_TUDO_WINDOWS.bat`. O script `backend/app/smoke.py` verifica:

1. API e seis regiões disponíveis;
2. cadastro de cliente Madrid (EUR) e Xangai (CNY);
3. depósito de 700 EUR por gerente europeu;
4. repetição do depósito com mesma chave sem crédito duplicado;
5. débito de 120 EUR + comissão, crédito correspondente em CNY após 2PC;
6. repetição da mesma transferência com a mesma chave sem segundo débito;
7. recusa por saldo insuficiente sem afectar nenhum saldo;
8. transferência intrarregional ACID para Lisboa;
9. comprovativo PDF autenticado;
10. gestor regional com visão do próprio nó.

Se surgir erro, copiar o terminal e executar `docker compose logs --tail=90 gateway router legacy eu-primary eu-standby as-primary as-standby db-global db-eu db-as`. **Não apagues volumes para corrigir.**

## 3. Demonstração com dois telemóveis

Ambos na mesma rede. Abrir `https://<IP_PC>:8443` (CA de teste). No telemóvel 1, criar conta em Espanha/Madrid com EUR; no telemóvel 2, criar conta em China/Xangai com CNY. Copiar ID da conta de Xangai. No PC, entrar como gerente europeu e efectuar depósito na conta Madrid. No primeiro telemóvel, transferir para a conta Xangai, mostrar cotação e comissão, confirmar. No segundo, consultar saldo e movimentos. No PC, gerente global consulta o histórico e as regiões. Descarregar comprovativo PDF no telemóvel 1.

## 4. Falha de aplicação durante serviço

Executar `DEMO_FAILOVER_WINDOWS.bat`, ou manualmente:

```powershell
docker compose stop as-primary
Start-Sleep -Seconds 7
docker compose exec -T gateway python -m app.smoke
docker compose up -d --no-build as-primary
```

Na página "Nós continentais" o campo Ásia deve indicar **Reserva** enquanto a principal estiver parada. O teste automático deve confirmar transferências e depósitos no cenário de falha de **aplicação**. Não garante sucesso se a base regional cair.

## 5. Falha do coordenador e recuperação de 2PC

A interrupção do coordenador a meio de um `PREPARE` pode bloquear temporariamente linhas até à decisão de recuperação. Apresentar logs e verificar a recuperação automática após reinício. Se forçar falhas manualmente, anotar ID da transacção; inspecionar `pg_prepared_xacts`, decisões no banco global e estado das duas contas antes de considerar concluído. **Nunca confirmar uma transacção que só foi preparada.**

## 6. Saldo insuficiente

Cliente com 50 EUR tenta enviar 20.000 EUR: mensagem `SALDO_INSUFICIENTE`, saldo origem intacto, nenhum crédito destino, estado `ABORTED`.

## 7. Moedas e depósitos de balcão

Criar conta EUR e depositar MZN no painel do gerente autorizado. Observar montante e moeda recebida, taxa, saldo de crédito em EUR e registo no painel. Mostrar que a taxa DEMO pode ser alterada pelo gerente global; a transferência seguinte utiliza a taxa nova, mas anteriores guardam a antiga.

## 8. Concorrência e idempotência

Fazer duas transferências simultâneas de uma conta com saldo para uma só, tentar repetir uma `idempotency_key` e mostrar apenas uma aplicação. O PostgreSQL utiliza `SELECT FOR UPDATE` e 2PC para controlar as operações. Para a defesa, usar logs reais para provar o resultado.

## 9. DFS/NFS

Executar `scripts/VERIFICAR_DFS_WINDOWS.ps1` e demonstrar escrita e leitura do mesmo ficheiro por dois contentores. Só marcar como concluído se a montagem e o teste de concorrência tiverem êxito no Windows/WSL2.

## 10. Evidências para o relatório

Usar capturas do Docker, endereços/portas da rede, GET `/docs`, painéis, formulário FX, transferência Madrid→Xangai, saldos antes/depois, `db` com estados 2PC, falha/standby, NFS, HMAC válido/inválido e PDFs. As figuras de demonstração precisam de registos reais. O ficheiro de arquitectura serve para os diagramas teóricos.
