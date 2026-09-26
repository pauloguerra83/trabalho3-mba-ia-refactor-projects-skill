from flask import Blueprint, jsonify, request

from src.controllers import produto_controller

produto_bp = Blueprint("produtos", __name__)


@produto_bp.route("/produtos", methods=["GET"])
def listar_produtos():
    return jsonify({"dados": produto_controller.listar(), "sucesso": True}), 200


@produto_bp.route("/produtos/busca", methods=["GET"])
def buscar_produtos():
    resultados = produto_controller.buscar(
        request.args.get("q", ""),
        request.args.get("categoria"),
        request.args.get("preco_min"),
        request.args.get("preco_max"),
    )
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200


@produto_bp.route("/produtos/<int:id>", methods=["GET"])
def buscar_produto(id):
    return jsonify({"dados": produto_controller.buscar_por_id(id), "sucesso": True}), 200


@produto_bp.route("/produtos", methods=["POST"])
def criar_produto():
    produto_id = produto_controller.criar(request.get_json(silent=True))
    return jsonify({"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}), 201


@produto_bp.route("/produtos/<int:id>", methods=["PUT"])
def atualizar_produto(id):
    produto_controller.atualizar(id, request.get_json(silent=True))
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


@produto_bp.route("/produtos/<int:id>", methods=["DELETE"])
def deletar_produto(id):
    produto_controller.deletar(id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
