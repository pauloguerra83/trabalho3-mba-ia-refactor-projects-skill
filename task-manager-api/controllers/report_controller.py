from datetime import timedelta

from config.constants import HIGH_PRIORITY_MAX, PRIORITY_LABELS, RECENT_ACTIVITY_DAYS, TASK_STATUSES
from database import utc_now
from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User


def _rate(part, total):
    return round((part / total) * 100, 2) if total > 0 else 0


def summary_report():
    now = utc_now()
    by_status = Task.count_by(Task.status)
    by_priority = Task.count_by(Task.priority)

    overdue_list = [
        {
            'id': task.id,
            'title': task.title,
            'due_date': str(task.due_date),
            'days_overdue': (now - task.due_date).days,
        }
        for task in Task.list_all() if task.is_overdue()
    ]

    since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
    totals_by_user = Task.count_by(Task.user_id)
    done_by_user = Task.count_done_by_user()
    user_stats = []
    for user in User.list_all():
        total = totals_by_user.get(user.id, 0)
        completed = done_by_user.get(user.id, 0)
        user_stats.append({
            'user_id': user.id,
            'user_name': user.name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': _rate(completed, total),
        })

    return {
        'generated_at': str(now),
        'overview': {
            'total_tasks': Task.count(),
            'total_users': User.count(),
            'total_categories': Category.count(),
        },
        'tasks_by_status': {status: by_status.get(status, 0) for status in TASK_STATUSES},
        'tasks_by_priority': {label: by_priority.get(p, 0) for p, label in PRIORITY_LABELS.items()},
        'overdue': {
            'count': len(overdue_list),
            'tasks': overdue_list,
        },
        'recent_activity': {
            'tasks_created_last_7_days': Task.count_created_since(since),
            'tasks_completed_last_7_days': Task.count_done_since(since),
        },
        'user_productivity': user_stats,
    }


def user_report(user_id):
    user = User.get_by_id(user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    tasks = Task.list_by_user(user_id)
    counts = {status: 0 for status in TASK_STATUSES}
    for task in tasks:
        if task.status in counts:
            counts[task.status] += 1

    total = len(tasks)
    return {
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
        },
        'statistics': {
            'total_tasks': total,
            'done': counts['done'],
            'pending': counts['pending'],
            'in_progress': counts['in_progress'],
            'cancelled': counts['cancelled'],
            'overdue': sum(1 for task in tasks if task.is_overdue()),
            'high_priority': sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_MAX),
            'completion_rate': _rate(counts['done'], total),
        },
    }
