import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500

    def __init__(self, message, status_code=None, com_sucesso=False):
        super().__init__(message)
        self.message = message
        if status_code:
            self.status_code = status_code
        self.com_sucesso = com_sucesso  # algumas rotas do contrato original incluem "sucesso": false no erro


class ValidationError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        corpo = {"erro": err.message}
        if err.com_sucesso:
            corpo["sucesso"] = False
        return jsonify(corpo), err.status_code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        if isinstance(err, HTTPException):  # 404/405 de rota inexistente seguem o padrão do Flask
            return err
        logger.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno do servidor"}), 500
