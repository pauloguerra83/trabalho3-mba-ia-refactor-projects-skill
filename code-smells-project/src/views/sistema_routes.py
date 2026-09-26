from flask import Blueprint, jsonify, request

from src.config.constants import APP_VERSION
from src.controllers import sistema_controller
from src.middlewares.auth import require_admin

sistema_bp = Blueprint("sistema", __name__)


@sistema_bp.route("/", methods=["GET"])
def index():
    return jsonify({
        "mensagem": "Bem-vindo à API da Loja",
        "versao": APP_VERSION,
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health",
        },
    })


@sistema_bp.route("/health", methods=["GET"])
def health_check():
    status = sistema_controller.health()
    return jsonify(status), 200 if status["status"] == "ok" else 500


@sistema_bp.route("/admin/reset-db", methods=["POST"])
@require_admin
def reset_database():
    sistema_controller.reset_database()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200


@sistema_bp.route("/admin/query", methods=["POST"])
@require_admin
def executar_query():
    dados = sistema_controller.executar_query(request.get_json(silent=True))
    return jsonify({"dados": dados, "sucesso": True}), 200
