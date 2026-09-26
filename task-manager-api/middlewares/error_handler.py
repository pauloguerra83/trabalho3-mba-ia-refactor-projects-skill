import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from database import db

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({'error': err.message}), err.status_code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        if isinstance(err, HTTPException):  # 404/405 de rota inexistente seguem o padrão do Flask
            return err
        db.session.rollback()
        logger.exception('Erro não tratado')
        return jsonify({'error': 'Erro interno'}), 500
