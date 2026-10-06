import logging
import re

from flask import current_app
from itsdangerous import URLSafeTimedSerializer

from config.constants import DEFAULT_ROLE, EMAIL_REGEX, PASSWORD_MIN_LENGTH, USER_ROLES
from database import db
from middlewares.error_handler import (
    ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError,
)
from models.task import Task
from models.user import User

logger = logging.getLogger(__name__)


def _valid_email(email):
    return isinstance(email, str) and re.match(EMAIL_REGEX, email)


def _get_or_404(user_id):
    user = User.get_by_id(user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')
    return user


def _require_body(data):
    if not data or not isinstance(data, dict):
        raise ValidationError('Dados inválidos')


def list_users():
    task_counts = Task.count_by(Task.user_id)  # uma query agregada em vez de carregar u.tasks por usuário
    result = []
    for user in User.list_all():
        data = user.to_dict()
        data['task_count'] = task_counts.get(user.id, 0)
        result.append(data)
    return result


def get_user(user_id):
    data = _get_or_404(user_id).to_dict()
    data['tasks'] = [task.to_dict() for task in Task.list_by_user(user_id)]
    return data


def create_user(data):
    _require_body(data)
    name, email, password = data.get('name'), data.get('email'), data.get('password')
    role = data.get('role', DEFAULT_ROLE)

    if not name:
        raise ValidationError('Nome é obrigatório')
    if not email:
        raise ValidationError('Email é obrigatório')
    if not password:
        raise ValidationError('Senha é obrigatória')
    if not _valid_email(email):
        raise ValidationError('Email inválido')
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationError('Senha deve ter no mínimo 4 caracteres')
    if User.get_by_email(email):
        raise ConflictError('Email já cadastrado')
    if role not in USER_ROLES:
        raise ValidationError('Role inválido')

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    user.save()
    db.session.commit()
    logger.info('Usuário criado: %s', user.id)
    return user.to_dict()


def update_user(user_id, data):
    user = _get_or_404(user_id)
    _require_body(data)

    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        if not _valid_email(data['email']):
            raise ValidationError('Email inválido')
        existing = User.get_by_email(data['email'])
        if existing and existing.id != user_id:
            raise ConflictError('Email já cadastrado')
        user.email = data['email']
    if 'password' in data:
        if not isinstance(data['password'], str) or len(data['password']) < PASSWORD_MIN_LENGTH:
            raise ValidationError('Senha muito curta')
        user.set_password(data['password'])
    if 'role' in data:
        if data['role'] not in USER_ROLES:
            raise ValidationError('Role inválido')
        user.role = data['role']
    if 'active' in data:
        user.active = data['active']

    db.session.commit()
    return user.to_dict()


def delete_user(user_id):
    user = _get_or_404(user_id)
    for task in Task.list_by_user(user_id):  # tasks do usuário e o usuário no mesmo commit
        task.remove()
    user.remove()
    db.session.commit()
    logger.info('Usuário deletado: %s', user_id)


def get_user_tasks(user_id):
    _get_or_404(user_id)
    result = []
    for task in Task.list_by_user(user_id):
        result.append({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'created_at': str(task.created_at),
            'due_date': str(task.due_date) if task.due_date else None,
            'overdue': task.is_overdue(),
        })
    return result


def _issue_token(user):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='auth-token')
    return serializer.dumps({'user_id': user.id})


def login(data):
    _require_body(data)
    email, password = data.get('email'), data.get('password')
    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')
    if not isinstance(email, str) or not isinstance(password, str):
        raise UnauthorizedError('Credenciais inválidas')

    user = User.get_by_email(email)
    if not user or not user.check_password(password):
        raise UnauthorizedError('Credenciais inválidas')
    if not user.active:
        raise ForbiddenError('Usuário inativo')

    return {
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': _issue_token(user),
    }
