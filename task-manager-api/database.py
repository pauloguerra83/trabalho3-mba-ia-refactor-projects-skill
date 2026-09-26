from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utc_now():
    """Agora em UTC, sem tzinfo: mesmo formato que datetime.utcnow() gravava (substitui a API deprecated)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
