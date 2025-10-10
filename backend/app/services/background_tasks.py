"""
后台任务服务
"""

import asyncio
from typing import Dict, Any
from loguru import logger
from datetime import datetime, timedelta

from app.core.redis import get_redis, clear_cache_pattern
from app.services.data_collector import DataCollector


class BackgroundTaskManager:
    """后台任务管理器"""
    
    def __init__(self):
        self.data_collector = DataCollector()
        self.running = False
    
    async def start_tasks(self):
        """启动所有后台任务"""
        if self.running:
            logger.warning("后台任务已在运行")
            return
        
        self.running = True
        logger.info("启动后台任务管理器")
        
        # 启动各种后台任务（非阻塞）
        asyncio.create_task(self.cache_cleanup_task())
        asyncio.create_task(self.data_refresh_task())
        asyncio.create_task(self.health_check_task())
        asyncio.create_task(self.monitoring_task())
        
        logger.info("后台任务已启动")
    
    async def stop_tasks(self):
        """停止所有后台任务"""
        self.running = False
        logger.info("停止后台任务管理器")
    
    async def cache_cleanup_task(self):
        """缓存清理任务"""
        while self.running:
            try:
                logger.info("执行缓存清理任务")
                
                # 清理过期的缓存
                redis_client = await get_redis()
                
                # 清理过期的航班缓存
                await clear_cache_pattern("flights:*")
                
                # 清理过期的酒店缓存
                await clear_cache_pattern("hotels:*")
                
                # 清理过期的天气缓存
                await clear_cache_pattern("weather:*")
                
                logger.info("缓存清理完成")
                
                # 每小时执行一次
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"缓存清理任务失败: {e}")
                # 任务失败时继续运行，避免阻塞
                await asyncio.sleep(300)  # 5分钟后重试
    
    async def data_refresh_task(self):
        """数据刷新任务"""
        while self.running:
            try:
                logger.info("执行数据刷新任务")
                
                # 刷新热门目的地的数据（减少数量，避免阻塞）
                popular_destinations = [
                    "北京", "上海", "广州", "深圳", "杭州"
                ]
                
                for destination in popular_destinations:
                    if not self.running:  # 检查是否仍在运行
                        break
                        
                    try:
                        # 并行刷新数据，提高效率
                        tasks = [
                            self.data_collector.collect_attraction_data(destination),
                            self.data_collector.collect_restaurant_data(destination),
                            self.data_collector.collect_transportation_data(destination)
                        ]
                        
                        await asyncio.gather(*tasks, return_exceptions=True)
                        logger.info(f"已刷新 {destination} 的数据")
                        
                        # 避免请求过于频繁
                        await asyncio.sleep(5)
                        
                    except Exception as e:
                        logger.error(f"刷新 {destination} 数据失败: {e}")
                        # 继续处理下一个目的地
                        continue
                
                logger.info("数据刷新完成")
                
                # 每天执行一次
                await asyncio.sleep(86400)
                
            except Exception as e:
                logger.error(f"数据刷新任务失败: {e}")
                # 任务失败时继续运行，避免阻塞
                await asyncio.sleep(1800)  # 30分钟后重试
    
    async def health_check_task(self):
        """健康检查任务"""
        while self.running:
            try:
                logger.info("执行健康检查任务")
                
                # 并行检查各种连接，避免阻塞
                tasks = [
                    self._check_database(),
                    self._check_redis(),
                    self._check_external_apis()
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 检查结果
                success_count = sum(1 for result in results if not isinstance(result, Exception))
                logger.info(f"健康检查完成: {success_count}/{len(tasks)} 项通过")
                
                # 每10分钟执行一次
                await asyncio.sleep(600)
                
            except Exception as e:
                logger.error(f"健康检查失败: {e}")
                # 任务失败时继续运行，避免阻塞
                await asyncio.sleep(300)  # 5分钟后重试
    
    async def monitoring_task(self):
        """监控任务"""
        while self.running:
            try:
                logger.info("执行监控任务")
                
                # 监控系统资源使用情况
                import psutil
                
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # 内存使用率
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                
                # 磁盘使用率
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                
                logger.info(f"系统监控 - CPU: {cpu_percent}%, 内存: {memory_percent}%, 磁盘: {disk_percent}%")
                
                # 如果资源使用率过高，记录警告
                if cpu_percent > 80:
                    logger.warning(f"CPU使用率过高: {cpu_percent}%")
                
                if memory_percent > 80:
                    logger.warning(f"内存使用率过高: {memory_percent}%")
                
                if disk_percent > 90:
                    logger.warning(f"磁盘使用率过高: {disk_percent}%")
                
                # 每5分钟执行一次
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"监控任务失败: {e}")
                await asyncio.sleep(300)  # 5分钟后重试
    
    async def _check_database(self):
        """检查数据库连接"""
        try:
            from app.core.database import async_engine
            from sqlalchemy import text
            async with async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"数据库检查失败: {e}")
            raise
    
    async def _check_redis(self):
        """检查Redis连接"""
        try:
            redis_client = await get_redis()
            await redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis检查失败: {e}")
            raise
    
    async def _check_external_apis(self):
        """检查外部API连接"""
        try:
            # 检查OpenAI API
            from app.core.config import settings
            if settings.OPENAI_API_KEY:
                import openai
                # 这里可以添加简单的API测试
                pass
            
            # 检查天气API
            if settings.WEATHER_API_KEY:
                # 这里可以添加天气API测试
                pass
            
            # 检查其他API
            # ...
            return True
            
        except Exception as e:
            logger.error(f"外部API检查失败: {e}")
            raise


# 全局任务管理器实例
task_manager = BackgroundTaskManager()


async def start_background_tasks():
    """启动后台任务"""
    await task_manager.start_tasks()


async def stop_background_tasks():
    """停止后台任务"""
    await task_manager.stop_tasks()
