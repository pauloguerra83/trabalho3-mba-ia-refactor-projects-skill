# Referência — Análise de Projeto (Fase 1)

Heurísticas para detectar linguagem, framework, banco de dados, domínio, arquitetura, endpoints e forma de execução de **qualquer** projeto backend. Sempre combine pelo menos duas evidências (manifest + código) antes de concluir.

---

## 1. Inventário de arquivos

```bash
# arquivos-fonte (ajuste extensões à linguagem detectada), ignorando vendor/artefatos
find . -type f \( -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.go' -o -name '*.java' -o -name '*.rb' -o -name '*.php' -o -name '*.cs' \) \
  -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/venv/*' -not -path '*/.git/*' \
  -not -path '*/.claude/*' -not -path '*/__pycache__/*' -not -path '*/dist/*' -not -path '*/build/*' | sort
# linhas por arquivo e total
... | xargs wc -l
```

- Conte **somente código-fonte da aplicação** (inclua scripts como `seed.py`; exclua testes gerados, migrations automáticas e arquivos vazios `__init__.py` do total de "files analyzed" se não tiverem conteúdo — mas cite-os na estrutura).
- Arquivos auxiliares relevantes: `README*`, `.env*`, `api.http`/`*.http`/coleções Postman (ótimos para exemplos de payload), `Dockerfile`, `Procfile`.

## 2. Linguagem (manifests e extensões)

| Evidência | Linguagem |
|-----------|-----------|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, maioria `*.py` | Python |
| `package.json` (+ `*.js`) / `tsconfig.json` (+ `*.ts`) | JavaScript (Node.js) / TypeScript |
| `go.mod` | Go |
| `pom.xml`, `build.gradle(.kts)` | Java / Kotlin |
| `composer.json` | PHP |
| `Gemfile` | Ruby |
| `*.csproj`, `*.sln` | C# (.NET) |

Versão do runtime: `.python-version`, `runtime.txt`, `engines` do `package.json`, `.nvmrc`, `go` em `go.mod`. Se não houver, informe só a linguagem (ou a versão instalada, deixando claro que é a do ambiente).

## 3. Framework e versão

| Framework | Dependência no manifest | Assinatura no código |
|-----------|------------------------|----------------------|
| Flask | `flask` | `Flask(__name__)`, `@app.route`, `Blueprint(`, `add_url_rule(` |
| FastAPI | `fastapi` | `FastAPI()`, `@app.get(`, `APIRouter(` |
| Django | `django` | `manage.py`, `settings.py`, `urls.py`, `models.Model` |
| Express | `express` | `require('express')` / `import express`, `app.get(`, `express.Router()` |
| NestJS | `@nestjs/core` | `@Controller(`, `@Module(` |
| Fastify / Koa / Hapi | `fastify` / `koa` / `@hapi/hapi` | `fastify()`, `new Koa()` |
| Spring Boot | `spring-boot-starter-web` | `@RestController`, `@GetMapping` |
| Laravel / Rails | `laravel/framework` / `rails` | `routes/web.php` / `config/routes.rb` |

Versão: use a versão fixada no manifest (`flask==3.1.1`); para ranges (`^4.18.2`) prefira a versão resolvida no lock file (`package-lock.json` → `"node_modules/express": { "version": ... }`) e informe-a.

Dependências relevantes: liste as de runtime com papel arquitetural (ORM, driver de banco, CORS, validação, auth, dotenv, clients HTTP/SMTP). Sinalize dependências **declaradas mas não usadas** (grep pelo import) — viram finding de código morto.

## 4. Banco de dados e tabelas/entidades

| Sinal | Conclusão |
|-------|-----------|
| `sqlite3.connect(`, `new sqlite3.Database(`, `*.db` / `:memory:` | SQLite (arquivo ou em memória) |
| `SQLAlchemy(`, `db.Model`, `__tablename__` | SQLAlchemy ORM (+ URI em `SQLALCHEMY_DATABASE_URI`) |
| `mongoose`, `MongoClient` | MongoDB |
| `pg`, `psycopg2`, `mysql2`, `pymysql` | PostgreSQL / MySQL |
| `prisma/schema.prisma`, `sequelize.define`, `TypeORM @Entity` | ORMs Node |

Tabelas: `grep -n "CREATE TABLE" -r`, `grep -n "__tablename__"`, classes que herdam de `Model`, schemas do ORM. Registre também **onde o schema é criado e onde há seed** (dados iniciais), pois isso afeta a execução e a validação.

## 5. Domínio da aplicação

Infira pelo vocabulário de tabelas, rotas e entidades e descreva em uma linha com as entidades principais, no idioma do código. Exemplos de raciocínio:
- `produtos`, `pedidos`, `itens_pedido`, `usuarios` → "E-commerce API (produtos, pedidos, usuários)".
- `courses`, `enrollments`, `payments`, rota `/checkout` → "LMS (plataforma de cursos) com fluxo de checkout/pagamento".
- `tasks`, `categories`, `users`, rotas `/reports` → "Task Manager API (tarefas, categorias, usuários, relatórios)".

## 6. Classificação da arquitetura atual

| Classificação | Critérios |
|---------------|-----------|
| **Monolítica sem camadas** | Poucos arquivos; SQL, regras de negócio, validação e roteamento misturados; arquivo/classe "faz-tudo" (ex.: classe que cria o banco, faz seed, registra rotas e processa pagamento). |
| **Parcialmente em camadas** | Existem pastas `models/`, `routes/`, `services/`, `utils/`, mas: rotas contêm regra de negócio e queries; services/helpers existem e não são usados; config espalhada. |
| **Em camadas (MVC/Layered)** | Rotas finas delegando para controllers/services; models só com dados; config centralizada; tratamento de erro centralizado. |

Justifique em uma frase citando a evidência principal (ex.: "Monolítica — 4 arquivos, `models.py` concentra SQL + regras de 4 domínios").

## 7. Inventário de endpoints

| Stack | Como encontrar rotas |
|-------|---------------------|
| Flask | `grep -rn "@.*\.route(\|add_url_rule(" .` + prefixos de `Blueprint(..., url_prefix=)` e `register_blueprint(..., url_prefix=)` |
| FastAPI | `grep -rn "@\(app\|router\)\.\(get\|post\|put\|patch\|delete\)(" .` |
| Express/Koa/Fastify | `grep -rnE "(app|router)\.(get|post|put|patch|delete|all|use)\(" src` + prefixos de `app.use('/prefix', router)` |
| Django | `path(`/`re_path(` em `urls.py` |
| Spring | `@(Get|Post|Put|Delete|Patch|Request)Mapping` |

Para cada rota registre: método, caminho completo, handler (`arquivo:linha`), parâmetros de path/query e **formato do body** (nomes exatos dos campos — ex.: `usr`, `eml`, `c_id`). Use `api.http`/README para exemplos de payload válidos.

## 8. Como executar (receita de execução)

Levante — sem executar nada nesta fase:
- **Instalação**: `pip install -r requirements.txt` / `npm install` / `go mod download`...
- **Pré-passos**: seed/migrations (`python seed.py`, `npm run migrate`), variáveis de ambiente obrigatórias.
- **Start**: README → `scripts.start` do `package.json` → `if __name__ == "__main__":` / `app.listen(` / `Procfile`.
- **Porta**: `app.run(port=...)`, `listen(PORT)`, config (`config.port`), padrão do framework (Flask 5000, Express sem padrão).
- **Estado**: onde fica o banco (arquivo relativo ao cwd? `instance/`? memória?) — importante para rodar a validação com banco limpo.

## 9. Bloco de saída

Use o bloco definido no `SKILL.md` (Fase 1). Exemplo preenchido:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1, sqlite3 (stdlib)
Domain:        E-commerce API (produtos, pedidos, usuários)
Architecture:  Monolítica — tudo em 4 arquivos, sem separação de camadas
Source files:  4 files analyzed (~800 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Entry point:   app.py (python app.py, porta 5000)
Endpoints:     17 routes (GET /produtos, POST /produtos, ..., POST /admin/query)
================================
```
