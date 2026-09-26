# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`, organizada em MVC.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Exemplos de requisições estão em `api.http`.

## Configuração

Todas as opções vêm de variáveis de ambiente (veja `.env.example`). Sem nenhuma variável a API sobe com defaults de desenvolvimento:

| Variável | Default | Uso |
|----------|---------|-----|
| `PORT` | `3000` | Porta HTTP |
| `DB_PATH` | `:memory:` | Banco SQLite |
| `PAYMENT_GATEWAY_KEY` | vazio (gateway simulado) | Chave do gateway de pagamento |
| `ADMIN_TOKEN` | vazio (rotas admin bloqueadas) | Valor exigido no header `X-Admin-Token` |

As rotas `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem o header `X-Admin-Token`:

```bash
ADMIN_TOKEN=troque-me npm start
curl http://localhost:3000/api/admin/financial-report -H "X-Admin-Token: troque-me"
```

## Estrutura

```
src/app.js           # entry point + composition root
src/config/          # variáveis de ambiente e constantes de pagamento
src/database.js      # conexão, helpers Promise, transaction(), schema e seed
src/models/          # acesso a dados (users, courses, enrollments/payments/audit)
src/services/        # gateway de pagamento (simulado)
src/controllers/     # checkout, relatório financeiro, usuários
src/routes/          # rotas HTTP (express.Router)
src/middlewares/     # tratamento central de erros e guard de admin
```
