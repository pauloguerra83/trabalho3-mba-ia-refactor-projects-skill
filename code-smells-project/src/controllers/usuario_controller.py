import logging

from src.database.connection import get_db
from src.middlewares.error_handler import NotFoundError, UnauthorizedError, ValidationError
from src.models import usuario_model

logger = logging.getLogger(__name__)


def listar():
    return usuario_model.listar(get_db())


def buscar_por_id(usuario_id):
    usuario = usuario_model.buscar_por_id(get_db(), usuario_id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return usuario


def criar(dados):
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    nome, email, senha = dados.get("nome", ""), dados.get("email", ""), dados.get("senha", "")
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not all(isinstance(v, str) for v in (nome, email, senha)):
        raise ValidationError("Nome, email e senha devem ser texto")

    db = get_db()
    with db:
        usuario_id = usuario_model.criar(db, nome, email, senha)
    logger.info("Usuário criado: id=%s", usuario_id)
    return usuario_id


def login(dados):
    dados = dados if isinstance(dados, dict) else {}
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")
    if not isinstance(email, str) or not isinstance(senha, str):
        raise ValidationError("Email e senha devem ser texto")

    usuario = usuario_model.autenticar(get_db(), email, senha)
    if not usuario:
        logger.info("Login falhou")
        raise UnauthorizedError("Email ou senha inválidos", com_sucesso=True)
    logger.info("Login bem-sucedido: id=%s", usuario["id"])
    return usuario
