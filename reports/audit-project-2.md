# Audit Report — ecommerce-api-legacy (2026-09-26)

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.22.1
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 5 | HIGH: 3 | MEDIUM: 4 | LOW: 2

| #  | Severity | Anti-pattern                                   | Location |
|----|----------|------------------------------------------------|----------|
| 1  | CRITICAL | Credenciais e segredos hardcoded               | src/utils.js:2-5 |
| 2  | CRITICAL | Armazenamento inseguro de senhas               | src/utils.js:17-23, src/AppManager.js:68, src/AppManager.js:18 |
| 3  | CRITICAL | Exposição de dados sensíveis em log            | src/AppManager.js:45 |
| 4  | CRITICAL | Endpoints perigosos sem autenticação           | src/AppManager.js:80-129, src/AppManager.js:131-137 |
| 5  | CRITICAL | God Class                                      | src/AppManager.js:4-139 |
| 6  | HIGH     | Regra de negócio na camada de rota             | src/AppManager.js:28-78, src/AppManager.js:80-129 |
| 7  | HIGH     | Estado global mutável e dependência acoplada   | src/utils.js:9-10, src/utils.js:14, src/AppManager.js:7 |
| 8  | HIGH     | Operação multi-etapa sem transação / callback hell | src/AppManager.js:37-77 |
| 9  | MEDIUM   | Queries N+1                                    | src/AppManager.js:89-127 |
| 10 | MEDIUM   | Validação ausente                              | src/AppManager.js:35, src/AppManager.js:46 |
| 11 | MEDIUM   | Erros de callback ignorados                    | src/AppManager.js:57, src/AppManager.js:92-93, src/AppManager.js:104-106, src/AppManager.js:133-135 |
| 12 | MEDIUM   | Integridade referencial ausente                | src/AppManager.js:131-137, src/AppManager.js:12-15 |
| 13 | LOW      | Magic numbers / strings de regra de negócio    | src/AppManager.js:46, src/AppManager.js:48, src/AppManager.js:108 |
| 14 | LOW      | Código morto e nomes que enganam               | src/utils.js:2-3, src/utils.js:5, src/utils.js:9-10, src/utils.js:17, src/AppManager.js:2 |

## Findings

### [CRITICAL] Credenciais e segredos hardcoded (AP-02)
File: src/utils.js:2-5
Description: O objeto `config` traz no código a senha do banco (`dbPass: "senh****"`), a chave de produção do gateway de pagamento (`paymentGatewayKey: "pk_l****"`) e o usuário SMTP.
Impact: Qualquer pessoa com acesso ao repositório tem a chave live do gateway e a senha do banco; trocar credenciais exige editar e redeployar código.
Recommendation: `src/config/index.js` lendo `PAYMENT_GATEWAY_KEY`, `PORT` e `ADMIN_TOKEN` de `process.env`, sem defaults reais, + `.env.example` (T-02).

### [CRITICAL] Armazenamento inseguro de senhas (AP-03)
File: src/utils.js:17-23, src/AppManager.js:68, src/AppManager.js:18
Description: `badCrypto` não é hash: repete os 2 primeiros caracteres do base64 da senha e trunca em 10 (senhas com o mesmo início geram o mesmo "hash"). Sem `pwd`, o usuário é criado com a senha fixa `"123456"`; o seed grava `'123'` em texto plano.
Impact: Senhas triviais de reverter/colidir e contas criadas no checkout com senha conhecida por qualquer um.
Recommendation: `crypto.scryptSync` com salt aleatório (stdlib); sem `pwd`, gerar senha aleatória em vez de default fixo; seed também com hash (T-03).

### [CRITICAL] Exposição de dados sensíveis em log (AP-04)
File: src/AppManager.js:45
Description: `console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`)` grava o número completo do cartão e a chave do gateway em todo checkout.
Impact: Vazamento de PAN e da chave de pagamento para qualquer destino de log (violação de PCI-DSS).
Recommendation: Logar só os 4 últimos dígitos do cartão e nunca a chave (T-04).

### [CRITICAL] Endpoints perigosos sem autenticação (AP-05)
File: src/AppManager.js:80-129, src/AppManager.js:131-137
Description: `GET /api/admin/financial-report` expõe faturamento e nomes de alunos, e `DELETE /api/users/:id` apaga usuários, ambos sem nenhuma autenticação.
Impact: Qualquer cliente anônimo lê dados financeiros e apaga contas.
Recommendation: **Manter as rotas** e protegê-las com middleware de admin (`X-Admin-Token` comparado com `ADMIN_TOKEN` do ambiente; sem token configurado → 403) (T-05).

### [CRITICAL] God Class (AP-06)
File: src/AppManager.js:4-139
Description: `AppManager` cria a conexão (`new sqlite3.Database`), cria schema e seed (`initDb`), registra todas as rotas (`setupRoutes`), processa pagamento, grava auditoria e monta o relatório financeiro.
Impact: Nenhuma parte pode ser testada ou trocada isoladamente; toda mudança passa pela mesma classe.
Recommendation: Separar em `database.js`, `models/`, `services/paymentService.js`, `controllers/`, `routes/` e `app.js` como composition root (T-06).

### [HIGH] Regra de negócio na camada de rota (AP-07)
File: src/AppManager.js:28-78, src/AppManager.js:80-129
Description: O handler de checkout (50 linhas) busca curso, busca/cria usuário, decide o pagamento (`cc.startsWith("4")`), matricula e audita; o handler do relatório agrega receita e alunos dentro da rota.
Impact: Regras de pagamento e de relatório não são testáveis sem HTTP e banco.
Recommendation: Rotas finas em `src/routes/`, fluxo em `checkoutController`/`reportController`, SQL nos models (T-07, T-16).

### [HIGH] Estado global mutável e dependência acoplada (AP-08)
File: src/utils.js:9-10, src/utils.js:14, src/AppManager.js:7
Description: `globalCache` e `totalRevenue` são estado de módulo exportado; `globalCache` é gravado a cada checkout e nunca lido. O construtor de `AppManager` instancia a própria conexão SQLite.
Impact: Crescimento de memória sem limite (cache sem leitor) e impossibilidade de injetar outro banco em testes.
Recommendation: Remover o cache sem leitor; conexão criada no entry point e passada aos models por parâmetro (T-08).

### [HIGH] Operação multi-etapa sem transação / callback hell (AP-09)
File: src/AppManager.js:37-77
Description: Checkout grava usuário → matrícula → pagamento → auditoria em 5 níveis de callbacks aninhados, sem `BEGIN/COMMIT/ROLLBACK`. O usuário é criado antes da decisão de pagamento e permanece mesmo com pagamento recusado.
Impact: Falha no meio deixa matrícula sem pagamento ou usuário órfão; fluxo difícil de ler e sem tratamento de erro único.
Recommendation: `async/await` com helpers Promise e `transaction()` em `database.js`; autorizar o pagamento antes de gravar (T-09).

### [MEDIUM] Queries N+1 (AP-11)
File: src/AppManager.js:89-127
Description: Para cada curso, uma query de matrículas; para cada matrícula, uma query de usuário e outra de pagamento.
Impact: O relatório faz 1 + C + 2·M queries, crescendo com o número de matrículas.
Recommendation: Uma query com LEFT JOINs e agregação em memória (`reduce`) no model (T-10).

### [MEDIUM] Validação ausente (AP-12)
File: src/AppManager.js:35, src/AppManager.js:46
Description: O checkout só testa presença de campos. `card` numérico (ex.: `4111...` sem aspas) faz `cc.startsWith` lançar TypeError dentro do callback do sqlite.
Impact: Um único request malformado derruba o processo Node inteiro (exceção não capturada em callback), tirando a API do ar.
Recommendation: Validar tipos no controller (card string de dígitos, c_id numérico) e responder 400 "Bad Request" (T-12).

### [MEDIUM] Erros de callback ignorados (AP-13)
File: src/AppManager.js:57, src/AppManager.js:92-93, src/AppManager.js:104-106, src/AppManager.js:133-135
Description: O `err` é descartado na auditoria, no relatório (`enrollments.length` com `enrollments` indefinido em erro) e no delete, que responde sucesso mesmo quando falha.
Impact: Erros de banco viram crash do processo ou falso sucesso; não há handler central.
Recommendation: Erros propagados por `async/await` até um `errorHandler` central do Express, mantendo o formato texto das respostas (T-11).

### [MEDIUM] Integridade referencial ausente (AP-14)
File: src/AppManager.js:131-137, src/AppManager.js:12-15
Description: `DELETE /api/users/:id` apaga só o usuário; tabelas sem `FOREIGN KEY`. A própria resposta admite: "as matrículas e pagamentos ficaram sujos no banco".
Impact: Matrículas e pagamentos órfãos distorcem o relatório financeiro (alunos "Unknown" com receita).
Recommendation: Apagar pagamentos, matrículas e usuário dentro da mesma transação (T-09).

### [LOW] Magic numbers / strings de regra de negócio (AP-17)
File: src/AppManager.js:46, src/AppManager.js:48, src/AppManager.js:108
Description: A regra de aprovação do gateway simulado (`cc.startsWith("4")`) e os status `"PAID"`/`"DENIED"` aparecem como literais espalhados.
Impact: Mudar a regra de aprovação ou um status exige caçar strings em vários pontos; erro de digitação quebra o relatório silenciosamente.
Recommendation: `PAYMENT_STATUS` e `APPROVED_CARD_PREFIX` como constantes em `config` (T-14).

### [LOW] Código morto e nomes que enganam (AP-18)
File: src/utils.js:2-3, src/utils.js:5, src/utils.js:9-10, src/utils.js:17, src/AppManager.js:2
Description: `dbUser`, `dbPass` e `smtpUser` nunca são usados; `totalRevenue` é importado e nunca atualizado; `globalCache` nunca é lido; `badCrypto` é usado como se fosse hash de senha.
Impact: Código morto esconde segredos reais no repositório e o nome `badCrypto` induz a achar que existe hash.
Recommendation: Remover na limpeza da T-06; substituir `badCrypto` pelo hash da T-03.

## Notes
- Deprecated APIs: none detected (Express 4.22.1 já usa `express.json()`; sem `new Buffer`, `url.parse`, `createCipher`, `req.param`).
- SQL Injection: não encontrado — todas as queries usam placeholders `?`.
- Outros pontos menores, fora do escopo: `console.log` de cache em src/utils.js:13 (AP-16); nomes de variável curtos `u`, `e`, `p`, `cid`, `cc` (src/AppManager.js:29-33 — são o contrato `usr/eml/pwd/c_id/card`, só renomear internamente).
- Pontos a preservar: nomes dos campos de request (`usr`, `eml`, `pwd`, `c_id`, `card`), respostas em texto puro nos erros, porta 3000 e `npm start`.

================================
Total: 14 findings
================================
```
