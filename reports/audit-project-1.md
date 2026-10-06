# Audit Report — code-smells-project (2026-09-26)

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 6 | HIGH: 4 | MEDIUM: 3 | LOW: 3

| #  | Severity | Anti-pattern                              | Location |
|----|----------|-------------------------------------------|----------|
| 1  | CRITICAL | SQL Injection                             | models.py:28, 47-50, 57-61, 109-111, 126-129, 289-297 (+ others) |
| 2  | CRITICAL | Credenciais e segredos hardcoded          | app.py:7, controllers.py:289 |
| 3  | CRITICAL | Senhas em texto plano                     | models.py:109-111, models.py:126-129, database.py:75-83 |
| 4  | CRITICAL | Exposição de dados sensíveis              | models.py:83, models.py:99, controllers.py:285-289 |
| 5  | CRITICAL | Endpoints perigosos sem autenticação      | app.py:47-57, app.py:59-78 |
| 6  | CRITICAL | God File                                  | models.py:1-314 |
| 7  | HIGH     | Regra de negócio/acesso a dados na camada errada | models.py:139-146, models.py:256-262, controllers.py:208-210, controllers.py:247-250, controllers.py:266-274, app.py:49-55, app.py:66-76 |
| 8  | HIGH     | Estado global mutável                     | database.py:4-10 |
| 9  | HIGH     | Operação multi-etapa sem transação        | models.py:148-168 |
| 10 | HIGH     | Configuração insegura em runtime          | app.py:8, app.py:9, app.py:88 |
| 11 | MEDIUM   | Queries N+1                               | models.py:187-199, models.py:219-231 |
| 12 | MEDIUM   | Validação ausente ou duplicada            | controllers.py:28-50, controllers.py:72-90, controllers.py:169-170, controllers.py:239-240 |
| 13 | MEDIUM   | Tratamento de erro genérico com vazamento | controllers.py:10-12, 21-22, 60-62, ... 291-292; app.py:77-78 |
| 14 | LOW      | print no lugar de logging                 | controllers.py:8, 161, 179, 182, 208-210, ...; app.py:56 |
| 15 | LOW      | Magic numbers / strings de regra de negócio | controllers.py:52, controllers.py:242, models.py:256-262 |
| 16 | LOW      | Código morto e nomes que enganam          | database.py:2, models.py:2, controllers.py:286 |

## Findings

### [CRITICAL] SQL Injection (AP-01)
File: models.py:28, models.py:47-50, models.py:57-61, models.py:68, models.py:92, models.py:109-111, models.py:126-129, models.py:140, models.py:149-151, models.py:155-166, models.py:174, models.py:188, models.py:192, models.py:220, models.py:224, models.py:280, models.py:289-297
Description: Todas as queries com dados externos são montadas por concatenação (ex.: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`; busca com `LIKE '%" + termo + "%'`). No `POST /login`, `email = "' OR '1'='1' --"` autentica sem senha; em `POST /produtos` um `nome` com aspas quebra ou altera o INSERT.
Impact: Bypass de autenticação e leitura/alteração arbitrária do banco por qualquer cliente anônimo.
Recommendation: Queries parametrizadas (`?`) em todas as funções de acesso a dados, concentradas em `src/models/*_model.py` (T-01).

### [CRITICAL] Credenciais e segredos hardcoded (AP-02)
File: app.py:7, controllers.py:289
Description: `SECRET_KEY = "minh****"` fixa no código e repetida literalmente na resposta do health check.
Impact: Qualquer pessoa com acesso ao repositório (ou ao `/health`) conhece a chave de assinatura da aplicação; impossível trocar por ambiente sem editar código.
Recommendation: `src/config/settings.py` lendo `SECRET_KEY` do ambiente, com chave efêmera gerada em runtime para dev + `.env.example` (T-02).

### [CRITICAL] Armazenamento inseguro de senhas (AP-03)
File: models.py:109-111, models.py:126-129, database.py:75-83
Description: Senhas gravadas em texto plano no INSERT e no seed (`"admin123"`, `"123456"`), e o login compara `WHERE ... senha = '<senha>'` direto no SQL.
Impact: Vazamento do banco (ou da rota `/admin/query`) expõe todas as senhas reais dos usuários.
Recommendation: `werkzeug.security.generate_password_hash`/`check_password_hash` (já vem com Flask) no cadastro e no seed; login busca por e-mail e verifica o hash no código (T-03).

### [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models.py:83, models.py:99, controllers.py:285-289
Description: `GET /usuarios` e `GET /usuarios/<id>` serializam o campo `senha`; `GET /health` devolve `secret_key`, `debug: True` e `db_path`.
Impact: Qualquer cliente anônimo obtém as senhas de todos os usuários (incluindo admin) e a chave secreta da aplicação.
Recommendation: Serializer de usuário sem `senha`; health check só com status/contagens/versão (T-04). Mudança de contrato por segurança.

### [CRITICAL] Endpoints perigosos sem autenticação (AP-05)
File: app.py:47-57, app.py:59-78
Description: `POST /admin/reset-db` apaga todas as tabelas e `POST /admin/query` executa SQL arbitrário vindo do body (`cursor.execute(query)`), ambos sem nenhuma autenticação.
Impact: Qualquer cliente pode destruir ou exfiltrar todo o banco com uma requisição.
Recommendation: **Manter as rotas** e protegê-las com guard de admin (`X-Admin-Token` comparado com `ADMIN_TOKEN` do ambiente; sem token configurado → 403); `/admin/query` restrita a um único SELECT em modo somente leitura (T-05).

### [CRITICAL] God File (AP-06)
File: models.py:1-314
Description: Um único arquivo de 314 linhas com SQL e regras de negócio de 4 domínios (produtos, usuários, pedidos com baixa de estoque, relatório com cálculo de desconto). database.py mistura conexão global, schema e seed.
Impact: Qualquer mudança em um domínio mexe no mesmo arquivo; impossível testar regras sem banco; alto acoplamento.
Recommendation: Separar em `src/models/{produto,usuario,pedido,sistema}_model.py` e `src/database/{connection,schema}.py` (T-06).

### [HIGH] Regra de negócio / acesso a dados na camada errada (AP-07)
File: models.py:139-146, models.py:256-262, controllers.py:208-210, controllers.py:247-250, controllers.py:266-274, app.py:49-55, app.py:66-76
Description: Checagem de estoque e cálculo de desconto (`> 10000` → `* 0.1`) dentro das funções de acesso a dados; notificações (e-mail/SMS/push) inline nos handlers; health check e rotas admin executando SQL diretamente no controller/rota.
Impact: Regras de negócio não testáveis isoladamente; camadas sem fronteira clara.
Recommendation: Regras em `src/controllers/*_controller.py`, SQL só nos models, rotas finas em `src/views/` (T-07, T-16).

### [HIGH] Estado global mutável (AP-08)
File: database.py:4-10
Description: Conexão SQLite única em variável de módulo (`global db_connection`) compartilhada entre threads com `check_same_thread=False`.
Impact: Condições de corrida entre requisições concorrentes e transações misturadas entre requests; impossível injetar outro banco em testes.
Recommendation: Conexão por request via `flask.g` + `teardown_appcontext`, caminho do banco vindo da config (T-08).

### [HIGH] Operação multi-etapa sem transação (AP-09)
File: models.py:148-168
Description: `criar_pedido` insere o pedido, os itens e baixa o estoque em várias tabelas com um único `commit()` no final e nenhum `rollback()` em erro (ex.: item sem `quantidade` gera KeyError no meio do loop).
Impact: Falha no meio deixa escritas parciais pendentes na conexão compartilhada, que são commitadas pela próxima requisição → pedidos sem itens / estoque inconsistente.
Recommendation: Envolver o caso de uso em `with db:` (commit/rollback automático) no controller (T-09).

### [HIGH] Configuração insegura em runtime (AP-10)
File: app.py:8, app.py:9, app.py:88
Description: `DEBUG = True` e `app.run(host="0.0.0.0", ..., debug=True)` fixos; `CORS(app)` libera qualquer origem.
Impact: O debugger do Werkzeug exposto na rede permite execução remota de código.
Recommendation: `FLASK_DEBUG` (default desligado), `HOST` (default 127.0.0.1), `PORT` e `CORS_ORIGINS` vindos do ambiente (T-02).

### [MEDIUM] Queries N+1 (AP-11)
File: models.py:187-199, models.py:219-231
Description: Para cada pedido, uma query de itens; para cada item, uma query do nome do produto (duplicado em `get_pedidos_usuario` e `get_todos_pedidos`).
Impact: `GET /pedidos` faz 1 + P + I queries — cresce linearmente com o volume de vendas.
Recommendation: Uma query com LEFT JOIN + agrupamento em memória, compartilhada pelas duas listagens (T-10).

### [MEDIUM] Validação ausente ou duplicada (AP-12)
File: controllers.py:28-50, controllers.py:72-90, controllers.py:169-170, controllers.py:239-240
Description: Bloco de validação de produto copiado em criar/atualizar (e o update não valida nome/categoria); `preco` string gera TypeError → 500; `login` e `atualizar_status_pedido` chamam `dados.get` sem checar body nulo → 500.
Impact: Entrada inválida vira erro 500 em vez de 400; regras divergem entre criar e atualizar.
Recommendation: Uma única função de validação de produto no controller, mantendo mensagens e ordem; checagem de body nulo/tipos (T-12).

### [MEDIUM] Tratamento de erro genérico / vazamento (AP-13)
File: controllers.py:10-12, controllers.py:21-22, controllers.py:60-62, controllers.py:95-96, controllers.py:108-109, controllers.py:125-126, controllers.py:133-134, controllers.py:143-144, controllers.py:164-165, controllers.py:185-186, controllers.py:218-220, controllers.py:226-227, controllers.py:234-235, controllers.py:254-255, controllers.py:261-262, controllers.py:291-292, app.py:77-78
Description: `try/except Exception as e: return jsonify({"erro": str(e)}), 500` copiado em todos os handlers.
Impact: Mensagens internas do SQLite/Python vazam ao cliente (facilita exploração da injeção); código repetido em 17 lugares.
Recommendation: Exceções de domínio (`ValidationError`, `NotFoundError`, `ForbiddenError`) + handler central com 500 genérico e log do stack, mantendo a chave `erro` (T-11).

### [LOW] print/console.log no lugar de logging (AP-16)
File: controllers.py:8, controllers.py:11, controllers.py:57, controllers.py:61, controllers.py:106, controllers.py:161, controllers.py:179, controllers.py:182, controllers.py:208-210, controllers.py:219, controllers.py:248, controllers.py:250, app.py:56
Description: 15 `print(...)` espalhados pelos handlers, inclusive com o e-mail do usuário (`"Login falhou: " + email`, `"Usuário criado: " + email`) e as "notificações" simuladas de e-mail/SMS/push.
Impact: Sem nível, timestamp nem destino configurável; não dá para silenciar em produção nem filtrar erros, e dados pessoais (e-mail) vão parar no stdout em toda tentativa de login.
Recommendation: `logging.getLogger(__name__)` configurado uma vez em `create_app()`, sem e-mail nos logs (T-13).

### [LOW] Magic numbers / strings de regra de negócio (AP-17)
File: controllers.py:52, controllers.py:242, models.py:256-262
Description: Lista de categorias válidas inline em `criar_produto`, lista de status de pedido inline em `atualizar_status_pedido`, e faixas de desconto `> 10000 → 0.1`, `> 5000 → 0.05`, `> 1000 → 0.02` codificadas na query do relatório.
Impact: As regras não estão num lugar só. Por exemplo, `atualizar_produto` não usa a lista de categorias e aceita qualquer categoria, e mudar a política de desconto exige mexer na camada de dados.
Recommendation: `CATEGORIAS_VALIDAS`, `STATUS_PEDIDO` e `FAIXAS_DESCONTO` em `src/config/constants.py`, usadas pelos controllers (T-14).

### [LOW] Código morto e nomes que enganam (AP-18)
File: database.py:2, models.py:2, controllers.py:286
Description: `import os` (database.py) e `import sqlite3` (models.py) nunca são usados; `/health` declara `"ambiente": "producao"` fixo enquanto a app roda com `debug=True`.
Impact: Imports mortos poluem o módulo, e o campo `ambiente` mente para quem monitora o serviço (reporta produção em um servidor de debug).
Recommendation: Remover os imports na reescrita dos módulos; derivar `ambiente` da config (`FLASK_DEBUG` → `desenvolvimento`/`producao`) (remoção/renomeação na limpeza da T-06).

## Notes
- Deprecated APIs: none detected (Flask 3.1.1 / Python 3.12 — sem `utcnow`, `before_first_request`, `json_encoder`).
- Outros pontos menores, fora do escopo como findings próprios: `DELETE /produtos/<id>` deixa itens_pedido órfãos (models.py:68, sem FK) — AP-14; cancelar pedido não devolve estoque (controllers.py:249-250 só imprime).
- `GET /relatorios/vendas` expõe faturamento sem auth, mas o projeto não tem modelo de autenticação de usuário; recomendação apenas documentada.
- Pontos a preservar: rotas já separadas de handlers via `add_url_rule`; nomes de campos e formato `{"dados", "sucesso"}` consistentes.

================================
Total: 16 findings
================================
```
