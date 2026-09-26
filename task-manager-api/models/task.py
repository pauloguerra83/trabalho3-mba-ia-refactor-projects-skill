from sqlalchemy import func
from sqlalchemy.orm import joinedload

from config.constants import CLOSED_STATUSES, DEFAULT_PRIORITY, DEFAULT_TASK_STATUS
from database import db, utc_now


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=DEFAULT_TASK_STATUS)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    def to_dict(self):
        data = {}
        data['id'] = self.id
        data['title'] = self.title
        data['description'] = self.description
        data['status'] = self.status
        data['priority'] = self.priority
        data['user_id'] = self.user_id
        data['category_id'] = self.category_id
        data['created_at'] = str(self.created_at)
        data['updated_at'] = str(self.updated_at)
        data['due_date'] = str(self.due_date) if self.due_date else None
        data['tags'] = self.tags.split(',') if self.tags else []
        return data

    def is_overdue(self):
        return bool(self.due_date) and self.due_date < utc_now() and self.status not in CLOSED_STATUSES

    # --- acesso a dados ---

    @classmethod
    def get_by_id(cls, task_id):
        return db.session.get(cls, task_id)

    @classmethod
    def list_all(cls):
        return db.session.execute(db.select(cls).order_by(cls.id)).scalars().all()

    @classmethod
    def list_all_with_relations(cls):
        stmt = db.select(cls).options(joinedload(cls.user), joinedload(cls.category)).order_by(cls.id)
        return db.session.execute(stmt).scalars().all()

    @classmethod
    def list_by_user(cls, user_id):
        return db.session.execute(db.select(cls).filter_by(user_id=user_id).order_by(cls.id)).scalars().all()

    @classmethod
    def search(cls, text=None, status=None, priority=None, user_id=None):
        stmt = db.select(cls)
        if text:
            stmt = stmt.where(db.or_(cls.title.like(f'%{text}%'), cls.description.like(f'%{text}%')))
        if status:
            stmt = stmt.where(cls.status == status)
        if priority is not None:
            stmt = stmt.where(cls.priority == priority)
        if user_id is not None:
            stmt = stmt.where(cls.user_id == user_id)
        return db.session.execute(stmt.order_by(cls.id)).scalars().all()

    @classmethod
    def count(cls):
        return db.session.scalar(db.select(func.count(cls.id)))

    @classmethod
    def count_by(cls, column):
        """{valor da coluna: quantidade de tasks} em uma única query (GROUP BY)."""
        rows = db.session.execute(db.select(column, func.count(cls.id)).group_by(column)).all()
        return {value: total for value, total in rows}

    @classmethod
    def count_done_by_user(cls):
        stmt = db.select(cls.user_id, func.count(cls.id)).where(cls.status == 'done').group_by(cls.user_id)
        return {user_id: total for user_id, total in db.session.execute(stmt).all()}

    @classmethod
    def count_created_since(cls, since):
        return db.session.scalar(db.select(func.count(cls.id)).where(cls.created_at >= since))

    @classmethod
    def count_done_since(cls, since):
        return db.session.scalar(
            db.select(func.count(cls.id)).where(cls.status == 'done', cls.updated_at >= since)
        )

    def save(self):
        db.session.add(self)

    def remove(self):
        db.session.delete(self)
