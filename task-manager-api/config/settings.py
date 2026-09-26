import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _bool(name, default=False):
    return os.getenv(name, str(default)).lower() in ('1', 'true', 'yes')


class Settings:
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)  # dev: chave efêmera gerada em runtime
    SECRET_KEY_FROM_ENV = bool(os.getenv('SECRET_KEY'))
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///tasks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = _bool('FLASK_DEBUG', False)
    HOST = os.getenv('HOST', '127.0.0.1')
    PORT = int(os.getenv('PORT', '5000'))
    CORS_ORIGINS = [o.strip() for o in os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',') if o.strip()]
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
