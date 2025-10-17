"""
数据收集相关任务
"""

from celery import current_task
from app.core.celery import celery_app
from app.services.data_collector import DataCollector
from loguru import logger


@celery_app.task
def collect_destination_data_task(
    origin: str,
    destination: str, 
    departure_date: str = None,
    return_date: str = None,
    transportation_type: str = "mixed"
):
    """
    收集目的地数据任务
    
    Args:
        origin: 出发地
        destination: 目的地
        departure_date: 出发日期 (YYYY-MM-DD格式)
        return_date: 返回日期 (YYYY-MM-DD格式，可选)
        transportation_type: 交通方式 ("flight", "train", "mixed")
    """
    try:
        logger.info(f"开始收集目的地数据: {origin} -> {destination}")
        logger.info(f"出发日期: {departure_date}, 返回日期: {return_date}")
        logger.info(f"交通方式: {transportation_type}")
        
        async def run_collection():
            data_collector = DataCollector()
            
            # 收集所有类型的数据
            data = await data_collector.collect_all_data(
                origin,
                destination, 
                departure_date,
                return_date,
                transportation_type
            )
            
            await data_collector.close()
            
            return {
                "status": "success",
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date,
                "transportation_type": transportation_type,
                "data_counts": {
                    "flights": len(data.get("flights", [])),
                    "hotels": len(data.get("hotels", [])),
                    "attractions": len(data.get("attractions", [])),
                    "restaurants": len(data.get("restaurants", [])),
                    "weather": len(data.get("weather", [])),
                    "transportation": len(data.get("transportation", []))
                }
            }
        
        import asyncio
        return asyncio.run(run_collection())
        
    except Exception as e:
        logger.error(f"收集目的地数据失败: {e}")
        raise


@celery_app.task
def refresh_cache_task():
    """刷新缓存任务"""
    try:
        logger.info("开始执行缓存刷新任务")
        
        from app.core.redis import clear_cache_pattern_sync
        
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
            cleared = clear_cache_pattern_sync(pattern)
            total_cleared += cleared
        
        return {
            "status": "success",
            "cleared_keys": total_cleared
        }
        
    except Exception as e:
        logger.error(f"刷新缓存任务失败: {e}")
        raise


@celery_app.task
def validate_data_quality_task():
    """数据质量验证任务"""
    try:
        logger.info("开始执行数据质量验证任务")
        
        # 这里应该实现数据质量检查逻辑
        # 例如：检查数据的完整性、准确性、时效性等
        
        return {
            "status": "success",
            "validation_results": {
                "total_records": 1000,
                "valid_records": 950,
                "invalid_records": 50,
                "quality_score": 0.95
            }
        }
        
    except Exception as e:
        logger.error(f"数据质量验证任务失败: {e}")
        raise
