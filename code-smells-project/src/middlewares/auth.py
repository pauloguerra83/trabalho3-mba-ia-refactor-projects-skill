import hmac
from functools import wraps

from flask import current_app, request

from src.middlewares.error_handler import ForbiddenError


def require_admin(fn):
    """Exige o header X-Admin-Token igual ao ADMIN_TOKEN do ambiente; sem token configurado a rota fica bloqueada."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        esperado = current_app.config.get("ADMIN_TOKEN")
        recebido = request.headers.get("X-Admin-Token", "")
        if not esperado or not hmac.compare_digest(recebido, esperado):
            raise ForbiddenError("Acesso administrativo não autorizado")
        return fn(*args, **kwargs)
    return wrapper
