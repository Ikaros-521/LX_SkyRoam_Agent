"""
Redis配置和连接管理
"""

import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from loguru import logger

from app.core.config import settings

# Redis连接池
redis_pool: ConnectionPool = None
redis_client: redis.Redis = None


async def init_redis():
    """初始化Redis连接"""
    global redis_pool, redis_client
    
    try:
        # 创建连接池
        redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            max_connections=20,
            retry_on_timeout=True
        )
        
        # 创建Redis客户端
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        # 测试连接
        await redis_client.ping()
        logger.info("✅ Redis连接成功")
        
    except Exception as e:
        logger.error(f"❌ Redis连接失败: {e}")
        raise


async def get_redis() -> redis.Redis:
    """获取Redis客户端"""
    if redis_client is None:
        await init_redis()
    return redis_client


async def close_redis():
    """关闭Redis连接"""
    global redis_client, redis_pool
    
    if redis_client:
        await redis_client.close()
        redis_client = None
    
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None
    
    logger.info("✅ Redis连接已关闭")


# 缓存装饰器
def cache_key(prefix: str, *args, **kwargs):
    """生成缓存键"""
    key_parts = [prefix]
    
    # 添加位置参数
    for arg in args:
        key_parts.append(str(arg))
    
    # 添加关键字参数
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")
    
    return ":".join(key_parts)


async def get_cache(key: str):
    """获取缓存"""
    try:
        client = await get_redis()
        value = await client.get(key)
        if value:
            import json
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"获取缓存失败: {e}")
        return None


async def set_cache(key: str, value, ttl: int = None):
    """设置缓存"""
    try:
        client = await get_redis()
        import json
        json_value = json.dumps(value, ensure_ascii=False)
        
        if ttl is None:
            ttl = settings.CACHE_TTL
        
        await client.setex(key, ttl, json_value)
        return True
    except Exception as e:
        logger.error(f"设置缓存失败: {e}")
        return False


async def delete_cache(key: str):
    """删除缓存"""
    try:
        client = await get_redis()
        await client.delete(key)
        return True
    except Exception as e:
        logger.error(f"删除缓存失败: {e}")
        return False


async def clear_cache_pattern(pattern: str):
    """清除匹配模式的缓存"""
    try:
        client = await get_redis()
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
        return len(keys)
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        return 0


def clear_cache_pattern_sync(pattern: str):
    """清除匹配模式的缓存 (同步版本，用于Celery任务)"""
    import asyncio
    try:
        # 在同步环境中运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(clear_cache_pattern(pattern))
            return result
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"清除缓存失败 (同步版本): {e}")
        return 0
