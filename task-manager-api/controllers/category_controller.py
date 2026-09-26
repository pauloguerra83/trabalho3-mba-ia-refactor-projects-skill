from config.constants import DEFAULT_CATEGORY_COLOR
from database import db
from middlewares.error_handler import NotFoundError, ValidationError
from models.category import Category
from models.task import Task


def _get_or_404(category_id):
    category = Category.get_by_id(category_id)
    if not category:
        raise NotFoundError('Categoria não encontrada')
    return category


def list_categories():
    task_counts = Task.count_by(Task.category_id)  # uma query agregada em vez de um count() por categoria
    result = []
    for category in Category.list_all():
        data = category.to_dict()
        data['task_count'] = task_counts.get(category.id, 0)
        result.append(data)
    return result


def create_category(data):
    if not data or not isinstance(data, dict):
        raise ValidationError('Dados inválidos')
    if not data.get('name'):
        raise ValidationError('Nome é obrigatório')

    category = Category(
        name=data['name'],
        description=data.get('description', ''),
        color=data.get('color', DEFAULT_CATEGORY_COLOR),
    )
    category.save()
    db.session.commit()
    return category.to_dict()


def update_category(category_id, data):
    category = _get_or_404(category_id)
    if not isinstance(data, dict):
        raise ValidationError('Dados inválidos')
    for field in ('name', 'description', 'color'):
        if field in data:
            setattr(category, field, data[field])
    db.session.commit()
    return category.to_dict()


def delete_category(category_id):
    category = _get_or_404(category_id)
    category.remove()  # o relacionamento Category.tasks anula category_id das tasks no mesmo commit
    db.session.commit()
