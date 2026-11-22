# Relatório de testes — NandBank

## Regras cobertas por testes automatizados

- Registo: palavra-passe mínima de 12 caracteres, com maiúscula, minúscula e número.
- Demonstração: registos fictícios só são usados quando o modo de demonstração está explicitamente activo.
- Transferência: a chave de idempotência mantém-se num retry dos mesmos dados e muda quando os dados mudam.

## Validação do projecto

| Verificação | Resultado |
|---|---|
| Testes automatizados | Aprovados: 4 testes em 2 ficheiros. |
| Build do preview | Aprovado: última compilação registada como `build OK`. |
| Rotas e metadados | Aprovados: 15 páginas abriram em desktop com títulos próprios. |
| Ecrãs desktop e mobile | Aprovados: sem overflow horizontal a 1280×1800; também verificados a 390×844, incluindo menu móvel. |
| Estados de ligação | Aprovados: sem dados fictícios no modo normal; a entrada apresenta aviso explícito quando o Gateway não está ligado. |
| Erros de renderização | Nenhum erro de hidratação ou HTML inválido nas páginas verificadas após as correcções. |
| Gateway Windows real | Não ligado neste ambiente; requer o endereço e uma sessão de teste do Gateway do utilizador. |

O preview devolveu HTTP 406 para chamadas da API, por não estar ligado ao Gateway. Por isso, autenticação real, contas, cotações, transferências, permissões e publicação em `/app/ui` ainda precisam de ser ensaiadas no ambiente Windows. Não foram usados dados de clientes reais nem segredos.