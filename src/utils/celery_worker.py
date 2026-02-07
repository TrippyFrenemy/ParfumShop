from celery import Celery
from celery.schedules import crontab
from src.config import settings

celery_app = Celery(
    "tasks",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
    include=["src.tasks.backup", "src.tasks.cleanup", "src.tasks.reporting", "src.tasks.notifications"]
)

celery_app.conf.broker_transport_options = {
    "visibility_timeout": 3600,
    "socket_keepalive": True,
    "retry_on_timeout": True,
    "max_retries": 3
}

celery_app.conf.timezone = "Europe/Kyiv"
celery_app.conf.beat_schedule = {
    "backup-every-12-hours": {
        "task": "src.tasks.backup.send_db_backup_task",
        "schedule": crontab(hour='8-21', minute=0),
    },
    "clean-old-logs-daily": {
        "task": "src.tasks.cleanup.clean_old_logs",
        "schedule": crontab(hour=0, minute=0),
    },

}