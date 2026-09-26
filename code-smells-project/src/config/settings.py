import os
import secrets


def _bool(nome, padrao=False):
    return os.getenv(nome, str(padrao)).lower() in ("1", "true", "yes")


class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)  # dev: chave efêmera gerada em runtime
    SECRET_KEY_FROM_ENV = bool(os.getenv("SECRET_KEY"))
    DEBUG = _bool("FLASK_DEBUG", False)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", "loja.db")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")  # None => rotas /admin/* respondem 403
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
