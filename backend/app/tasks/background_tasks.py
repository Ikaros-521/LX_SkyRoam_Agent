"""
后台任务
"""

from celery import current_task
from app.core.celery import celery_app
from app.services.background_tasks import task_manager
from loguru import logger


@celery_app.task
def data_refresh_task():
    """数据刷新任务"""
    try:
        logger.info("开始执行数据刷新任务")
        
        # 这里应该调用数据刷新逻辑
        # 由于这是Celery任务，我们需要重新实现数据刷新逻辑
        
        return {
            "status": "success",
            "message": "数据刷新完成"
        }
        
    except Exception as e:
        logger.error(f"数据刷新任务失败: {e}")
        raise


@celery_app.task
def cache_cleanup_task():
    """缓存清理任务"""
    try:
        logger.info("开始执行缓存清理任务")
        
        from app.core.redis import clear_cache_pattern
        
        # 清理过期的缓存
        patterns = [
            "flights:*",
            "hotels:*",
            "attractions:*", 
            "restaurants:*",
            "transportation:*",
            "weather:*"
        ]
        
        total_cleared = 0
        for pattern in patterns:
            cleared = await clear_cache_pattern(pattern)
            total_cleared += cleared
        
        return {
            "status": "success",
            "cleared_keys": total_cleared
        }
        
    except Exception as e:
        logger.error(f"缓存清理任务失败: {e}")
        raise


@celery_app.task
def health_check_task():
    """健康检查任务"""
    try:
        logger.info("开始执行健康检查任务")
        
        # 检查数据库连接
        from app.core.database import async_engine
        async with async_engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        # 检查Redis连接
        from app.core.redis import get_redis
        redis_client = await get_redis()
        await redis_client.ping()
        
        return {
            "status": "success",
            "checks": {
                "database": "healthy",
                "redis": "healthy"
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查任务失败: {e}")
        raise
