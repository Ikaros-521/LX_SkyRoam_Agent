"""
Celery配置
"""

from celery import Celery
from app.core.config import settings

# 创建Celery应用
celery_app = Celery(
    "lx_skyroam_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.travel_plan_tasks",
        "app.tasks.data_collection_tasks",
        "app.tasks.background_tasks"
    ]
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟
    task_soft_time_limit=25 * 60,  # 25分钟
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1小时
)

# 定时任务配置
celery_app.conf.beat_schedule = {
    "data-refresh-task": {
        "task": "app.tasks.background_tasks.data_refresh_task",
        "schedule": 86400.0,  # 每天执行一次
    },
    "cache-cleanup-task": {
        "task": "app.tasks.background_tasks.cache_cleanup_task", 
        "schedule": 3600.0,  # 每小时执行一次
    },
    "health-check-task": {
        "task": "app.tasks.background_tasks.health_check_task",
        "schedule": 600.0,  # 每10分钟执行一次
    },
}
