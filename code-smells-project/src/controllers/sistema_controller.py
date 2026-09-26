import logging
import sqlite3

from flask import current_app

from src.config.constants import APP_VERSION
from src.database.connection import get_db
from src.middlewares.error_handler import ValidationError
from src.models import sistema_model

logger = logging.getLogger(__name__)


def health():
    """Retorna o status do serviço sem expor segredos, caminhos ou flags internas."""
    try:
        counts = sistema_model.contagens(get_db())
    except sqlite3.Error:
        logger.exception("Health check: falha ao acessar o banco")
        return {"status": "erro", "database": "disconnected"}
    return {
        "status": "ok",
        "database": "connected",
        "counts": counts,
        "versao": APP_VERSION,
        "ambiente": "desenvolvimento" if current_app.config["DEBUG"] else "producao",
    }


def reset_database():
    db = get_db()
    with db:
        sistema_model.limpar_tabelas(db)
    logger.warning("Banco de dados resetado via /admin/reset-db")


def executar_query(dados):
    dados = dados if isinstance(dados, dict) else {}
    sql = dados.get("sql", "")
    if not sql:
        raise ValidationError("Query não informada")
    if not isinstance(sql, str):
        raise ValidationError("Query inválida")

    consulta = sql.strip().rstrip(";").strip()
    if not consulta.upper().startswith("SELECT") or ";" in consulta:
        raise ValidationError("Apenas uma única consulta SELECT é permitida")
    try:
        return sistema_model.executar_consulta_somente_leitura(get_db(), consulta)
    except sqlite3.Error:
        logger.warning("Consulta administrativa inválida", exc_info=True)
        raise ValidationError("Consulta inválida")
