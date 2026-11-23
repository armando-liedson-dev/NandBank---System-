# NandBank — Roteiro de defesa prática (10 minutos)

## Equipamento

- **PC Windows:** Docker Desktop e painel do gerente regional África.
- **Telemóvel 1:** cliente de Maputo (MZN).
- **Telemóvel 2:** cliente de Lisboa (EUR).
- **GitHub Pages:** landing page e demonstração visual pública. A API real é local.

## 1. Introdução (1 minuto)

«O NandBank é um banco distribuído académico. A sua arquitectura separa contas por seis regiões e permite transferências internacionais com consistência transaccional e comunicação segura.»

## 2. Arquitectura (2 minutos)

Mostrar `docker compose ps`, painel dos nós e explicar:

- 6 bases continentais e 1 global.
- 2 serviços de aplicação por continente: primary e standby.
- HAProxy e Gateway entre clientes e serviços.
- 2PC para várias bases, transacções ACID locais, JWT, mTLS e Java legado.

## 3. Contas e câmbio (2 minutos)

Cliente Maputo com conta MZN; cliente Lisboa com conta EUR. Gerente África faz depósito fictício ao cliente de Maputo. Cliente Maputo envia MZN para Lisboa. O beneficiário recebe EUR à cotação demonstrativa exibida e pode consultar o saldo local. Mostrar o PDF do remetente.

## 4. Falha durante operações (3 minutos)

1. No painel África confirmar primary e standby disponíveis.
2. Seleccionar «Desligar nó principal» e o motivo «Teste de tolerância a falhas». O agente Windows recebe a acção autenticada.
3. No cliente Maputo, demonstrar o aviso de indisponibilidade temporária. No cliente Lisboa, ao tentar transferir para África, demonstrar o estado do nó envolvido.
4. O HAProxy encaminha para o standby após detecção. Depois da pausa configurada e saúde confirmada, repetir uma transferência **apenas após consultar o estado de uma tentativa anterior**.
5. Gerente solicita «Ligar nó principal». Verificar o estado real e o restauro.

**Não afirmar:** que a base de dados tem réplica ou que a comunicação de uma transferência interrompida pelo desligamento abrupto será sempre transparente. O 2PC pode precisar de recuperação após decisão durável.

## 5. Cartões e conclusão (2 minutos)

Cliente solicita cartão académico. Gerente regional aprova. Cliente congela/descongela. Explicar por que não usa PAN ou CVV real e não é cartão Visa/Mastercard. Concluir mostrando README, Actions e Pages e distinguindo a interface pública do backend em Docker.

## Se algum serviço falhar na demonstração

- `docker compose ps`
- `docker compose logs --tail=70 gateway router af-primary af-standby db-af`
- `Get-Content .credentials` **somente em privado**, sem partilhar no projector ou no Git.
- Não executar `docker compose down -v`.

## Evidências recomendadas

Capturas de ecrã reais dos saldos antes/depois, decisão 2PC, resultado do teste, nó principal down/standby up, pedido de cartão pendente e aprovado, GitHub Actions e GitHub Pages acessível fora da rede.
