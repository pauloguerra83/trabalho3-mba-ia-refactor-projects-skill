import logging

from src.config.constants import STATUS_PEDIDO, STATUS_PEDIDO_INICIAL
from src.database.connection import get_db
from src.middlewares.error_handler import ValidationError
from src.models import pedido_model, produto_model

logger = logging.getLogger(__name__)


def _validar_itens(itens):
    for item in itens:
        if not isinstance(item, dict) or "produto_id" not in item or "quantidade" not in item:
            raise ValidationError("Cada item deve ter produto_id e quantidade")
        quantidade = item["quantidade"]
        if not isinstance(quantidade, int) or isinstance(quantidade, bool) or quantidade <= 0:
            raise ValidationError("Quantidade deve ser um inteiro positivo")


def criar(dados):
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens or not isinstance(itens, list):
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    _validar_itens(itens)

    db = get_db()
    with db:  # pedido + itens + baixa de estoque: tudo ou nada
        total = 0
        precos = {}
        for item in itens:
            produto = produto_model.buscar_por_id(db, item["produto_id"])
            if produto is None:
                raise ValidationError("Produto " + str(item["produto_id"]) + " não encontrado", com_sucesso=True)
            if produto["estoque"] < item["quantidade"]:
                raise ValidationError("Estoque insuficiente para " + produto["nome"], com_sucesso=True)
            precos[item["produto_id"]] = produto["preco"]
            total = total + (produto["preco"] * item["quantidade"])

        pedido_id = pedido_model.inserir(db, usuario_id, STATUS_PEDIDO_INICIAL, total)
        for item in itens:
            pedido_model.inserir_item(db, pedido_id, item["produto_id"], item["quantidade"], precos[item["produto_id"]])
            produto_model.baixar_estoque(db, item["produto_id"], item["quantidade"])

    logger.info("Notificação (e-mail/SMS/push): pedido %s criado para usuario %s", pedido_id, usuario_id)
    return {"pedido_id": pedido_id, "total": total}


def listar_todos():
    return pedido_model.listar_com_itens(get_db())


def listar_por_usuario(usuario_id):
    return pedido_model.listar_com_itens(get_db(), usuario_id)


def atualizar_status(pedido_id, dados):
    dados = dados if isinstance(dados, dict) else {}
    novo_status = dados.get("status", "")
    if novo_status not in STATUS_PEDIDO:
        raise ValidationError("Status inválido")

    db = get_db()
    with db:
        pedido_model.atualizar_status(db, pedido_id, novo_status)

    if novo_status == "aprovado":
        logger.info("Notificação: pedido %s foi aprovado, preparar envio", pedido_id)
    elif novo_status == "cancelado":
        logger.info("Notificação: pedido %s cancelado", pedido_id)
