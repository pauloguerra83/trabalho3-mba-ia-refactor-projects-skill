import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import Settings
from src.database import connection
from src.database.schema import init_db
from src.middlewares.error_handler import register_error_handlers
from src.views.pedido_routes import pedido_bp
from src.views.produto_routes import produto_bp
from src.views.relatorio_routes import relatorio_bp
from src.views.sistema_routes import sistema_bp
from src.views.usuario_routes import usuario_bp

logger = logging.getLogger(__name__)


def create_app(settings=Settings):
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.config.from_object(settings)
    if not settings.SECRET_KEY_FROM_ENV:
        logger.warning("SECRET_KEY não definida; usando chave efêmera de desenvolvimento")
    if not settings.ADMIN_TOKEN:
        logger.warning("ADMIN_TOKEN não definido; rotas /admin/* responderão 403")

    CORS(app, origins=settings.CORS_ORIGINS)

    connection.init_app(app)
    db = connection.connect(settings.DATABASE_PATH)
    try:
        init_db(db)
    finally:
        db.close()

    register_error_handlers(app)
    for blueprint in (produto_bp, usuario_bp, pedido_bp, relatorio_bp, sistema_bp):
        app.register_blueprint(blueprint)
    return app
