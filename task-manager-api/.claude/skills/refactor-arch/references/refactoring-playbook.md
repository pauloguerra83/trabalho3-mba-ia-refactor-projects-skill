# Referência — Playbook de Refatoração (Fase 3)

Padrões concretos de transformação, cada um com **antes/depois**. Os exemplos estão em Python/Flask e Node/Express; para outra stack, aplique a mesma ideia com os idiomas dela. O mapeamento finding → transformação está no catálogo (`AP-xx` → `T-xx`).

| T | Transformação | Corrige |
|---|---------------|---------|
| T-01 | SQL concatenado → queries parametrizadas | AP-01 |
| T-02 | Segredos/config hardcoded → módulo de config + env | AP-02, AP-10 |
| T-03 | Senha fraca/texto plano → hash forte com salt | AP-03 |
| T-04 | Dados sensíveis expostos → serializer seguro + logs mascarados | AP-04 |
| T-05 | Endpoint perigoso aberto → guard de admin | AP-05 |
| T-06 | God File/Class → módulos por camada e domínio | AP-06 |
| T-07 | Fat route → route fina + controller | AP-07, AP-18 |
| T-08 | Estado global / dependência instanciada → injeção via composition root | AP-08 |
| T-09 | Escritas multi-etapa → transação; callback hell → async/await | AP-09, AP-14 |
| T-10 | N+1 → JOIN / agregação / eager loading | AP-11 |
| T-11 | try/except em todo handler → exceções de domínio + handler central | AP-13 |
| T-12 | Validação duplicada → validators únicos | AP-12 |
| T-13 | print/console.log → logger | AP-16 |
| T-14 | Magic numbers → constantes nomeadas | AP-17 |
| T-15 | API deprecated → equivalente moderno | AP-15 |
| T-16 | Query (SQL/ORM) no controller → método do model | AP-07 (acesso a dados fora dos models) |

---

## T-01 — Queries parametrizadas

**Python (sqlite3) — antes**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query = "SELECT * FROM produtos WHERE 1=1"
if termo:
    query += " AND (nome LIKE '%" + termo + "%')"
```
**Depois**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))   # senha verificada por hash (T-03)

sql, params = "SELECT * FROM produtos WHERE 1=1", []
if termo:
    sql += " AND (nome LIKE ? OR descricao LIKE ?)"
    params += [f"%{termo}%", f"%{termo}%"]
cursor.execute(sql, params)
```
**Node (sqlite3) — antes / depois**
```js
db.get(`SELECT * FROM users WHERE email = '${email}'`, cb);        // antes
db.get("SELECT * FROM users WHERE email = ?", [email], cb);          // depois
```
Regra: **todo** valor externo vira parâmetro; só identificadores fixos do código podem compor a string SQL.

---

## T-02 — Config centralizada via ambiente

**Antes**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.run(host="0.0.0.0", port=5000, debug=True)
```
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_123...", port: 3000 };
```
**Depois — Python (`src/config/settings.py`)**
```python
import os, secrets, logging

def _bool(name, default=False):
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)   # dev: gerado em runtime
    DEBUG = _bool("FLASK_DEBUG", False)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", "loja.db")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")                         # None => rotas admin desabilitadas

if not os.getenv("SECRET_KEY"):
    logging.getLogger(__name__).warning("SECRET_KEY não definida; usando chave efêmera de desenvolvimento")
```
**Depois — Node (`src/config/index.js`)**
```js
const crypto = require('crypto');
module.exports = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',      // vazio em dev => gateway simulado
  adminToken: process.env.ADMIN_TOKEN || null,
  sessionSecret: process.env.SESSION_SECRET || crypto.randomBytes(32).toString('hex'),
});
```
E um `.env.example` listando as variáveis sem valores reais. Se o projeto já tem `python-dotenv`/`dotenv`, carregue o `.env` no composition root.

---

## T-03 — Hash de senha forte

**Antes**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()               # MD5 sem salt
cursor.execute("INSERT INTO usuarios (..., senha) VALUES (..., '" + senha + "')")   # texto plano
```
```js
function badCrypto(pwd) { /* base64 repetido e truncado */ }
let hash = badCrypto(p || "123456");                                  // senha default fixa
```
**Depois — Python** (werkzeug já vem com Flask)
```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, raw):  self.password = generate_password_hash(raw)
def check_password(self, raw): return check_password_hash(self.password, raw)
```
**Depois — Node** (stdlib `crypto`)
```js
const crypto = require('crypto');
function hashPassword(raw) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(raw, salt, 64).toString('hex');
  return `${salt}:${hash}`;
}
function verifyPassword(raw, stored) {
  const [salt, hash] = stored.split(':');
  const candidate = crypto.scryptSync(raw, salt, 64);
  return crypto.timingSafeEqual(candidate, Buffer.from(hash, 'hex'));
}
// senha ausente: gerar aleatória (crypto.randomBytes) em vez de default fixo — ou exigir o campo se o contrato permitir
```
Seeds também passam pelo hash. Login: buscar usuário por e-mail e verificar hash no código (nunca `WHERE senha = ?`).

---

## T-04 — Serializer seguro e logs mascarados

**Antes**
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password}
```
```python
return jsonify({"status": "ok", "secret_key": app.config["SECRET_KEY"], "debug": True, "db_path": "loja.db"})
```
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
**Depois**
```python
PUBLIC_FIELDS = ("id", "name", "email", "role", "active", "created_at")
def to_dict(self):
    return {"id": self.id, "name": self.name, "email": self.email, "role": self.role,
            "active": self.active, "created_at": str(self.created_at)}   # sem password
```
```python
return jsonify({"status": "ok", "database": "connected", "counts": counts, "versao": APP_VERSION})
```
```js
logger.info(`Processando pagamento cartão final ${card.slice(-4)}`);   // nunca a chave nem o PAN completo
```

---

## T-05 — Endpoint perigoso protegido

**Antes**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json()["sql"])          # SQL arbitrário, sem auth
```
**Depois — `middlewares/auth.py`**
```python
from functools import wraps
import hmac
from flask import request, current_app
from src.utils.errors import ForbiddenError

def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN")
        given = request.headers.get("X-Admin-Token", "")
        if not expected or not hmac.compare_digest(given, expected):
            raise ForbiddenError("Acesso administrativo não autorizado")
        return fn(*args, **kwargs)
    return wrapper
```
```python
@admin_bp.route("/admin/reset-db", methods=["POST"])
@require_admin
def reset_database():
    return jsonify(admin_controller.reset_database()), 200
```
- **Nunca remova a rota** (o desafio exige que os endpoints originais continuem respondendo): ela continua registrada e responde 403 sem token válido; com o token (`ADMIN_TOKEN` do ambiente) mantém o comportamento original.
- Rota de **SQL arbitrário**: além do guard, restrinja a um único `SELECT` executado em modo somente leitura (ex.: SQLite `PRAGMA query_only = ON` na conexão dessa requisição) — escrita arbitrária passa a ser recusada com 400. Documente em "Contract Changes".
- Express: `router.use(adminAuth(config.adminToken))` antes das rotas `/api/admin/*` e rotas destrutivas.
- "Token" falso (`'fake-jwt-token-' + id`): gere token assinado/aleatório com o segredo da config (ex.: `itsdangerous`/`hmac`), mantendo o campo `token` na resposta.

---

## T-06 — God File/Class → módulos por camada e domínio

**Antes** (`models.py`, 300+ linhas, 4 domínios; ou `AppManager` com `initDb` + `setupRoutes` + pagamento)
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE + seed */ }
  setupRoutes(app) { app.post('/api/checkout', (req, res) => { /* 50 linhas: SQL + pagamento + auditoria */ }); }
}
```
**Depois** — um arquivo por responsabilidade:
```
database/connection.js   -> abre a conexão, expõe run/get/all/transaction (Promise)
database/schema.js       -> initSchema(db) + seed(db)
models/courseModel.js    -> findActiveById(id)
models/userModel.js      -> findByEmail(email), create(user), deleteWithDependents(id)
services/paymentService.js -> authorize(card, amount)
controllers/checkoutController.js -> checkout({ name, email, password, courseId, card })
routes/checkoutRoutes.js -> router.post('/api/checkout', ...)
app.js                   -> composition root
```
Procedimento: (1) crie os novos módulos copiando a lógica e já aplicando T-01/T-03/T-09; (2) aponte o entry point para eles; (3) valide; (4) **apague o arquivo antigo**.

---

## T-07 — Route fina + controller

**Antes (Flask)**
```python
@task_bp.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data: return jsonify({'error': 'Dados inválidos'}), 400
    # 60 linhas: validação, lookup de user/categoria, parse de data, tags, commit, print
```
**Depois**
```python
# routes/task_routes.py (view)
@task_bp.route('/tasks', methods=['POST'])
def create_task():
    task = task_controller.create_task(request.get_json(silent=True))
    return jsonify(task), 201

# controllers/task_controller.py
def create_task(data):
    payload = validate_task_payload(data, partial=False)      # lança ValidationError (400)
    ensure_user_exists(payload.get("user_id"))                # lança NotFoundError (404)
    ensure_category_exists(payload.get("category_id"))
    task = Task(**payload)
    db.session.add(task); db.session.commit()
    logger.info("Task criada: %s", task.id)
    return task.to_dict()
```
**Express**
```js
// routes/checkoutRoutes.js
router.post('/api/checkout', async (req, res, next) => {
  try {
    const { usr, eml, pwd, c_id, card } = req.body;           // contrato preservado
    const result = await checkoutController.checkout({ name: usr, email: eml, password: pwd, courseId: c_id, card });
    res.status(200).json(result);
  } catch (err) { next(err); }                                // erro vai para o handler central
});
```
Efeitos colaterais (e-mail/SMS/push) saem do handler e vão para o controller; só vire `services/notification_service` se forem reutilizados por mais de um controller ou envolverem integração externa real.

---

## T-08 — Injeção de dependência e fim do estado global

**Antes**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
    return db_connection
```
```js
let globalCache = {}; let totalRevenue = 0;
module.exports = { globalCache, totalRevenue, logAndCache };
```
**Depois — Flask: conexão por request**
```python
from flask import g, current_app
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
```
**Depois — Node: a conexão é criada no entry point e passada adiante (sem estado de módulo)**
```js
// app.js
const db = openDatabase(config.dbPath);        // uma conexão, criada aqui
initSchema(db);
const app = express();
app.use(express.json());
app.use(checkoutRoutes(db));                   // rotas/controllers recebem db por parâmetro
app.use(errorHandler);
app.listen(config.port);
```
Estado global que só servia de "cache" sem leitor (ex.: `globalCache` gravado e nunca lido) é **removido**, não transformado em `CacheService`. Não introduza classes, containers de DI ou factories só para injetar uma dependência: um parâmetro de função basta.

---

## T-09 — Transação e async/await

**Antes (Python)**
```python
cursor.execute("INSERT INTO pedidos ...")
for item in itens:
    cursor.execute("INSERT INTO itens_pedido ...")
    cursor.execute("UPDATE produtos SET estoque = estoque - ...")
db.commit()                                  # falha no meio => estado parcial; sem rollback
```
**Depois**
```python
try:
    with db:                                 # sqlite3: commit no sucesso, rollback em exceção
        pedido_id = pedido_model.inserir(db, usuario_id, total)
        for item in itens:
            pedido_model.inserir_item(db, pedido_id, item)
            produto_model.baixar_estoque(db, item["produto_id"], item["quantidade"])
except sqlite3.Error:
    logger.exception("Falha ao criar pedido")
    raise
```
SQLAlchemy: `db.session.add(...)`; `db.session.commit()` dentro de `try` com `db.session.rollback()` no `except`.

**Antes (Node, callback hell sem transação)**
```js
db.run("INSERT INTO enrollments ...", [u, c], function (err) {
  db.run("INSERT INTO payments ...", [this.lastID, ...], function (err) {
    db.run("INSERT INTO audit_logs ...", [...], (err) => res.json(...));
  });
});
```
**Depois**
```js
// database/connection.js
const run = (sql, p = []) => new Promise((ok, fail) => db.run(sql, p, function (e) { e ? fail(e) : ok({ lastID: this.lastID, changes: this.changes }); }));
async function transaction(work) {
  await run('BEGIN');
  try { const r = await work(); await run('COMMIT'); return r; }
  catch (e) { await run('ROLLBACK'); throw e; }
}
// controllers/checkoutController.js
return transaction(async () => {
  const { lastID: enrollmentId } = await enrollments.create(userId, course.id);
  await payments.create(enrollmentId, course.price, PAYMENT_STATUS.PAID);
  await audit.log(`Checkout curso ${course.id} por ${userId}`);
  return { msg: 'Sucesso', enrollment_id: enrollmentId };
});
```
Deleção com dependentes (AP-14): apagar filhos e pai dentro da mesma transação, ou `ON DELETE CASCADE`/`cascade="all, delete-orphan"` no ORM.

---

## T-10 — Eliminar N+1

**Antes**
```python
for row in pedidos:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in cursor2.fetchall():
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
**Depois — uma query com JOIN e agrupamento em memória**
```python
rows = db.execute("""
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr   ON pr.id = i.produto_id
    WHERE (? IS NULL OR p.usuario_id = ?)
    ORDER BY p.id""", (usuario_id, usuario_id)).fetchall()
pedidos = {}
for r in rows:
    pedido = pedidos.setdefault(r["id"], {...campos do pedido..., "itens": []})
    if r["produto_id"] is not None:
        pedido["itens"].append({"produto_id": r["produto_id"], "produto_nome": r["produto_nome"] or "Desconhecido", ...})
return list(pedidos.values())
```
**SQLAlchemy**: `db.session.execute(db.select(Task).options(joinedload(Task.user), joinedload(Task.category))).scalars().all()`; contagens com `db.session.query(Task.status, func.count()).group_by(Task.status)`.
**Node**: um `SELECT ... JOIN ...` + `reduce` para montar a estrutura, no lugar de `forEach` com `db.get` aninhado.

---

## T-11 — Erros de domínio + handler central

**Antes**
```python
def buscar_produto(id):
    try:
        ...
    except Exception as e:
        return jsonify({"erro": str(e)}), 500          # repetido em 20 handlers; vaza detalhes
```
**Depois**
```python
# utils/errors.py
class AppError(Exception):
    status_code = 500
    def __init__(self, message, status_code=None):
        super().__init__(message); self.message = message
        if status_code: self.status_code = status_code
class ValidationError(AppError): status_code = 400
class NotFoundError(AppError): status_code = 404
# crie outras (403, 409...) só se o código realmente as lançar

# middlewares/error_handler.py
def register_error_handlers(app, error_key="erro"):       # mantém a chave que o contrato já usa
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({error_key: err.message, "sucesso": False}), err.status_code
    @app.errorhandler(404)
    def not_found(_): return jsonify({error_key: "Recurso não encontrado"}), 404
    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception("Erro não tratado")
        return jsonify({error_key: "Erro interno do servidor"}), 500
```
**Express**
```js
// Express 4: em handlers async, faça try/catch e chame next(err) — ou use um helper de 1 linha
// se houver muitos handlers async (não crie arquivo só para ele).
function errorHandler(err, req, res, _next) {
  if (err instanceof AppError) return res.status(err.statusCode).send(err.message);   // preserve o formato original (texto ou JSON)
  console.error(err);
  res.status(500).send('Erro interno');
}
app.use(errorHandler);   // último middleware
```

---

## T-12 — Validators únicos

**Antes** (mesmo bloco em `criar_produto` e `atualizar_produto`)
```python
if "nome" not in dados: return jsonify({"erro": "Nome é obrigatório"}), 400
if dados["preco"] < 0:  return jsonify({"erro": "Preço não pode ser negativo"}), 400
```
**Depois**
```python
# utils/validators.py
def validar_produto(dados):
    if not isinstance(dados, dict): raise ValidationError("Dados inválidos")
    for campo, msg in (("nome", "Nome é obrigatório"), ("preco", "Preço é obrigatório"), ("estoque", "Estoque é obrigatório")):
        if campo not in dados: raise ValidationError(msg)
    if not isinstance(dados["preco"], (int, float)) or dados["preco"] < 0: raise ValidationError("Preço não pode ser negativo")
    ...
    return {"nome": dados["nome"].strip(), ...}
```
Mantenha as **mesmas mensagens e a mesma ordem de checagem** do original para não mudar o contrato.

---

## T-13 — Logging

```python
print("ERRO ao criar produto: " + str(e))                 # antes
logger = logging.getLogger(__name__)                       # depois
logger.exception("Erro ao criar produto")
```
```js
console.log(`[LOG] Salvando no cache: ${key}`);            // antes
console.debug(`cache set: ${key}`);                        // depois: console com nível, sem wrapper próprio
```
Configure o logging uma vez no composition root (`logging.basicConfig(level=settings.LOG_LEVEL)`). Não crie `utils/logger` só para repassar `logging.getLogger`/`console`.

---

## T-14 — Constantes nomeadas

**Antes**
```python
if faturamento > 10000: desconto = faturamento * 0.1
elif faturamento > 5000: desconto = faturamento * 0.05
if novo_status not in ["pendente", "aprovado", "enviado", "entregue", "cancelado"]: ...
```
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";
```
**Depois**
```python
# config/constants.py
STATUS_PEDIDO = ("pendente", "aprovado", "enviado", "entregue", "cancelado")
FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))   # (faturamento mínimo exclusivo, percentual)

def calcular_desconto(faturamento):
    for minimo, pct in FAIXAS_DESCONTO:
        if faturamento > minimo:
            return faturamento * pct
    return 0
```
```js
// config/constants.js
const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });
const APPROVED_CARD_PREFIX = '4';   // regra do gateway simulado
```

---

## T-15 — APIs deprecated

```python
datetime.utcnow()                          # antes (deprecated no Python 3.12)
datetime.now(timezone.utc)                 # depois

Task.query.get(task_id)                    # antes (Query.get legado no SQLAlchemy 2.x)
db.session.get(Task, task_id)              # depois
```
```js
new Buffer(pwd)                            // antes
Buffer.from(pwd)                           // depois
app.use(bodyParser.json())                 // antes
app.use(express.json())                    // depois
```
Atenção com `utcnow()` → `now(timezone.utc)`: datetimes *aware* não comparam com *naive* vindos do banco. Em colunas SQLite/SQLAlchemy sem timezone, use um helper único `utc_now()` que retorna `datetime.now(timezone.utc).replace(tzinfo=None)` e use-o em defaults de coluna, comparações e seeds — preservando o formato já serializado nas respostas.

---

## T-16 — Query no controller → método do model

Regra: o controller **nunca** executa SQL nem monta query de ORM; ele chama uma função/método do model e, no máximo, delimita a transação. Isso vale também para controllers "técnicos" (admin, health).

**Antes (sqlite3)**
```python
# controllers/admin_controller.py
def reset_database():
    db = get_db()
    with db:
        db.execute("DELETE FROM itens_pedido")
        db.execute("DELETE FROM pedidos")

# controllers/meta_controller.py
def health():
    db = get_db()
    db.execute("SELECT 1")
```
**Depois**
```python
# models/admin_model.py
TABELAS_RESET = ("itens_pedido", "pedidos", "produtos", "usuarios")   # ordem respeita as FKs

def limpar_tabelas(db):
    for tabela in TABELAS_RESET:                   # nomes fixos do código, não vêm do cliente
        db.execute(f"DELETE FROM {tabela}")

def ping(db):
    db.execute("SELECT 1")

# controllers/admin_controller.py
def reset_database():
    db = get_db()
    with db:                                       # controller só delimita a transação
        admin_model.limpar_tabelas(db)
```

**Antes (SQLAlchemy)**
```python
# controllers/task_controller.py
task = db.session.get(Task, task_id)
tasks = db.session.execute(db.select(Task).where(Task.user_id == user_id)).scalars().all()
db.session.add(task); db.session.commit()
```
**Depois**
```python
# models/task.py
class Task(db.Model):
    ...
    @classmethod
    def get_by_id(cls, task_id):
        return db.session.get(cls, task_id)

    @classmethod
    def list_by_user(cls, user_id):
        return db.session.execute(db.select(cls).where(cls.user_id == user_id)).scalars().all()

    def save(self):
        db.session.add(self)

    def remove(self):
        db.session.delete(self)

# controllers/task_controller.py
task = Task.get_by_id(task_id)
tasks = Task.list_by_user(user_id)
try:
    task.save()
    db.session.commit()                            # permitido: limite da transação
except SQLAlchemyError:
    db.session.rollback()
    raise
```
Node/Express: o controller chama `userModel.findByEmail(...)` e usa `db.transaction(async () => ...)`; nunca `this.db.run/get/all`.
Mova as queries **sem alterar** o SQL/ORM nem o resultado (mesma ordenação, mesmos campos): é uma mudança de camada, não de comportamento.
