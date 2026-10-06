import logging
from datetime import datetime

from config.constants import (
    DEFAULT_PRIORITY, DEFAULT_TASK_STATUS, PRIORITY_MAX, PRIORITY_MIN,
    TASK_STATUSES, TITLE_MAX_LENGTH, TITLE_MIN_LENGTH,
)
from database import db, utc_now
from middlewares.error_handler import NotFoundError, ValidationError
from models.category import Category
from models.task import Task
from models.user import User

logger = logging.getLogger(__name__)


def _with_overdue(task):
    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    return data


def _parse_due_date(value, error_message):
    if not isinstance(value, str):
        raise ValidationError(error_message)
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        raise ValidationError(error_message)


def _join_tags(tags):
    return ','.join(tags) if isinstance(tags, list) else tags


def _validate(data, creating):
    """Validação única de criação/atualização, com as mensagens e a ordem do contrato original.

    Retorna só os campos presentes (na criação, com defaults), já convertidos.
    """
    if not data or not isinstance(data, dict):
        raise ValidationError('Dados inválidos')

    fields = {}
    if creating or 'title' in data:
        title = data.get('title')
        if creating and not title:
            raise ValidationError('Título é obrigatório')
        if not isinstance(title, str):
            raise ValidationError('Título inválido')
        if len(title) < TITLE_MIN_LENGTH:
            raise ValidationError('Título muito curto')
        if len(title) > TITLE_MAX_LENGTH:
            raise ValidationError('Título muito longo')
        fields['title'] = title

    if creating:
        fields['description'] = data.get('description', '')
    elif 'description' in data:
        fields['description'] = data['description']

    if creating or 'status' in data:
        status = data.get('status', DEFAULT_TASK_STATUS)
        if status not in TASK_STATUSES:
            raise ValidationError('Status inválido')
        fields['status'] = status

    if creating or 'priority' in data:
        priority = data.get('priority', DEFAULT_PRIORITY)
        if isinstance(priority, bool) or not isinstance(priority, int) or not PRIORITY_MIN <= priority <= PRIORITY_MAX:
            raise ValidationError('Prioridade deve ser entre 1 e 5')
        fields['priority'] = priority

    if creating or 'user_id' in data:
        user_id = data.get('user_id')
        if user_id and not User.get_by_id(user_id):
            raise NotFoundError('Usuário não encontrado')
        fields['user_id'] = user_id

    if creating or 'category_id' in data:
        category_id = data.get('category_id')
        if category_id and not Category.get_by_id(category_id):
            raise NotFoundError('Categoria não encontrada')
        fields['category_id'] = category_id

    if 'due_date' in data:
        date_error = 'Formato de data inválido. Use YYYY-MM-DD' if creating else 'Formato de data inválido'
        if data['due_date']:
            fields['due_date'] = _parse_due_date(data['due_date'], date_error)
        elif not creating:
            fields['due_date'] = None

    if 'tags' in data and (data['tags'] or not creating):
        fields['tags'] = _join_tags(data['tags'])

    return fields


def list_tasks():
    result = []
    for task in Task.list_all_with_relations():  # user e category carregados na mesma query
        data = _with_overdue(task)
        data['user_name'] = task.user.name if task.user else None
        data['category_name'] = task.category.name if task.category else None
        result.append(data)
    return result


def get_task(task_id):
    task = Task.get_by_id(task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    return _with_overdue(task)


def create_task(data):
    fields = _validate(data, creating=True)
    task = Task(**fields)
    task.save()
    db.session.commit()
    logger.info('Task criada: %s', task.id)
    return task.to_dict()


def update_task(task_id, data):
    task = Task.get_by_id(task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    for field, value in _validate(data, creating=False).items():
        setattr(task, field, value)
    task.updated_at = utc_now()
    db.session.commit()
    logger.info('Task atualizada: %s', task.id)
    return task.to_dict()


def delete_task(task_id):
    task = Task.get_by_id(task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    task.remove()
    db.session.commit()
    logger.info('Task deletada: %s', task_id)


def _optional_int(value):
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError('Parâmetro de busca inválido')


def search_tasks(text, status, priority, user_id):
    tasks = Task.search(text, status, _optional_int(priority), _optional_int(user_id))
    return [task.to_dict() for task in tasks]


def task_stats():
    by_status = Task.count_by(Task.status)
    total = sum(by_status.values())
    done = by_status.get('done', 0)
    stats = {status: by_status.get(status, 0) for status in TASK_STATUSES}
    stats['total'] = total
    stats['overdue'] = sum(1 for task in Task.list_all() if task.is_overdue())
    stats['completion_rate'] = round((done / total) * 100, 2) if total > 0 else 0
    return stats
