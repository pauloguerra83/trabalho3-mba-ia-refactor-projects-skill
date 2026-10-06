# Skill `refactor-arch` — Refatoração Arquitetural Automatizada

Skill do Claude Code que analisa um backend legado, audita anti-patterns por severidade e o refatora para MVC, validando que a aplicação continua funcionando. A skill está em `.claude/skills/refactor-arch/` dentro de cada projeto (as 3 cópias são idênticas) e os relatórios de auditoria estão em [`reports/`](reports/). Enunciado original: [devfullcycle/mba-ia-refactor-projects-skill](https://github.com/devfullcycle/mba-ia-refactor-projects-skill).

**Código original:** o estado dos projetos antes da refatoração, já com a skill, está preservado no commit `34653e8`. É o ponto de partida para executar a skill novamente (veja [Como Executar](#d-como-executar)).

---

## A) Análise Manual

As linhas citadas referem-se ao código **original** de cada projeto.

### code-smells-project (Python/Flask — API de E-commerce)

| Severidade | Problema | Por que é relevante |
|---|---|---|
| CRITICAL | SQL injection por concatenação de strings (`models.py:28`, `models.py:109-111`, `models.py:289-297`) | `' OR '1'='1' --` no e-mail do `/login` autentica como admin sem senha; qualquer cliente lê ou altera o banco. |
| CRITICAL | Senhas em texto plano e devolvidas em `GET /usuarios` (`models.py:83`, `database.py:75-83`) | Qualquer cliente anônimo obtém a senha de todos os usuários. |
| CRITICAL | `POST /admin/query` executa SQL arbitrário e `/admin/reset-db` apaga tudo, sem autenticação (`app.py:47-78`) | Uma requisição anônima destrói ou exfiltra o banco inteiro. |
| HIGH | `debug=True` e `host="0.0.0.0"` fixos (`app.py:8`, `app.py:88`) | O debugger do Werkzeug exposto na rede permite execução remota de código. |
| MEDIUM | Queries N+1 na listagem de pedidos (`models.py:187-199`) | 1 query por pedido e mais 1 por item: o custo cresce com o volume de vendas. |
| MEDIUM | `except Exception as e: return {"erro": str(e)}` em 17 handlers (`controllers.py:10-12`, …) | Vaza mensagens internas do SQLite ao cliente e facilita explorar a injeção. |
| LOW | `print` no lugar de logging, inclusive com e-mail do usuário (`controllers.py:179`, `controllers.py:182`) | Sem nível nem destino configurável; dado pessoal no stdout a cada login. |
| LOW | Listas de categorias/status e faixas de desconto como literais (`controllers.py:52`, `models.py:256-262`) | A regra fica espalhada; `PUT /produtos` nem usa a lista de categorias. |

### ecommerce-api-legacy (Node.js/Express — LMS com checkout)

| Severidade | Problema | Por que é relevante |
|---|---|---|
| CRITICAL | Chave live do gateway de pagamento e senha do banco no código (`src/utils.js:2-5`) | Qualquer pessoa com acesso ao repositório tem credenciais de produção. |
| CRITICAL | Número completo do cartão e chave do gateway no log (`src/AppManager.js:45`) | Vazamento de dados de cartão (PCI-DSS) para qualquer destino de log. |
| CRITICAL | "Hash" de senha é base64 truncado; sem senha, o usuário recebe `"123456"` (`src/utils.js:17-23`, `src/AppManager.js:68`) | Senhas reversíveis e contas criadas com senha conhecida por todos. |
| HIGH | Checkout em 5 níveis de callbacks sem transação (`src/AppManager.js:37-77`) | Uma falha no meio deixa matrícula sem pagamento ou usuário órfão. |
| MEDIUM | `card` numérico faz `cc.startsWith` lançar TypeError dentro do callback (`src/AppManager.js:46`) | Um único request malformado derruba o processo Node inteiro. |
| MEDIUM | `DELETE /api/users/:id` apaga só o usuário (`src/AppManager.js:131-137`) | Matrículas e pagamentos órfãos aparecem como "Unknown" no relatório financeiro. |
| LOW | Regra de aprovação `startsWith("4")` e status `"PAID"`/`"DENIED"` como literais (`src/AppManager.js:46`, `src/AppManager.js:108`) | Mudar a regra exige caçar strings; um erro de digitação quebra o relatório silenciosamente. |
| LOW | Código morto: `globalCache` nunca lido, `totalRevenue` nunca atualizado, `dbUser`/`smtpUser` sem uso (`src/utils.js:2-10`) | Esconde segredos no repositório e confunde a leitura. |

### task-manager-api (Python/Flask — Task Manager, parcialmente em camadas)

| Severidade | Problema | Por que é relevante |
|---|---|---|
| CRITICAL | Senhas com MD5 sem salt (`models/user.py:27-32`) | MD5 sem salt é quebrado por rainbow table em segundos. |
| CRITICAL | `User.to_dict()` inclui o hash da senha, devolvido em 4 rotas, inclusive no login (`models/user.py:21`) | Qualquer cliente obtém o hash, e pelo item anterior a senha. |
| CRITICAL | Login devolve `'fake-jwt-token-' + id` (`routes/user_routes.py:210`) | Token previsível: qualquer um forja a identidade de qualquer usuário. |
| HIGH | Regra de "task atrasada" copiada em 6 rotas, apesar de `Task.is_overdue()` existir (`routes/task_routes.py:30-39`, …) | Mudar a regra exige editar 6 trechos; rotas de 50–70 linhas sem teste possível. |
| MEDIUM | `except:` nu em 8 pontos e nenhum handler central (`routes/task_routes.py:62`, …) | Erros são engolidos sem log; o formato das respostas de erro varia entre JSON e HTML. |
| MEDIUM | `datetime.utcnow()` e `Query.get()` deprecated (`models/task.py:15-16`, `routes/task_routes.py:42`, …) | 31 warnings em runtime hoje e quebra quando as APIs forem removidas. |
| LOW | `print` espalhado nas rotas, inclusive `print(f"ERRO: {e}")` sem stack (`routes/user_routes.py:89`, …) | Erros de banco somem entre prints de sucesso. |
| LOW | `services/` e quase todo `utils/` nunca usados; `marshmallow` e `requests` declarados e não importados | O serviço morto carrega a senha SMTP no repositório. |

---

## B) Construção da Skill

### Decisões de design

O `SKILL.md` é o orquestrador: define as 3 fases, 7 regras globais (escopo, evidência com `arquivo:linha`, nenhuma modificação antes da confirmação, agnosticismo, formato de saída, contrato HTTP preservado e proporcionalidade) e os blocos de saída. O conhecimento de domínio fica em 6 arquivos de referência, e cada fase carrega só os que usa:

| Arquivo | Área de conhecimento | Fase |
|---|---|---|
| `references/project-analysis.md` | Detecção de linguagem, framework, banco, arquitetura e endpoints | 1 |
| `references/anti-patterns-catalog.md` | Catálogo de anti-patterns com sinais de detecção e severidade | 2 |
| `references/audit-report-template.md` | Formato do relatório de auditoria | 2 |
| `references/mvc-guidelines.md` | Camadas do MVC alvo, regras de dependência e proporcionalidade | 3 |
| `references/refactoring-playbook.md` | 16 transformações com exemplos antes/depois (Python e Node) | 3 |
| `references/validation-guide.md` | Baseline, boot, chamada aos endpoints e varredura final | 3 |

A Fase 2 termina obrigatoriamente em `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` e não modifica nenhum arquivo. Depois do "y", a primeira ação da Fase 3 é salvar o relatório em `reports/<nome>.md`.

### Anti-patterns do catálogo e por quê

| Severidade | Anti-patterns |
|---|---|
| CRITICAL | AP-01 SQL injection · AP-02 segredos hardcoded · AP-03 senha insegura · AP-04 exposição de dados sensíveis · AP-05 endpoint perigoso sem auth · AP-06 God Class/File |
| HIGH | AP-07 regra de negócio na camada errada · AP-08 estado global/dependência acoplada · AP-09 escrita multi-etapa sem transação · AP-10 configuração insegura em runtime |
| MEDIUM | AP-11 N+1 · AP-12 validação ausente/duplicada · AP-13 tratamento de erro genérico · AP-14 integridade referencial · AP-15 APIs deprecated |
| LOW | AP-16 print no lugar de logging · AP-17 magic numbers · AP-18 código morto |

O critério foi impacto arquitetural: primeiro o que expõe dados ou permite ataque, depois o que quebra a separação de camadas e a consistência dos dados, e por último qualidade de código. Cada entrada traz sinais concretos de detecção (greps por stack), uma seção "não reportar quando" para evitar falsos positivos e a transformação do playbook que a corrige. O AP-15 tem uma tabela de APIs obsoletas (Python, SQLAlchemy, Flask, Node, Express) com o substituto moderno.

### Como garantimos que a skill é agnóstica de tecnologia

- A stack é decidida por evidência (manifest + imports + assinatura no código), nunca pelo nome do projeto.
- Os sinais de detecção e os exemplos do playbook existem para Python/Flask e Node/Express, e a regra manda traduzir os padrões para outras stacks.
- As guidelines definem duas estratégias: monólito sem camadas vira um pacote `src/`; projeto parcialmente em camadas evolui no lugar, mantendo as pastas que já fazem sentido.
- A validação não depende de framework de teste: compara as respostas HTTP reais antes e depois da refatoração.

### Desafios encontrados e como resolvemos

- **Cota de severidades.** A primeira versão empurrava MEDIUM/LOW para as "Notes" e não atingia o mínimo de 2 LOW. Adicionamos uma distribuição mínima obrigatória (≥1 CRITICAL/HIGH, ≥2 MEDIUM, ≥2 LOW), sempre com evidência confirmada.
- **Relatório só no terminal.** A skill imprimia o relatório, mas ninguém o salvava. Criamos a etapa 3.0, que grava o relatório em `reports/` logo após a confirmação.
- **Over-engineering.** As primeiras refatorações criavam camadas e abstrações sem necessidade. A seção "Proporcionalidade" exige que todo arquivo novo seja justificado por um finding ou seja camada MVC essencial.
- **Falso positivo.** No task-manager-api, a auditoria apontou tasks órfãs ao excluir categoria, mas o baseline mostrou que o SQLAlchemy já anula o `category_id`. O finding foi removido do relatório — a validação por execução real pegou o erro da leitura estática.

---

## C) Resultados

### Resumo dos relatórios de auditoria

| Projeto | Stack | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|---|
| [code-smells-project](reports/audit-project-1.md) | Python + Flask 3.1.1 | 6 | 4 | 3 | 3 | 16 |
| [ecommerce-api-legacy](reports/audit-project-2.md) | Node.js + Express 4.22.1 | 5 | 3 | 4 | 2 | 14 |
| [task-manager-api](reports/audit-project-3.md) | Python + Flask 3.0.0 | 4 | 2 | 4 | 3 | 13 |

### Antes e depois da estrutura

**code-smells-project**
```
Antes                      Depois
app.py                     app.py                  (entry point fino)
controllers.py             src/app.py              (create_app)
models.py                  src/config/             (settings, constants)
database.py                src/database/           (conexão por request, schema/seed)
                           src/models/             (produto, usuario, pedido, sistema)
                           src/controllers/        (produto, usuario, pedido, relatorio, sistema)
                           src/views/              (Blueprints)
                           src/middlewares/        (error_handler, auth)
```

**ecommerce-api-legacy**
```
Antes                      Depois
src/app.js                 src/app.js              (entry point + composition root)
src/AppManager.js          src/config/index.js
src/utils.js               src/database.js         (Promise helpers + transaction)
                           src/models/             (user, course, enrollment)
                           src/services/           (paymentService)
                           src/controllers/        (checkout, report, user)
                           src/routes/             (checkout, admin, user)
                           src/middlewares/        (errorHandler, adminAuth)
```

**task-manager-api**
```
Antes                      Depois
app.py                     app.py                  (create_app)
database.py                database.py             (+ utc_now)
models/                    models/                 (+ métodos de acesso a dados)
routes/                    routes/                 (finas; + category_routes, system_routes)
services/  (não usado)     controllers/            (task, user, report, category)
utils/     (não usado)     config/                 (settings, constants)
seed.py                    middlewares/            (error_handler)
                           seed.py
```

### Checklist de validação

| Item | code-smells-project | ecommerce-api-legacy | task-manager-api |
|---|---|---|---|
| **Fase 1** — Linguagem detectada corretamente | ✅ | ✅ | ✅ |
| Framework detectado corretamente | ✅ | ✅ | ✅ |
| Domínio da aplicação descrito corretamente | ✅ | ✅ | ✅ |
| Número de arquivos analisados condiz com a realidade | ✅ | ✅ | ✅ |
| **Fase 2** — Relatório segue o template | ✅ | ✅ | ✅ |
| Cada finding tem arquivo e linhas exatos | ✅ | ✅ | ✅ |
| Findings ordenados por severidade | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ | ✅ | ✅ |
| Detecção de APIs deprecated incluída | ✅ (nenhuma) | ✅ (nenhuma) | ✅ (2 encontradas) |
| Skill pausa e pede confirmação antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3** — Estrutura de diretórios segue MVC | ✅ | ✅ | ✅ |
| Configuração extraída para módulo de config | ✅ | ✅ | ✅ |
| Models criados para abstrair dados | ✅ | ✅ | ✅ |
| Views/Routes separadas | ✅ | ✅ | ✅ |
| Controllers concentram o fluxo da aplicação | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ | ✅ | ✅ |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem corretamente | ✅ | ✅ | ✅ |

### Logs das aplicações rodando após a refatoração

**code-smells-project** (`python app.py`)
```
2026-09-26 15:02:37,437 WARNING src.app: SECRET_KEY não definida; usando chave efêmera de desenvolvimento
SERVIDOR INICIADO
Rodando em http://127.0.0.1:5000
 * Debug mode: off
2026-09-26 15:02:38,506 INFO src.controllers.produto_controller: Listando 10 produtos
2026-09-26 15:02:38,506 INFO werkzeug: 127.0.0.1 - - [26/Sep/2026 15:02:38] "GET /produtos HTTP/1.1" 200 -
```

**ecommerce-api-legacy** (`npm start`)
```
> node src/app.js
Frankenstein LMS rodando na porta 3000...
Processando pagamento de 497 no cartão final 4444 (gateway simulado)
POST   /api/checkout  -> 200 | {"msg":"Sucesso","enrollment_id":2}
POST   /api/checkout  -> 400 | Pagamento recusado
```

**task-manager-api** (`python seed.py && python app.py`)
```
 * Debug mode: off
 * Running on http://127.0.0.1:5000
2026-09-26 15:56:48,733 INFO werkzeug: 127.0.0.1 - - [26/Sep/2026 15:56:48] "GET /tasks HTTP/1.1" 200 -
2026-09-26 15:56:49,648 INFO controllers.task_controller: Task criada: 11
2026-09-26 15:56:49,648 INFO werkzeug: 127.0.0.1 - - [26/Sep/2026 15:56:49] "POST /tasks HTTP/1.1" 201 -
```

### Validação dos endpoints (antes × depois)

Cada aplicação foi executada duas vezes, sempre com banco limpo: uma com o código **original** (commit `34653e8`) e outra com o código **refatorado**, com `ADMIN_TOKEN` definido. Todas as rotas do inventário original foram chamadas com pelo menos um caso de sucesso e um de erro. As rotas administrativas foram chamadas sem token e com o header `X-Admin-Token`.

A comparação considera o status HTTP e a estrutura da resposta (as chaves), ignorando valores voláteis como ids, datas e token. **Todas as diferenças encontradas são intencionais** e estão ligadas a um finding do relatório. Nenhuma regressão foi encontrada.

| Projeto | Rotas | Requisições | Idênticas | Diferenças intencionais | Boot |
|---|---|---|---|---|---|
| code-smells-project | 19/19 | 32 | 25 | 7 | ✅ `python app.py` |
| ecommerce-api-legacy | 3/3 | 10 | 6 | 4 | ✅ `npm start` |
| task-manager-api | 22/22 | 35 | 30 | 5 | ✅ `python seed.py && python app.py` |

**code-smells-project**
```
✓ Application boots without errors (python app.py — 0 tracebacks, 0 warnings)
✓ All endpoints respond correctly (19/19 rotas, 32 requisições: 25 idênticas ao baseline, 7 diferenças intencionais)
```
Contract Changes:
- `GET /usuarios` e `GET /usuarios/<id>`: o campo `senha` saiu da resposta (AP-04).
- `GET /health`: a resposta não traz mais `secret_key`, `debug` nem `db_path` (AP-02, AP-04).
- `POST /login` com `' OR '1'='1' --` no e-mail: no original autenticava como Admin (200); agora responde 401 (AP-01).
- `POST /admin/query` e `POST /admin/reset-db`: respondem 403 sem `X-Admin-Token`. Com o token, o comportamento é o mesmo do original (AP-05).
- `POST /admin/query` com comando de escrita (`DELETE ...`): no original era executado; agora responde 400 e só aceita uma consulta `SELECT` (AP-05).

<details><summary>Tabela completa — code-smells-project (32 requisições)</summary>

| Método | Rota | Cenário | Antes | Depois | |
|---|---|---|---|---|---|
| GET | `/` | índice | 200 | 200 | = |
| GET | `/health` | health check | 200 | 200 | ≠ |
| GET | `/produtos` | listar | 200 | 200 | = |
| GET | `/produtos/busca?q=Mouse` | buscar | 200 | 200 | = |
| GET | `/produtos/1` | existente | 200 | 200 | = |
| GET | `/produtos/9999` | inexistente | 404 | 404 | = |
| POST | `/produtos` | criar | 201 | 201 | = |
| POST | `/produtos` | sem nome | 400 | 400 | = |
| PUT | `/produtos/11` | atualizar | 200 | 200 | = |
| PUT | `/produtos/9999` | inexistente | 404 | 404 | = |
| GET | `/usuarios` | listar | 200 | 200 | ≠ |
| GET | `/usuarios/1` | existente | 200 | 200 | ≠ |
| GET | `/usuarios/9999` | inexistente | 404 | 404 | = |
| POST | `/usuarios` | criar | 201 | 201 | = |
| POST | `/usuarios` | campos faltando | 400 | 400 | = |
| POST | `/login` | credenciais válidas | 200 | 200 | = |
| POST | `/login` | senha errada | 401 | 401 | = |
| POST | `/login` | SQL injection | 200 | 401 | ≠ |
| POST | `/pedidos` | criar | 201 | 201 | = |
| POST | `/pedidos` | sem itens | 400 | 400 | = |
| GET | `/pedidos` | listar todos | 200 | 200 | = |
| GET | `/pedidos/usuario/2` | por usuário | 200 | 200 | = |
| PUT | `/pedidos/1/status` | status válido | 200 | 200 | = |
| PUT | `/pedidos/1/status` | status inválido | 400 | 400 | = |
| GET | `/relatorios/vendas` | relatório | 200 | 200 | = |
| DELETE | `/produtos/11` | deletar | 200 | 200 | = |
| DELETE | `/produtos/9999` | inexistente | 404 | 404 | = |
| POST | `/admin/query` | SELECT sem token | 200 | 403 | ≠ |
| POST | `/admin/query` | SELECT com token | 200 | 200 | = |
| POST | `/admin/query` | escrita com token | 200 | 400 | ≠ |
| POST | `/admin/reset-db` | sem token | 200 | 403 | ≠ |
| POST | `/admin/reset-db` | com token | 200 | 200 | = |

</details>

**ecommerce-api-legacy**
```
✓ Application boots without errors (npm start — 0 erros)
✓ All endpoints respond correctly (3/3 rotas, 10 requisições: 6 idênticas ao baseline, 4 diferenças intencionais)
```
Contract Changes:
- `GET /api/admin/financial-report` e `DELETE /api/users/:id`: respondem 403 sem `X-Admin-Token`. Com o token, status e formato são os mesmos do original (AP-05).
- `DELETE /api/users/:id`: agora remove matrículas e pagamentos na mesma transação. A mensagem passou de "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco." para "Usuário deletado" (AP-14).
- `POST /api/checkout` com `card` numérico: no original, o `TypeError: cc.startsWith is not a function` derrubava o processo Node e a chamada seguinte falhava com conexão recusada. Agora responde 400 "Bad Request" e o servidor continua no ar (AP-12).

<details><summary>Tabela completa — ecommerce-api-legacy (10 requisições)</summary>

| Método | Rota | Cenário | Antes | Depois | |
|---|---|---|---|---|---|
| POST | `/api/checkout` | pagamento aprovado | 200 | 200 | = |
| POST | `/api/checkout` | pagamento recusado | 400 | 400 | = |
| POST | `/api/checkout` | curso inexistente | 404 | 404 | = |
| POST | `/api/checkout` | campos faltando | 400 | 400 | = |
| GET | `/api/admin/financial-report` | sem token | 200 | 403 | ≠ |
| GET | `/api/admin/financial-report` | com token | 200 | 200 | = |
| DELETE | `/api/users/1` | sem token | 200 | 403 | ≠ |
| DELETE | `/api/users/1` | com token | 200 | 200 | = |
| POST | `/api/checkout` | card numérico | crash | 400 | ≠ |
| GET | `/api/admin/financial-report` | chamada seguinte (processo vivo?) | crash | 200 | ≠ |

</details>

**task-manager-api**
```
✓ Application boots without errors (python seed.py && python app.py — 0 tracebacks, 0 DeprecationWarning)
✓ All endpoints respond correctly (22/22 rotas, 35 requisições: 30 idênticas ao baseline, 5 diferenças intencionais)
```
Contract Changes:
- `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `POST /login`: o campo `password` (hash MD5) saiu do objeto de usuário (AP-04).
- `POST /login`: o `token` agora é assinado com a `SECRET_KEY` (`itsdangerous`) em vez de `fake-jwt-token-<id>`. O nome do campo não mudou (AP-05).
- `GET /tasks/search?priority=abc`: no original dava 500 com a página HTML do debugger do Werkzeug (`ValueError`); agora responde 400 `{"error": "Parâmetro de busca inválido"}` (AP-10, AP-12).

<details><summary>Tabela completa — task-manager-api (35 requisições)</summary>

| Método | Rota | Cenário | Antes | Depois | |
|---|---|---|---|---|---|
| GET | `/` | índice | 200 | 200 | = |
| GET | `/health` | health check | 200 | 200 | = |
| GET | `/tasks` | listar | 200 | 200 | = |
| GET | `/tasks/1` | existente | 200 | 200 | = |
| GET | `/tasks/9999` | inexistente | 404 | 404 | = |
| POST | `/tasks` | criar | 201 | 201 | = |
| POST | `/tasks` | título curto | 400 | 400 | = |
| PUT | `/tasks/1` | atualizar | 200 | 200 | = |
| PUT | `/tasks/1` | prioridade inválida | 400 | 400 | = |
| GET | `/tasks/search?q=a` | busca texto | 200 | 200 | = |
| GET | `/tasks/search?status=pending` | busca status | 200 | 200 | = |
| GET | `/tasks/search?priority=abc` | prioridade não numérica | 500 | 400 | ≠ |
| GET | `/tasks/stats` | estatísticas | 200 | 200 | = |
| GET | `/users` | listar | 200 | 200 | = |
| GET | `/users/1` | existente | 200 | 200 | ≠ |
| GET | `/users/9999` | inexistente | 404 | 404 | = |
| POST | `/users` | criar | 201 | 201 | ≠ |
| POST | `/users` | e-mail duplicado | 409 | 409 | = |
| PUT | `/users/2` | atualizar | 200 | 200 | ≠ |
| GET | `/users/1/tasks` | tasks do usuário | 200 | 200 | = |
| POST | `/login` | credenciais válidas | 200 | 200 | ≠ |
| POST | `/login` | senha errada | 401 | 401 | = |
| GET | `/reports/summary` | resumo | 200 | 200 | = |
| GET | `/reports/user/1` | por usuário | 200 | 200 | = |
| GET | `/reports/user/9999` | inexistente | 404 | 404 | = |
| GET | `/categories` | listar | 200 | 200 | = |
| POST | `/categories` | criar | 201 | 201 | = |
| POST | `/categories` | sem nome | 400 | 400 | = |
| PUT | `/categories/1` | atualizar | 200 | 200 | = |
| PUT | `/categories/9999` | inexistente | 404 | 404 | = |
| DELETE | `/tasks/2` | deletar | 200 | 200 | = |
| DELETE | `/tasks/9999` | inexistente | 404 | 404 | = |
| DELETE | `/categories/5` | deletar | 200 | 200 | = |
| DELETE | `/users/3` | deletar | 200 | 200 | = |
| DELETE | `/users/9999` | inexistente | 404 | 404 | = |

</details>

### Observações sobre a skill em stacks diferentes

- **code-smells-project (monólito Flask):** a skill aplicou a estratégia de monólito — criou `src/` com as camadas essenciais e manteve `python app.py` como comando. Foi o projeto com mais findings críticos de segurança (SQL injection, senhas e rotas admin).
- **ecommerce-api-legacy (Node/Express):** o catálogo e o playbook funcionaram na stack JavaScript sem adaptação manual. A principal diferença foi o modelo assíncrono: a skill trocou o callback hell por `async/await` com uma função `transaction()`. O baseline mostrou um crash real do processo, que deixou de acontecer após a refatoração.
- **task-manager-api (Flask parcialmente organizado):** a skill evoluiu a estrutura no lugar, sem criar `src/`, adicionando só as camadas que faltavam e removendo `services/` e `utils/`, que eram código morto. Foi o único projeto com APIs deprecated, e os 31 warnings do original caíram para zero.

---

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado
- Python 3.12+ (projetos 1 e 3) e Node.js 18+ (projeto 2)

### Executar a skill em cada projeto

A skill deve rodar sobre o código **original**, preservado no commit `34653e8` (skill + projetos sem refatoração). Crie uma branch a partir dele e execute a skill em cada projeto. O argumento é o nome do relatório que a skill salva em `reports/`:

```bash
git checkout -b minha-execucao 34653e8
cd code-smells-project   && claude "/refactor-arch audit-project-1"
cd ../ecommerce-api-legacy && claude "/refactor-arch audit-project-2"
cd ../task-manager-api     && claude "/refactor-arch audit-project-3"
```

A skill imprime a análise (Fase 1) e o relatório (Fase 2) e para em `Proceed with refactoring (Phase 3)? [y/n]`. Com "y", salva o relatório, refatora e valida.

> Rodar a skill no `main` audita o código **já refatorado**. O relatório sai diferente dos que estão em `reports/`, e isso é esperado.

### Validar que a refatoração funcionou

No `main` (código refatorado), suba cada aplicação e chame um endpoint:

```bash
# code-smells-project
pip install -r requirements.txt && python app.py
curl http://127.0.0.1:5000/produtos

# ecommerce-api-legacy
npm install && npm start
curl -X POST http://localhost:3000/api/checkout -H "Content-Type: application/json" \
     -d '{"usr":"Ana","eml":"ana@x.com","pwd":"123","c_id":1,"card":"4111222233334444"}'

# task-manager-api
pip install -r requirements.txt && python seed.py && python app.py
curl http://127.0.0.1:5000/tasks
```

As variáveis de ambiente de cada projeto (por exemplo, `ADMIN_TOKEN` para as rotas administrativas) estão no README de cada um: [code-smells-project](code-smells-project/README.md), [ecommerce-api-legacy](ecommerce-api-legacy/README.md) e [task-manager-api](task-manager-api/README.md).
