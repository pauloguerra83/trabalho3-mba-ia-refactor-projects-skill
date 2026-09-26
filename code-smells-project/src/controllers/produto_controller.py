import logging

from src.config.constants import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_PRODUTO_MAX, NOME_PRODUTO_MIN
from src.database.connection import get_db
from src.middlewares.error_handler import NotFoundError, ValidationError
from src.models import produto_model

logger = logging.getLogger(__name__)


def _numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _validar_produto(dados, criacao):
    """Validação única de criar/atualizar, com as mesmas mensagens e a mesma ordem do contrato original."""
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    for campo, mensagem in (("nome", "Nome é obrigatório"), ("preco", "Preço é obrigatório"), ("estoque", "Estoque é obrigatório")):
        if campo not in dados:
            raise ValidationError(mensagem)

    nome, preco, estoque = dados["nome"], dados["preco"], dados["estoque"]
    if not isinstance(nome, str):
        raise ValidationError("Nome inválido")
    if not _numero(preco):
        raise ValidationError("Preço deve ser numérico")
    if not _numero(estoque):
        raise ValidationError("Estoque deve ser numérico")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")

    categoria = dados.get("categoria", CATEGORIA_PADRAO)
    if criacao:
        if len(nome) < NOME_PRODUTO_MIN:
            raise ValidationError("Nome muito curto")
        if len(nome) > NOME_PRODUTO_MAX:
            raise ValidationError("Nome muito longo")
        if categoria not in CATEGORIAS_VALIDAS:
            raise ValidationError("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

    return {
        "nome": nome,
        "descricao": dados.get("descricao", ""),
        "preco": preco,
        "estoque": estoque,
        "categoria": categoria,
    }


def listar():
    produtos = produto_model.listar(get_db())
    logger.info("Listando %d produtos", len(produtos))
    return produtos


def buscar_por_id(produto_id):
    produto = produto_model.buscar_por_id(get_db(), produto_id)
    if not produto:
        raise NotFoundError("Produto não encontrado", com_sucesso=True)
    return produto


def buscar(termo, categoria, preco_min, preco_max):
    try:
        preco_min = float(preco_min) if preco_min else preco_min
        preco_max = float(preco_max) if preco_max else preco_max
    except ValueError:
        raise ValidationError("preco_min e preco_max devem ser numéricos")
    return produto_model.buscar(get_db(), termo, categoria, preco_min, preco_max)


def criar(dados):
    produto = _validar_produto(dados, criacao=True)
    db = get_db()
    with db:
        produto_id = produto_model.criar(db, **produto)
    logger.info("Produto criado com ID: %s", produto_id)
    return produto_id


def atualizar(produto_id, dados):
    db = get_db()
    if not produto_model.buscar_por_id(db, produto_id):
        raise NotFoundError("Produto não encontrado")
    produto = _validar_produto(dados, criacao=False)
    with db:
        produto_model.atualizar(db, produto_id, **produto)


def deletar(produto_id):
    db = get_db()
    if not produto_model.buscar_por_id(db, produto_id):
        raise NotFoundError("Produto não encontrado")
    with db:
        produto_model.deletar(db, produto_id)
    logger.info("Produto %s deletado", produto_id)
