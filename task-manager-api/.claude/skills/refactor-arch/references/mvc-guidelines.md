# Referência — Guidelines da Arquitetura MVC Alvo (Fase 3)

Para APIs backend, o MVC é aplicado assim: **Model** = dados e acesso a dados; **View** = camada de apresentação HTTP (rotas + serialização JSON); **Controller** = fluxo da aplicação (casos de uso, regras, orquestração). Somam-se camadas de suporte: config, middlewares e composition root. **Essenciais** são config, models, controllers, views/routes, handler de erro e entry point; as demais (services, database separado, utils, auth) só existem quando um finding as exige — veja a seção 3 (Proporcionalidade).

---

## 1. Camadas e responsabilidades

| Camada | Pasta | Responsabilidade | NÃO pode |
|--------|-------|------------------|----------|
| **Config** | `config/` | Ler variáveis de ambiente (com defaults seguros para dev), constantes da aplicação (status válidos, limites, thresholds), configuração por ambiente. | Conter segredos reais; importar models/controllers. |
| **Models** | `models/` | Entidades e acesso a dados (repositórios): queries **parametrizadas**/ORM, mapeamento linha → objeto/dict **seguro** (sem senha), transações de persistência. | Importar framework HTTP (`flask.request`, `req/res`); decidir status HTTP; enviar e-mail. |
| **Controllers** | `controllers/` | Casos de uso: validar entrada (via validators), aplicar regras de negócio, orquestrar models e services, **delimitar** a transação do caso de uso (`with db:`, `commit()`/`rollback()`, `transaction()`), lançar erros de domínio (`NotFoundError`, `ValidationError`). Recebem e retornam **dados puros** (dict/objetos). | Acessar `request`/`res` diretamente; executar SQL **ou queries de ORM** (`execute(...)`, `db.session.get/execute/add/delete`, `Model.query`) — toda leitura/escrita passa por uma função/método do model (T-16); formatar resposta HTTP. |
| **Services** (opcional) | `services/` | Só quando há integração externa real (e-mail, gateway de pagamento) ou regra reutilizada por ≥ 2 controllers. Recebem config por parâmetro. Uma função usada em um único lugar fica no controller/model, não vira service. | Ter credenciais próprias; conhecer HTTP. |
| **Views / Routes** | `views/` ou `routes/` | Declarar rotas (método + caminho idênticos ao original), extrair parâmetros/body do request, chamar o controller, serializar a resposta (status + JSON no formato original). Finas: ~5–15 linhas por handler. | Regras de negócio; SQL; `try/except` genérico (erros sobem ao handler central). |
| **Middlewares** | `middlewares/` | Handler de erro central (erro de domínio → status + JSON), autenticação/autorização de rotas protegidas, logging de requisições. | Regras de negócio. |
| **Database** | `database/` (ou `models/db.*`) | Criação da conexão (por request ou pool), schema/migrations, seed separado. | Ser importado por views. |
| **Composition root** | `app.*` / `create_app()` | Carregar config, criar app, inicializar banco, instanciar dependências (injeção), registrar middlewares e rotas. Único lugar que "conhece todo mundo". | Conter handlers de rota ou SQL. |

### Regra de dependência (sempre de cima para baixo)

```
views/routes ──► controllers ──► models
      │               │  └─────► services
      ▼               ▼
  middlewares      config   (todas as camadas podem ler config)
composition root ──► todas (monta e injeta)
```
- Proibido: model importar controller/view; controller importar `request`/`res`; view **ou controller** executar SQL/queries de ORM (o controller só chama métodos do model e delimita a transação).
- Erros fluem por exceções de domínio até o middleware de erro — não por `return {"erro": ...}` misturado a dados.

## 2. Estrutura-alvo por situação

### 2.1 Monólito sem camadas (arquivos planos na raiz)
Crie um pacote `src/` com as camadas **essenciais** e mantenha o comando original de execução com um entry point fino na raiz. As árvores abaixo são o **máximo** esperado, não uma lista a preencher: itens marcados `(se necessário)` só existem quando algum finding os exige.

**Python/Flask**
```
<projeto>/
├── app.py                      # entry point fino: from src.app import create_app; app = create_app(); app.run(...)
├── requirements.txt
├── .env.example                # variáveis esperadas, sem valores reais
└── src/
    ├── __init__.py
    ├── app.py                  # composition root: create_app()
    ├── config/
    │   ├── __init__.py
    │   ├── settings.py         # Settings lidas do ambiente
    │   └── constants.py        # enums/limites/thresholds
    ├── database/               # (se necessário) conexão por request + schema/seed — ou um único models/db.py
    │   ├── connection.py
    │   └── schema.py
    ├── models/                 # um arquivo por agregado: produto_model.py, usuario_model.py, pedido_model.py
    ├── controllers/            # produto_controller.py, usuario_controller.py, pedido_controller.py, relatorio_controller.py
    ├── services/               # (se necessário) só integrações externas / regras reutilizadas
    ├── views/                  # produto_routes.py, ... (Blueprints)
    ├── middlewares/
    │   ├── error_handler.py    # inclui as exceções de domínio se forem poucas
    │   └── auth.py             # (se necessário) só se houver rota protegida por finding
    └── utils/                  # (se necessário) validators.py só se houver validação repetida (AP-12)
```

**Node.js/Express** (já costuma ter `src/`)
```
<projeto>/
├── package.json                # "start" continua funcionando (ajuste "main"/"start" se o entry mudar)
├── .env.example
└── src/
    ├── app.js                  # entry point + composition root (separe server.js só se houver motivo, ex.: testes)
    ├── config/index.js         # process.env + defaults de dev (+ constantes, se poucas)
    ├── database.js             # conexão + helpers Promise (run/get/all) + transaction() + schema/seed
    ├── models/                 # userModel.js, courseModel.js, enrollmentModel.js, paymentModel.js
    ├── controllers/            # checkoutController.js, reportController.js, userController.js
    ├── services/               # (se necessário) ex.: paymentService.js para o gateway
    ├── routes/ (views)         # checkoutRoutes.js, adminRoutes.js, userRoutes.js (express.Router)
    └── middlewares/            # errorHandler.js (+ erros de domínio), adminAuth.js (se necessário)
```

### 2.2 Projeto parcialmente em camadas (pastas já existem na raiz)
**Evolua in-place** — não mova tudo para `src/` só por estética (quebraria imports, scripts como `seed.py` e hábitos da equipe):
- Mantenha `models/`, `routes/` (= views), `services/`, `utils/` onde estão.
- **Adicione** só as camadas que faltam e que algum finding exige: `config/`, `controllers/` (tirar regra de negócio das rotas), handler de erro central, e um `create_app()` como composition root no entry point.
- Mova rotas que estão no arquivo errado para o módulo do seu recurso (ex.: rotas de categorias dentro de `report_routes` → `category_routes`).
- Helpers/services existentes e não usados: **remova** (código morto) em vez de integrá-los à força — só passe a usá-los se resolverem um finding.
- `app.py` e scripts auxiliares (`seed.py`) devem continuar funcionando com o mesmo comando.

### 2.3 Outras stacks (mesmos princípios)
- **FastAPI**: `routers/` (views) + `controllers/` ou `services/` + `models/`/`repositories/` + `core/config.py`; erro via `@app.exception_handler`.
- **Django**: já é MVT — `views.py` fino, regras em `services.py`, queries no model/manager; settings via env.
- **Spring**: `@RestController` (view) → `@Service` (controller/caso de uso) → `@Repository` (model); `@ControllerAdvice` para erros.
- **NestJS**: controller → provider/service → repository; `ExceptionFilter`.

## 3. Proporcionalidade (anti over-engineering)

A refatoração busca o **menor conjunto de mudanças** que resolve os findings e deixa o projeto em MVC. Sinais de excesso a evitar:

| Não faça | Faça |
|----------|------|
| Criar `services/`, `utils/`, `repositories/` "porque a árvore-modelo tem" | Criar a pasta só quando um finding precisa dela |
| Arquivo com uma única função trivial (`health_model.ping`, `asyncHandler` de 1 linha usado 1 vez) | Deixar a função no módulo do domínio mais próximo |
| Wrapper sobre a stdlib (`utils/logger.py` que só chama `logging.getLogger`) | Usar `logging.getLogger(__name__)` / `console` direto |
| Classe, interface, factory ou injeção de dependência para uma única implementação | Funções de módulo; injetar só o que o teste/finding exige (ex.: conexão do banco) |
| Hierarquia grande de exceções | As exceções que o código realmente lança (ex.: `NotFoundError`, `ValidationError`) |
| Cache, retries, paginação, métricas "para o futuro" | Nada que nenhum finding pediu |
| Renomear variáveis/arquivos só por estilo | Renomear só quando o nome engana (AP-18) ou quando o arquivo já está sendo reescrito |

Critério de parada: todos os CRITICAL/HIGH resolvidos, camadas essenciais presentes, endpoints validados. Não continue "melhorando".

## 4. Regras obrigatórias da refatoração

1. **Contrato HTTP preservado**: mesmas rotas, métodos, nomes de campos de entrada (inclusive nomes ruins como `usr`, `eml`, `c_id` — renomeie só variáveis internas), mesma estrutura de resposta de sucesso e mesmas chaves de erro (`erro` vs `error`) e status de sucesso. Exceções permitidas **somente por segurança** (e listadas em "Contract Changes"): remover senha/hash/segredos das respostas, exigir auth em rota administrativa/destrutiva, recusar SQL arbitrário.
2. **Config sem segredos**: nenhum segredo real no código. Segredos vêm do ambiente; para rodar em dev sem `.env`, use default **gerado em runtime** (ex.: `secrets.token_hex(32)`, `crypto.randomBytes(32)`) ou valor explicitamente de dev (`"dev-only-change-me"`) com aviso no log. Crie `.env.example`. Debug desligado por padrão (ligável via env).
3. **Segurança mínima**: SQL parametrizado; senhas com hash forte e salt (`werkzeug.security`, `bcrypt`, `crypto.scrypt`/`pbkdf2`); nada sensível em logs; rotas administrativas protegidas por token de admin vindo do ambiente (sem token configurado ⇒ rota desabilitada com 403/404).
4. **Transações** em casos de uso que gravam em mais de uma tabela.
5. **Erro centralizado**: exceções de domínio + um handler que produz o JSON de erro; handler genérico para 500 que loga o stack e responde mensagem genérica (sem `str(e)`).
6. **Logging** via logger da stack (`logging.getLogger(__name__)`, `console` ou lib já presente) em vez de `print` espalhado — sem criar wrapper próprio.
7. **Constantes nomeadas** para listas de status/roles/categorias, limites e thresholds **repetidos ou de regra de negócio** — no módulo de config ou no próprio domínio, se usadas em um só lugar.
8. **Remova os arquivos antigos** depois que o novo código assumir (nada de `models_old.py`); remova imports e helpers mortos.
9. **Sem dependências novas desnecessárias**; se o projeto já declara algo útil (`python-dotenv`, `marshmallow`), pode usar.
10. **Documentação**: se o comando de execução, variáveis de ambiente ou estrutura mudarem, atualize o README do projeto.

## 5. Definition of Done (checklist da Fase 3)

- [ ] Estrutura de diretórios segue o padrão MVC (config, models, views/routes, controllers, handler de erro, entry point)
- [ ] Todo arquivo novo está justificado por um finding ou é camada essencial (seção "Files Created" da saída)
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models abstraem os dados (sem SQL nem queries de ORM fora dos models/database — checagem de camada do `validation-guide.md`)
- [ ] Views/Routes só roteiam e serializam
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro (composition root)
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem corretamente (comparados ao baseline)
