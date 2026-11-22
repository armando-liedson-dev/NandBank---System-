# Contrato de integração — FastAPI Gateway

Esta tabela reflecte a cópia de referência `REFERENCIA_gateway.py` enviada com o brief. A versão executada no Windows pode ser diferente; confirme o OpenAPI do Gateway em execução antes da integração final. O navegador não chama directamente o agente Windows.

## Autenticação e conta

| Método e caminho | Pedido | Resposta usada pela interface | Acesso |
|---|---|---|---|
| `GET /api/health` | — | `status`, `app`, `timestamp` | Público |
| `GET /api/config` | — | `name`, `regions`, `currencies`, `notice` | Público |
| `POST /api/auth/login` | `{ email, password }` | `{ access_token, token_type, role, name }` | Público |
| `GET /api/me` | Bearer token | `{ user, accounts }`; conta inclui `id`, `region`, `branch`, `currency` e saldo quando disponível | Autenticado |
| `POST /api/auth/register` | `{ name, email, password, branch }`; `currency` é opcional no Gateway | `{ ok, account_id, user_id, message }` | Público; a filial é validada pelo Gateway |
| `POST /api/accounts` | `{ branch }`; moeda opcional | `{ ok, account_id, balance_minor }` | Cliente |
| `GET /api/accounts/lookup/{account_id}` | Bearer token | `account_id`, `beneficiary`, `region`, `branch`, `currency` | Autenticado |
| `GET /api/accounts/{account_id}` | Bearer token | Conta e saldo conforme autorização | Titular/gestor autorizado |
| `GET /api/accounts/{account_id}/details` | Bearer token | Dados bancários académicos e aviso de que os identificadores são fictícios | Titular/gestor autorizado |
| `GET /api/accounts/{account_id}/ledger` | Bearer token | Registos do livro razão devolvidos pelo serviço regional | Titular/gestor autorizado |

A palavra-passe de registo exige 12–200 caracteres, com pelo menos uma maiúscula, uma minúscula e um número. A interface não guarda palavras-passe; o token fica apenas na sessão do separador. O Gateway não fornece um endpoint de refresh na referência.

## Câmbio, transferências e comprovativos

| Método e caminho | Pedido | Resposta usada pela interface | Acesso |
|---|---|---|---|
| `GET /api/fx/quote?source=…&destination=…&amount=…` | Códigos de moeda e montante decimal | `source_currency`, `destination_currency`, `amount_minor`, `fee_minor`, `total_debit_minor`, `credit_minor`, `rate`, `source_amount`, `fee`, `total_debit`, `recipient_amount`, `fx_source`, `updated_at`, `notice` | Público na referência |
| `GET /api/fx/rates` | — | Lista de moedas, unidades por EUR, origem e actualização | Público |
| `POST /api/transfers` | `{ source_id, destination_id, amount, idempotency_key, note? }` | Resultado do coordenador e cotação; o estado vem do Gateway | Cliente autenticado |
| `GET /api/transfers` | Bearer token | Registos limitados conforme o perfil | Cliente/gestor autorizado |
| `GET /api/transfers/{tx_id}` | Bearer token | Estado e valores da transferência | Conforme titular e papel |
| `GET /api/transactions/{tx_id}/receipt.pdf` | Bearer token | PDF apenas quando o estado é `COMMITTED` | Conforme titular e papel |

O mesmo pedido de transferência conserva a mesma chave de idempotência durante uma tentativa repetida. Uma alteração dos dados cria uma chave nova. O browser só mostra “concluída” quando lê o estado devolvido pelo servidor.

## Cartões académicos

| Método e caminho | Pedido | Resposta usada pela interface | Acesso |
|---|---|---|---|
| `GET /api/cards` | Bearer token | Cartões do titular; a interface mostra apenas `last4` quando fornecido | Cliente |
| `POST /api/cards/request` | `{ account_id }` | `{ id, status: "REQUESTED", message }` | Titular da conta |
| `POST /api/cards/{card_id}/freeze` ou `/unfreeze` | Sem corpo | `{ ok, status }` | Titular do cartão |
| `GET /api/admin/cards` | Bearer token | Pedidos de cartão no âmbito autorizado | Gerente regional/global |
| `POST /api/admin/cards/{card_id}/review` | `{ approved: boolean }` | `{ ok, status }` | Gerente regional/global |

São cartões virtuais académicos. Não representam redes de pagamento, não mostram PAN completo ou CVV e não autorizam compras reais.

## Gestão, nós e auditoria

| Método e caminho | Pedido/resposta | Acesso |
|---|---|---|
| `GET /api/admin/stats` | `clients`, `transfers`, `operations`, `regions` | Gestores e perfis de balcão autorizados; o âmbito é definido no servidor |
| `GET /api/admin/nodes` | Estado regional, `primary_status`, `standby_status`, `service_available`, eventos e mensagem | Gestor autorizado; global recebe regiões disponíveis |
| `GET /api/failover/status` | Estado de failover e disponibilidade | Autenticado; região conforme papel |
| `GET /api/admin/operations` | Registos operacionais | Gestor autorizado, filtrado por região/filial |
| `GET /api/admin/node-actions` | `{ agent_online, jobs }` | Gestor regional/global autorizado |
| `POST /api/admin/nodes/{code}/action` | `{ action: STOP_PRIMARY | START_PRIMARY, reason, note? }`; responde `202` com `id`, `status`, `message` | Gestor regional/global; exige o agente Windows ligado |
| `GET /api/admin/audit` | Eventos de auditoria | Apenas gerente global |

Motivos aceites na cópia de referência: `MAINTENANCE`, `FAULT`, `SECURITY`, `UPGRADE`, `FAILOVER_TEST`, `OTHER`. O Gateway pode responder `503` se o agente estiver desligado ou a região estiver indisponível; a interface não inventa progresso ou ETA.

## Respostas e limites tratados

- `401`: termina a sessão, limpa dados em memória e regressa à entrada.
- `403`: apresenta falta de autorização; a decisão efectiva continua no Gateway.
- `404`: informação inexistente; não substitui por dados inventados.
- `409`: conflito, por exemplo chave de idempotência reutilizada com dados diferentes.
- `400`/`422`: apresenta validação e pede correcção dos campos.
- `503`, timeout ou falha de rede: indica indisponibilidade e oferece nova tentativa.
- TLS/CORS: devem ser corrigidos no ambiente do Gateway; o browser não desactiva a validação TLS.

## Não incluído

Não foram ligados depósitos/levantamentos de balcão, sincronização ou edição global de câmbio, execução Docker, `/api/agent/jobs`, investimentos, recargas ou pagamentos de serviços. Estes fluxos não são apresentados como operações do cliente nesta interface.