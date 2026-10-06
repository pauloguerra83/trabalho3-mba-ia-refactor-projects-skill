TASK_STATUSES = ['pending', 'in_progress', 'done', 'cancelled']
CLOSED_STATUSES = ('done', 'cancelled')  # tasks nesses status nunca ficam atrasadas
DEFAULT_TASK_STATUS = 'pending'

PRIORITY_MIN = 1
PRIORITY_MAX = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_MAX = 2  # prioridades 1 e 2 contam como "alta" no relatório por usuário
PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}

TITLE_MIN_LENGTH = 3
TITLE_MAX_LENGTH = 200

USER_ROLES = ['user', 'admin', 'manager']
DEFAULT_ROLE = 'user'
PASSWORD_MIN_LENGTH = 4
EMAIL_REGEX = r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'

DEFAULT_CATEGORY_COLOR = '#000000'
RECENT_ACTIVITY_DAYS = 7
