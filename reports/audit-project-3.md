# Audit Report — task-manager-api (2026-09-26)

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1 / SQLAlchemy 2.0.54)
Files:   14 analyzed | ~1160 lines of code

## Summary
CRITICAL: 4 | HIGH: 2 | MEDIUM: 4 | LOW: 3

| #  | Severity | Anti-pattern                                   | Location |
|----|----------|------------------------------------------------|----------|
| 1  | CRITICAL | Credenciais e segredos hardcoded               | app.py:13, services/notification_service.py:9-10 |
| 2  | CRITICAL | Armazenamento inseguro de senhas (MD5)         | models/user.py:27-32 |
| 3  | CRITICAL | Exposição de dados sensíveis                   | models/user.py:21, routes/user_routes.py:33, 85, 129, 209 |
| 4  | CRITICAL | Token de autenticação falso                    | routes/user_routes.py:210 |
| 5  | HIGH     | Regra de negócio / acesso a dados nas rotas    | routes/task_routes.py:11-63, 85-154, 156-223; routes/report_routes.py:12-101; models/task.py:38-60 |
| 6  | HIGH     | Configuração insegura em runtime               | app.py:34, app.py:15, app.py:11 |
| 7  | MEDIUM   | Queries N+1                                    | routes/task_routes.py:41-57, routes/user_routes.py:22, routes/report_routes.py:55-56, 161-163 |
| 8  | MEDIUM   | Validação duplicada / ausente                  | routes/task_routes.py:92-114, 166-184, 113, 261, 264; routes/report_routes.py:196-197; utils/helpers.py:57-116 |
| 9  | MEDIUM   | Tratamento de erro genérico                    | routes/task_routes.py:62, 137, 236; routes/user_routes.py:130, 149; routes/report_routes.py:186, 207, 221 |
| 10 | MEDIUM   | APIs deprecated                                | models/task.py:15-16, 52 (+ 16 usos de Query.get e ~20 de utcnow) |
| 11 | LOW      | print no lugar de logging                      | routes/task_routes.py:149, 153, 219, 234; routes/user_routes.py:83, 89, 147; services/notification_service.py:21, 24; utils/helpers.py:39, 41 |
| 12 | LOW      | Magic numbers / strings de regra de negócio    | routes/task_routes.py:110, 113, 177, 182; routes/user_routes.py:71, 120; routes/report_routes.py:24-28, 129 |
| 13 | LOW      | Código morto                                   | services/notification_service.py:1-48, utils/helpers.py:1-116, app.py:7, routes/task_routes.py:7, routes/user_routes.py:6, routes/report_routes.py:7-8, models/task.py:3, requirements.txt:4-6 |

## Findings

### [CRITICAL] Credenciais e segredos hardcoded (AP-02)
File: app.py:13, services/notification_service.py:9-10
Description: `SECRET_KEY = 'supe****'` fixa em app.py; usuário e senha do SMTP (`email_password = 'senh****'`) escritos na classe NotificationService.
Impact: Quem tem acesso ao repositório tem a chave da aplicação e a senha da conta de e-mail; não há como trocar por ambiente.
Recommendation: `config/settings.py` lendo do ambiente (python-dotenv já está no requirements), chave efêmera em dev + `.env.example`; remover o serviço morto que guarda a senha SMTP (T-02).

### [CRITICAL] Armazenamento inseguro de senhas (AP-03)
File: models/user.py:27-32
Description: `set_password`/`check_password` usam `hashlib.md5(pwd.encode()).hexdigest()` — MD5 sem salt; o seed grava senhas como `'1234'` e `'abcd'` com esse hash.
Impact: Hashes MD5 sem salt são quebrados por rainbow table em segundos; senhas iguais geram hashes iguais.
Recommendation: `werkzeug.security.generate_password_hash`/`check_password_hash` (já vem com Flask) (T-03).

### [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models/user.py:21, routes/user_routes.py:33, routes/user_routes.py:85, routes/user_routes.py:129, routes/user_routes.py:209
Description: `User.to_dict()` inclui `'password'`, e esse dict é devolvido em `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e no `POST /login`.
Impact: Qualquer cliente obtém o hash MD5 de qualquer usuário (e, pelo AP-03, a senha em texto).
Recommendation: Serializer sem `password` em `User.to_dict()` (T-04).

### [CRITICAL] Token de autenticação falso (AP-05)
File: routes/user_routes.py:210
Description: O login devolve `'fake-jwt-token-' + str(user.id)` — um "token" previsível que qualquer um fabrica sabendo o id.
Impact: Qualquer cliente que venha a confiar nesse token aceita credenciais forjadas para qualquer usuário, inclusive admin.
Recommendation: Gerar token assinado com a `SECRET_KEY` (`itsdangerous`, dependência do Flask), mantendo o campo `token` na resposta (T-05).

### [HIGH] Regra de negócio / acesso a dados nas rotas (AP-07)
File: routes/task_routes.py:11-63, routes/task_routes.py:85-154, routes/task_routes.py:156-223, routes/report_routes.py:12-101, models/task.py:38-60
Description: As rotas fazem as queries e as regras (validação, lookup de usuário/categoria, parse de data, tags, estatísticas). A regra de atraso existe em `Task.is_overdue()` (models/task.py:50-60), mas é recopiada em 6 lugares (task_routes.py:30-39, 71-80, 283-287; user_routes.py:171-180; report_routes.py:33-37, 132-135); `validate_status`/`validate_priority` (models/task.py:38-48) nunca são usados.
Impact: Mudar a regra de atraso exige editar 6 trechos; rotas de 50–70 linhas impossíveis de testar sem HTTP.
Recommendation: Criar `controllers/` (task, user, report, category) com as regras e usar `Task.is_overdue()`; rotas finas; queries como métodos dos models (T-07, T-16).

### [HIGH] Configuração insegura em runtime (AP-10)
File: app.py:34, app.py:15, app.py:11
Description: `app.run(debug=True, host='0.0.0.0')` fixo, `CORS(app)` aberto para qualquer origem e URI do banco fixa no código.
Impact: O debugger do Werkzeug exposto na rede permite execução remota de código (qualquer 500 não tratado abre o console).
Recommendation: `FLASK_DEBUG` (default desligado), `HOST` (default 127.0.0.1), `PORT`, `DATABASE_URL`, `CORS_ORIGINS` do ambiente, via `create_app()` (T-02).

### [MEDIUM] Queries N+1 (AP-11)
File: routes/task_routes.py:41-57, routes/user_routes.py:22, routes/report_routes.py:55-56, routes/report_routes.py:161-163
Description: `GET /tasks` faz `User.query.get` e `Category.query.get` por task; `GET /users` carrega `u.tasks` (lazy) por usuário; o resumo faz uma query de tasks por usuário; `GET /categories` faz um `count()` por categoria.
Impact: `GET /tasks` faz 1 + 2·N queries; todas as listagens crescem linearmente com os dados.
Recommendation: `joinedload(Task.user, Task.category)` e agregações com `GROUP BY` nos models (T-10).

### [MEDIUM] Validação duplicada / ausente (AP-12)
File: routes/task_routes.py:92-114, routes/task_routes.py:166-184, routes/task_routes.py:113, routes/task_routes.py:261, routes/task_routes.py:264, routes/report_routes.py:196-197, utils/helpers.py:57-116
Description: O mesmo bloco de validação de task está copiado em criar e atualizar, enquanto `process_task_data` e as constantes `VALID_STATUSES`… de utils/helpers.py são ignorados. Sem checagem de tipo: `priority: "alta"` (task_routes.py:113), `?priority=abc` (261, 264) e `PUT /categories/<id>` sem body (report_routes.py:196-197) geram exceção não tratada → 500.
Impact: Entrada inválida vira 500 (com o debugger aberto, pelo AP-10); regras de criar/atualizar podem divergir.
Recommendation: Uma função de validação de task no controller, com as mesmas mensagens; checagem de tipos e de body (T-12).

### [MEDIUM] Tratamento de erro genérico (AP-13)
File: routes/task_routes.py:62, routes/task_routes.py:137, routes/task_routes.py:236, routes/user_routes.py:130, routes/user_routes.py:149, routes/report_routes.py:186, routes/report_routes.py:207, routes/report_routes.py:221
Description: `except:` nu em 8 pontos (engole até `KeyboardInterrupt`/`SystemExit`) e nenhum handler central — rotas sem `try` devolvem a página HTML de erro do Flask.
Impact: Erros são mascarados sem log, e o formato das respostas de erro varia (JSON `error` vs HTML).
Recommendation: Exceções de domínio + `errorhandler` central em `middlewares/error_handler.py` com JSON `{'error': ...}` e log do stack (T-11).

### [MEDIUM] APIs deprecated (AP-15)
File: models/task.py:15-16, models/task.py:52, models/category.py:11, models/user.py:14 (+ utcnow em routes/*, seed.py, services/, utils/; Query.get em routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227; routes/user_routes.py:29, 94, 136, 155; routes/report_routes.py:105, 192, 213)
Description: `datetime.utcnow()` está deprecated desde o Python 3.12, e `Model.query.get(id)` é API legada no SQLAlchemy 2.0 (emite `LegacyAPIWarning`).
Impact: Warnings em runtime hoje e quebra quando as APIs forem removidas.
Recommendation: Helper único `utc_now()` (datetime.now(timezone.utc) sem tzinfo, preservando o formato serializado) e `db.session.get(Model, id)` (T-15).

### [LOW] print no lugar de logging (AP-16)
File: routes/task_routes.py:149, routes/task_routes.py:153, routes/task_routes.py:219, routes/task_routes.py:234, routes/user_routes.py:83, routes/user_routes.py:89, routes/user_routes.py:147, services/notification_service.py:21, services/notification_service.py:24, utils/helpers.py:39, utils/helpers.py:41
Description: `print` espalhado nas rotas, incluindo `print(f"ERRO: {str(e)}")` sem stack trace.
Impact: Sem nível nem stack, erros de banco somem entre prints de sucesso; não dá para configurar em produção.
Recommendation: `logging.getLogger(__name__)` configurado em `create_app()` (T-13).

### [LOW] Magic numbers / strings de regra de negócio (AP-17)
File: routes/task_routes.py:110, routes/task_routes.py:113, routes/task_routes.py:177, routes/task_routes.py:182, routes/user_routes.py:71, routes/user_routes.py:120, routes/report_routes.py:24-28, routes/report_routes.py:129
Description: Lista de status e de roles repetida inline, faixa de prioridade `1..5`, rótulos de prioridade (p1..p5 → critical..minimal) e `priority <= 2` como "alta prioridade", enquanto as constantes de utils/helpers.py:110-116 existem e não são usadas.
Impact: As mesmas regras vivem em vários lugares e podem divergir (criar vs atualizar vs relatório).
Recommendation: `config/constants.py` com `TASK_STATUSES`, `USER_ROLES`, `PRIORITY_MIN/MAX`, `PRIORITY_LABELS`, `HIGH_PRIORITY_MAX` (T-14).

### [LOW] Código morto (AP-18)
File: services/notification_service.py:1-48, utils/helpers.py:1-116, app.py:7, routes/task_routes.py:7, routes/user_routes.py:6, routes/report_routes.py:7-8, models/task.py:3, requirements.txt:4-6
Description: `NotificationService` nunca é importado; de utils/helpers.py só `format_date` e `calculate_percentage` são importados — e nunca chamados; imports mortos (`os, sys, json, time, hashlib`); `marshmallow`, `requests` e `python-dotenv` declarados e não usados.
Impact: Código morto carrega a senha SMTP para o repositório e confunde sobre onde está a validação real.
Recommendation: Remover `services/` e `utils/` mortos e os imports; tirar `marshmallow` e `requests` do requirements; `python-dotenv` passa a ser usado pela config (limpeza da T-06).

## Notes
- Deprecated APIs: `datetime.utcnow` (Python 3.12) e `Query.get` (SQLAlchemy 2.0) — ver finding AP-15.
- SQL Injection: não encontrado — o ORM parametriza tudo (`.like(f'%{q}%')` do SQLAlchemy é parametrizado).
- Não reportado como AP-14: `DELETE /categories/<id>` não deixa tasks órfãs — o relacionamento `Category.tasks` (backref) faz o SQLAlchemy anular `category_id` das tasks na exclusão (confirmado executando a rota no baseline).
- Não reportado como AP-05: CRUD de tasks/users/categories sem auth — o projeto não tem modelo de autenticação aplicado a rotas (decisão de produto). Observação: `POST /users` aceita `role: "admin"` de qualquer cliente; hoje nenhuma rota usa o role.
- Pontos a preservar: blueprints por recurso, `Task.to_dict()`/`Category.to_dict()`, chave `error` nas respostas de erro, `python seed.py` + `python app.py`, porta 5000.

================================
Total: 13 findings
================================
```
