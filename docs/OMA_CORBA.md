# OMA/CORBA e sua relação com o NandBank

**Requisito do Exame:** análise teórica comparativa; não exige servidor CORBA em execução.

A Object Management Architecture (OMA) proposta pela OMG descreve um modelo de objectos distribuídos, interfaces e serviços comuns. CORBA, por meio de IDL, ORB e IIOP, permitia que programas em linguagens diferentes invocassem métodos de objectos remotos. Um ORB tratava a localização do objecto, a serialização e a chamada remota. Os serviços de objectos acrescentavam registo de nomes, transacções e segurança, conforme implementação.

No NandBank, a função conceptual do ORB é distribuída pelos componentes modernos: o Gateway encaminha pedidos, HAProxy descobre a instância saudável de cada região, o contrato REST/JSON descreve mensagens e o serviço Java interoperabiliza com Python usando um formato comum. A gestão das transacções está no coordenador 2PC, não no protocolo de transporte.

| Propriedade | CORBA / ORB | Arquitectura NandBank |
|---|---|---|
| Contrato | IDL e interfaces tipadas | REST/JSON e modelos de validação FastAPI |
| Descoberta | Naming Service / ORB | DNS Docker e HAProxy |
| Comunicação | IIOP com CDR binário | HTTP/JSON protegido por TLS/mTLS |
| Invocação | Métodos remotos | Endpoints de recursos e operações |
| Independência de linguagem | Stubs de IDL | Java + Python comunicam por JSON |
| Segurança | Políticas e serviços do middleware | JWT, TLS/mTLS, HMAC e RBAC |
| Coordenação | Serviço de transacções CORBA (possível) | Coordenador 2PC persistente em PostgreSQL |

O Laboratório 6 da disciplina ensinou `criarConta`, `consultarSaldo`, `depositar`, `sacar` e `transferir`, além de benchmarking de 10.000 consultas por tecnologia. As mesmas operações bancárias compõem o novo protótipo, mas o benchmark de CORBA contra REST do laboratório **não foi reexecutado neste novo ambiente**, pelo que não há métricas comparáveis a declarar.

Referências para o relatório: OMG (CORBA Specification), IETF RFC 8259 (JSON), Fielding (REST), documentação PostgreSQL (PREPARE TRANSACTION / COMMIT PREPARED), documentação HAProxy (health checks) e enunciado do exame SDP 2026.
