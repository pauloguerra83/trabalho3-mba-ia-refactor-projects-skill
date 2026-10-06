# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`, organizada em MVC.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas gravadas com hash).

> Se você tem um `loja.db` criado pela versão antiga (senhas em texto plano), apague-o antes de subir: o login agora verifica hash.

## Configuração

Todas as opções vêm de variáveis de ambiente (veja `.env.example`). Sem nenhuma variável a API sobe com defaults seguros de desenvolvimento:

| Variável | Default | Uso |
|----------|---------|-----|
| `SECRET_KEY` | gerada a cada boot | Chave da aplicação |
| `ADMIN_TOKEN` | vazio (rotas admin bloqueadas) | Valor exigido no header `X-Admin-Token` em `/admin/*` |
| `FLASK_DEBUG` | `false` | Liga o modo debug |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Endereço do servidor (`HOST=0.0.0.0` para expor na rede) |
| `DATABASE_PATH` | `loja.db` | Arquivo do banco SQLite |
| `CORS_ORIGINS` | `http://localhost:3000` | Origens permitidas, separadas por vírgula |
| `LOG_LEVEL` | `INFO` | Nível de log |

Exemplo de rota administrativa:

```bash
ADMIN_TOKEN=troque-me python app.py
curl -X POST http://127.0.0.1:5000/admin/query -H "X-Admin-Token: troque-me" \
     -H "Content-Type: application/json" -d '{"sql": "SELECT COUNT(*) AS n FROM produtos"}'
```

`/admin/query` aceita apenas uma consulta `SELECT`, executada em modo somente leitura.

## Estrutura

```
app.py                 # entry point (python app.py)
src/app.py             # create_app(): config, logging, CORS, banco, erros, rotas
src/config/            # settings (ambiente) e constantes de negócio
src/database/          # conexão por requisição, schema e seed
src/models/            # acesso a dados (SQL parametrizado)
src/controllers/       # regras de negócio e casos de uso
src/views/             # rotas HTTP (Blueprints)
src/middlewares/       # tratamento central de erros e guard de admin
```
