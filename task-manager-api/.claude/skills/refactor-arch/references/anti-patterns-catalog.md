# Referência — Catálogo de Anti-Patterns (Fase 2)

Cada entrada tem: **ID**, **severidade padrão**, o que é, **sinais de detecção** (padrões concretos e acionáveis, por stack), **quando NÃO reportar** e a transformação do playbook que o corrige (`T-xx` em `refactoring-playbook.md`).

> **Foco em impacto arquitetural.** O objetivo não é listar todo problema existente, e sim os que mais pesam em segurança, separação de camadas, consistência de dados e manutenção. Um sinal só vira finding quando a leitura do trecho confirma o problema **e** o impacto descrito na entrada. Na dúvida entre reportar um item de baixo impacto ou omiti-lo, omita — **exceto para completar a distribuição mínima de severidades exigida no `SKILL.md` (≥ 1 CRITICAL/HIGH, ≥ 2 MEDIUM, ≥ 2 LOW)**, usando sempre candidatos confirmados por leitura.

## Escala de severidade

- **CRITICAL** — falha grave de arquitetura ou segurança: quebra o funcionamento correto, expõe dados sensíveis (credenciais hardcoded, SQL Injection) ou viola completamente a separação de responsabilidades (God Class com banco + regras + rotas).
- **HIGH** — violação forte de MVC/SOLID que dificulta muito manutenção e testes: regra de negócio pesada em rotas/controllers, estado global mutável ou dependências concretas instanciadas por toda parte, operações sem transação.
- **MEDIUM** — padronização, duplicação ou performance moderada: N+1, validação ausente/duplicada, tratamento de erro inadequado, APIs deprecated com remoção anunciada.
- **LOW** — legibilidade: magic numbers, prints, código morto.

> Como usar: rode os greps a partir da raiz do projeto, excluindo `node_modules`, `.venv`, `.claude`. **Leia cada ocorrência** antes de registrar. Um grep sem leitura não é evidência.

## Índice

| ID | Anti-pattern | Severidade |
|----|--------------|-----------|
| AP-01 | SQL Injection (SQL montado por concatenação/interpolação) | CRITICAL |
| AP-02 | Credenciais e segredos hardcoded | CRITICAL |
| AP-03 | Armazenamento inseguro de senhas (texto plano, MD5/SHA1, "cripto caseira") | CRITICAL |
| AP-04 | Exposição de dados sensíveis (respostas, logs, health check) | CRITICAL |
| AP-05 | Endpoints perigosos sem autenticação/autorização | CRITICAL |
| AP-06 | God Class / God File | CRITICAL |
| AP-07 | Regra de negócio / acesso a dados na camada errada | HIGH |
| AP-08 | Estado global mutável e dependências concretas acopladas | HIGH |
| AP-09 | Operações multi-etapa sem transação / callback hell | HIGH |
| AP-10 | Configuração insegura em runtime (debug ligado, bind aberto, CORS irrestrito) | HIGH |
| AP-11 | Queries N+1 / consultas em loop | MEDIUM |
| AP-12 | Validação ausente ou duplicada | MEDIUM |
| AP-13 | Tratamento de erro genérico / vazamento / respostas de erro inconsistentes | MEDIUM |
| AP-14 | Integridade referencial ausente (delete sem cascade, órfãos) | MEDIUM |
| AP-15 | APIs deprecated / obsoletas | MEDIUM ou LOW |
| AP-16 | `print`/`console.log` no lugar de logging | LOW |
| AP-17 | Magic numbers / strings de regra de negócio | LOW |
| AP-18 | Código morto e nomes que enganam | LOW |

---

## AP-01 — SQL Injection · CRITICAL
**O que é**: SQL construído com dados externos via concatenação, f-string, `%`/`.format()` ou template literal.
**Sinais**:
```bash
grep -rnE "execute\((\"|')?[^)]*(\+|%|\.format\(|f\")" --include=*.py .
grep -rnE "(SELECT|INSERT|UPDATE|DELETE)[^\"']*[\"']\s*\+" -i .            # "... WHERE id = " + str(id)
grep -rnE "(query|run|all|get|exec)\(\`[^\`]*\\$\{" --include=*.js src     # template literal com ${} em SQL
grep -rnE "LIKE '%\"? ?\+" .                                                # LIKE montado por concatenação
```
**Não reportar quando**: placeholders (`?`, `%s`, `:nome`, `$1`) com parâmetros separados; ORM com filtros (`filter_by`, `.like(f'%{q}%')` do SQLAlchemy é parametrizado); a parte concatenada é um identificador fixo do código (nome de tabela constante), sem dado externo.
**Correção**: T-01.

## AP-02 — Credenciais e segredos hardcoded · CRITICAL
**O que é**: `SECRET_KEY`, senhas de banco/SMTP, chaves de API/gateway, tokens escritos no código.
**Sinais**:
```bash
grep -rniE "(secret|passw|pass|pwd|token|api[_-]?key|private[_-]?key|gateway|smtp).{0,20}[=:] *['\"][^'\"]{3,}" .
grep -rnE "pk_live_|sk_live_|AKIA[0-9A-Z]{16}|-----BEGIN" .
```
**Não reportar quando**: o valor vem de `os.environ`/`process.env`; é placeholder em `.env.example`; é texto de mensagem; é senha de **dados de seed de desenvolvimento** (isso é AP-03 se for gravada em texto plano, não AP-02).
**Correção**: T-02.

## AP-03 — Armazenamento inseguro de senhas · CRITICAL
**O que é**: senha salva em texto plano, com hash rápido sem salt (`md5`, `sha1`, `sha256` puro), base64 ou algoritmo caseiro; senha padrão fixa para usuários criados automaticamente; login comparando senha em SQL.
**Sinais**:
```bash
grep -rnE "hashlib\.(md5|sha1)|createHash\(['\"](md5|sha1)" .
grep -rnE "toString\(['\"]base64['\"]\)|btoa\(" .                     # "hash" que é só encoding
grep -rniE "senha *= *'|password *= *'|WHERE .*(senha|password) *=" .   # comparação de senha em SQL/texto plano
grep -rniE "(senha|password|pass|pwd)[^=]*\|\| *['\"]" .                 # senha default: p || "123456"
```
Leia também o INSERT de usuários e o seed: se a coluna de senha recebe o valor cru, é texto plano.
**Não reportar quando**: já usa `bcrypt`/`scrypt`/`argon2`/`pbkdf2`/`werkzeug.security` com salt.
**Correção**: T-03.

## AP-04 — Exposição de dados sensíveis · CRITICAL
**O que é**: senha/hash devolvido em JSON (`to_dict` com `password`, `SELECT *` de usuários serializado inteiro), segredo/config interna exposta (`/health` devolvendo `secret_key`, `debug`, caminho do banco), número de cartão ou chaves em logs.
**Sinais**:
```bash
grep -rnE "['\"](senha|password|pass|secret_key|token)['\"] *:" .       # chave sensível em dict/objeto de resposta
grep -rnE "(print|console\.log|logger\.\w+)\(.*(card|cartao|cc\b|senha|password|key|token)" -i .
```
Verifique o que cada serializer (`to_dict`, `toJSON`, dict literal de resposta) inclui.
**Não reportar quando**: o campo é um token de sessão devolvido de propósito no login; o log mostra apenas os últimos 4 dígitos ou um identificador não sensível.
**Correção**: T-04.

## AP-05 — Endpoints perigosos sem autenticação · CRITICAL
**O que é**: rotas administrativas ou destrutivas acessíveis a qualquer um: execução de SQL arbitrário, reset de banco, relatórios financeiros, exclusão em massa ou de usuários; "tokens" falsos/previsíveis (`'fake-jwt-token-' + id`).
**Sinais**:
```bash
grep -rniE "route\(.*(admin|reset|query|debug)|(get|post|delete)\(['\"]/.*(admin|reset|debug)" .
grep -rnE "execute\((query|sql|dados\.get|req\.body)" .                 # SQL vindo do cliente
grep -rniE "fake|token['\"]? *[:=] *['\"][^'\"]*['\"] *\+" .
```
Confirme a ausência de decorator/middleware de auth na rota.
**Não reportar quando**: o projeto inteiro não tem modelo de autenticação e a rota é um CRUD comum de recurso (ex.: `DELETE /tasks/<id>` de uma API sem usuários logados) — isso é decisão de produto, não falha a corrigir na refatoração. Reporte apenas rotas **administrativas/destrutivas em massa**, execução de SQL arbitrário e tokens falsos.
**Correção**: T-05 — proteger (guard de admin + restrição), **nunca remover** a rota do contrato; a recomendação do relatório deve dizer isso.

## AP-06 — God Class / God File · CRITICAL
**O que é**: uma unidade (arquivo, classe ou módulo) concentrando responsabilidades de camadas diferentes **e** de múltiplos domínios: conexão/schema/seed do banco + regras de negócio + roteamento HTTP + formatação.
**Sinais**:
- Arquivo com > ~250 linhas contendo SQL **e** regras de mais de um domínio (produtos, usuários, pedidos, relatórios...).
- Classe com métodos como `initDb` + `setupRoutes` + processamento de pagamento; "Manager"/"Utils"/"Helpers" que fazem de tudo.
- Imports de framework HTTP **e** driver de banco no mesmo arquivo, com handlers de mais de um recurso.
**Não reportar quando**: o arquivo é grande mas coeso (um único domínio e uma única camada).
**Correção**: T-06 (+ T-07).

## AP-07 — Regra de negócio / acesso a dados na camada errada · HIGH
**O que é**: route handlers / controllers com regras de domínio (cálculo de desconto, verificação de estoque, decisão de pagamento, cálculo de atraso) ou efeitos colaterais (e-mail/SMS/push) inline; funções de acesso a dados decidindo regras de negócio; controllers executando SQL/queries de ORM; métodos de domínio existentes mas **não usados** (lógica reimplementada na rota).
**Sinais**:
- Handler com mais de ~30 linhas ou mais de 2 níveis de `if` aninhados; `if/elif` com thresholds (`> 10000`, `* 0.1`).
- Rotas/controllers que chamam diretamente `db.session`, `cursor.execute`, `this.db.run`:
```bash
grep -rnE "execute\(|executemany\(|db\.session\.(get|execute|scalar|scalars|add|delete|query)\(|\.query\.|this\.db\.(run|get|all)\(|\b(SELECT|INSERT INTO|UPDATE|DELETE FROM|PRAGMA)\b" --include=*.py --include=*.js . | grep -E "/(controllers|routes|views|services)/"
```
- Método de domínio (ex.: `is_overdue()`) existente e a mesma lógica copiada em ≥ 2 handlers (`grep -rn "due_date <"`).
**Não reportar quando**: o controller só delimita transação (`with db:`, `commit()`/`rollback()`, `transaction(...)`) ou obtém a conexão para repassá-la ao model; o handler é longo apenas por montar um dict de resposta.
**Correção**: T-07; acesso a dados no controller → T-16.

## AP-08 — Estado global mutável e dependências concretas acopladas · HIGH
**O que é**: variáveis de módulo mutadas em runtime (caches, contadores, conexão única compartilhada entre threads com `check_same_thread=False`), `global` em funções, objetos exportados e alterados por vários módulos; classes de negócio que instanciam a própria conexão de banco ou client externo (`new sqlite3.Database(...)` no construtor), impedindo teste e troca de implementação.
**Sinais**:
```bash
grep -rnE "^\s*global |check_same_thread=False" --include=*.py .
grep -rnE "^(let|var) +\w+ *= *(\{\}|\[\]|0|null)" src                   # estado mutável de módulo em JS
grep -rnE "module\.exports *= *\{[^}]*(cache|state|total)" src
grep -rnE "new sqlite3\.Database\(|sqlite3\.connect\(|smtplib\.SMTP\(" .  # depois verifique se está dentro de classe/função de negócio
```
**Não reportar quando**: é uma constante imutável de módulo; é a instância única do ORM (`db = SQLAlchemy()`) inicializada na factory; é um `import` normal de função de acesso a dados (isso sozinho não é acoplamento a corrigir).
**Correção**: T-08.

## AP-09 — Operações multi-etapa sem transação / callback hell · HIGH
**O que é**: fluxos que gravam em várias tabelas (pedido + itens + estoque; matrícula + pagamento + auditoria) sem transação atômica — falha no meio deixa dados inconsistentes; callbacks aninhados (> 3 níveis) que impedem tratamento de erro e rollback.
**Sinais**: sequência de `INSERT/UPDATE` no mesmo fluxo sem `BEGIN/COMMIT/ROLLBACK`, `with conn:` ou `session.begin()`; `commit()` só no final sem `rollback()` em erro; pirâmide de callbacks `(err, x) => { ... (err, y) => { ...`.
**Não reportar quando**: a operação grava uma única tabela; o ORM já faz tudo em um único `commit()` com `rollback()` no `except`.
**Correção**: T-09.

## AP-10 — Configuração insegura em runtime · HIGH
**O que é**: `debug=True` / `DEBUG = True` fixo (o debugger do Werkzeug permite execução remota de código), bind `0.0.0.0` fixo, CORS liberado para qualquer origem sem configuração.
**Sinais**:
```bash
grep -rnE "debug *= *True|\[.DEBUG.\] *= *True|app\.run\(.*debug=True" .
grep -rnE "CORS\(app\)$|cors\(\)" .
```
**Não reportar quando**: o valor vem de variável de ambiente com default seguro (debug desligado).
**Correção**: T-02 (config por ambiente).

## AP-11 — Queries N+1 · MEDIUM
**O que é**: uma query para a lista e mais uma (ou mais) **por item**: `execute(...)` dentro de `for row in rows:`, `db.get(...)` dentro de `forEach(...)`, relacionamento lazy acessado em loop (`len(u.tasks)`, `User.query.get(t.user_id)` dentro do loop).
**Sinais**: leia todo loop sobre resultados de banco; `grep -rnE "for .* in .*:" -A6 | grep -E "execute|query|get\("`; em JS `forEach|map` contendo `db.`.
**Não reportar quando**: são algumas contagens fixas fora de loop (ex.: 5 `COUNT` independentes num relatório) — o custo não cresce com os dados; o loop percorre uma lista pequena e fixa (ex.: enum de status).
**Correção**: T-10.

## AP-12 — Validação ausente ou duplicada · MEDIUM
**O que é**: o mesmo bloco de validação copiado em ≥ 2 handlers (criar/atualizar); entrada usada sem checagem de tipo onde isso gera erro 500 (`preco < 0` com string; `int(request.args[...])` sem try); validadores/constantes existentes e ignorados.
**Sinais**: blocos `if "campo" not in dados` repetidos; listas de valores válidos repetidas; `grep -rn "def validate\|VALID_\|MAX_\|MIN_"` e verificar se são usados.
**Não reportar quando**: a validação existe em um único lugar e cobre o caso; a diferença é só de estilo.
**Correção**: T-12.

## AP-13 — Tratamento de erro genérico / vazamento / respostas inconsistentes · MEDIUM
**O que é**: `except:` nu, `except Exception as e: return str(e)` (vaza detalhes internos), erros de callback ignorados (`(err) => { ... }` sem usar `err`), `try/catch` copiado em todos os handlers em vez de um handler central; formatos de erro divergentes no mesmo projeto (texto vs JSON, `erro` vs `error`).
**Sinais**:
```bash
grep -rnE "except *:|except Exception" --include=*.py .
grep -rnE "str\(e\)|err\.message|error\.stack" .
grep -rnE "\(err(, *\w+)?\) *=> *\{" src   # depois verifique se err é tratado
```
**Não reportar quando**: há um handler central e os `try/except` restantes tratam casos específicos (ex.: rollback). Diferença de formato que faz parte do contrato existente e é consistente por rota não é finding.
**Correção**: T-11.

## AP-14 — Integridade referencial ausente · MEDIUM
**O que é**: exclusão de registro pai deixando filhos órfãos (usuário apagado com matrículas/pagamentos), deleção manual em loop sem transação.
**Sinais**: `DELETE FROM <pai>` sem tratar filhas; mensagens que admitem o problema; tabelas sem `FOREIGN KEY`/`ON DELETE` **e** rota que apaga o pai.
**Não reportar quando**: não existe rota/fluxo que apague o registro pai (FK ausente sem delete é observação, não finding).
**Correção**: T-09 (transação) + cascade explícito.

## AP-15 — APIs deprecated / obsoletas · MEDIUM (remoção anunciada ou warning em runtime) / LOW
Compare com as versões detectadas na Fase 1 e **recomende o equivalente moderno**:

| Stack | Uso obsoleto (sinal de grep) | Substituto moderno |
|-------|------------------------------|--------------------|
| Python ≥ 3.12 | `datetime.utcnow()` / `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)` / `datetime.fromtimestamp(ts, timezone.utc)` |
| SQLAlchemy 2.x / Flask-SQLAlchemy 3.x | `Model.query.get(id)` (`Query.get` legado) | `db.session.get(Model, id)` |
| Flask ≥ 2.3 | `@app.before_first_request`, `flask.json.JSONEncoder`, `app.json_encoder` | inicialização na factory; `app.json` provider |
| Python | `pkg_resources`, `distutils`, `imp`, `asyncio.get_event_loop()` fora de loop | `importlib.metadata`, `setuptools`, `importlib`, `asyncio.run` |
| Node.js | `new Buffer(x)` | `Buffer.from(x)` / `Buffer.alloc(n)` |
| Node.js | `url.parse()` | `new URL()` |
| Node.js | `crypto.createCipher()` | `crypto.createCipheriv()` |
| Node.js | `fs.exists()`, `util.isArray()` etc. | `fs.existsSync`/`fs.promises.access`, `Array.isArray` |
| Express 4 → 5 | `req.param()`, `res.send(status)`, `res.json(obj, status)`, `app.del()` | `req.params/query/body`, `res.sendStatus()`, `res.status().json()`, `app.delete()` |
| Express | `body-parser` separado | `express.json()` / `express.urlencoded()` |

**Sinais**: `grep -rnE "utcnow\(|\.query\.get\(|new Buffer\(|url\.parse\(|createCipher\(|bodyParser|req\.param\(" .` e rodar o app/seed observando `DeprecationWarning` no stderr (na Fase 3).
**Não reportar quando**: a API é apenas "legada/estilo antigo" mas não está deprecated na versão detectada (ex.: `Model.query.filter_by` no Flask-SQLAlchemy 3.x; callbacks do driver `sqlite3`).
Se nenhum uso deprecated for encontrado, declare no relatório: "Deprecated APIs: none detected".
**Correção**: T-15.

## AP-16 — print/console.log no lugar de logging · LOW
**Sinais**: `grep -rnE "^\s*print\(|console\.(log|error)\(" .`
**Não reportar quando**: está em scripts CLI (seed, migrations) ou é o banner de inicialização do servidor. Se o `print` vaza dado sensível, o finding é AP-04, não este.
**Correção**: T-13.

## AP-17 — Magic numbers / strings de regra de negócio · LOW
**O que é**: thresholds, percentuais, limites e listas de valores válidos (status, categorias, roles) **repetidos** inline ou que codificam uma regra de negócio (`> 10000`, `* 0.05`, `startsWith("4")`).
**Sinais**: literais numéricos em condições de regra de negócio; a mesma lista literal de valores válidos em ≥ 2 lugares; constantes definidas mas não usadas.
**Não reportar quando**: literal óbvio e único (`0`, `1`, códigos HTTP, porta padrão no entry point).
**Correção**: T-14.

## AP-18 — Código morto e nomes que enganam · LOW
**O que é**: imports/helpers/dependências nunca usados; nomes que mentem sobre o que o código faz (`badCrypto` como "hash", `AppManager` que faz tudo).
**Sinais**: para cada `import`/`require`, verifique uso (`grep -c nome arquivo`); helpers nunca chamados (`grep -rn "nome_funcao("` só encontra a definição); dependências do manifest nunca importadas.
**Não reportar quando**: é só abreviação/estilo de nome (`u`, `cid`) sem induzir a erro — renomear variáveis internas não é objetivo da auditoria.
**Correção**: remover/renomear na etapa de limpeza da Fase 3 (passo final da T-06).
