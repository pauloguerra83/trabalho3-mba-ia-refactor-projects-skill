# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`, organizada em MVC (models, controllers, routes, middlewares e config).

## Como rodar

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias.

> Se você tem um banco criado pela versão antiga (senhas em MD5), rode `python seed.py` de novo: o login agora usa hash com salt (werkzeug) e não reconhece os hashes antigos.

## Configuração

As opções vêm de variáveis de ambiente ou de um arquivo `.env` (veja `.env.example`). Sem nenhuma variável a API sobe com defaults seguros de desenvolvimento:

| Variável | Default | Uso |
|----------|---------|-----|
| `SECRET_KEY` | gerada a cada boot | Assina os tokens de login |
| `DATABASE_URL` | `sqlite:///tasks.db` | Banco (SQLAlchemy) |
| `FLASK_DEBUG` | `false` | Liga o modo debug |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Endereço do servidor (`HOST=0.0.0.0` para expor na rede) |
| `CORS_ORIGINS` | `http://localhost:3000` | Origens permitidas, separadas por vírgula |
| `LOG_LEVEL` | `INFO` | Nível de log |

## Estrutura

```
app.py            # create_app(): config, logging, CORS, banco, erros, blueprints
database.py       # instância do SQLAlchemy + utc_now()
config/           # settings (ambiente) e constantes de negócio
models/           # entidades e acesso a dados
controllers/      # regras de negócio e validação
routes/           # rotas HTTP (Blueprints)
middlewares/      # tratamento central de erros
seed.py           # dados de exemplo
```
