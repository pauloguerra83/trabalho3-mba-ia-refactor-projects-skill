import sqlite3

from flask import current_app, g


def get_db():
    """Conexão SQLite da requisição atual (uma por request, fechada no teardown)."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def connect(caminho):
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    return conexao


def close_db(_exc=None):
    conexao = g.pop("db", None)
    if conexao is not None:
        conexao.close()


def init_app(app):
    app.teardown_appcontext(close_db)
