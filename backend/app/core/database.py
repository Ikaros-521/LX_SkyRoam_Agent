"""
数据库配置和连接管理
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from loguru import logger

from app.core.config import settings

# 创建异步数据库引擎
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=300
)

# 创建同步数据库引擎（用于迁移等）
sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=300
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# 创建同步会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# 创建基础模型类
Base = declarative_base()

# 元数据
metadata = MetaData()


async def get_async_db():
    """获取异步数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话错误: {e}")
            raise
        finally:
            await session.close()


def get_sync_db():
    """获取同步数据库会话"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"数据库会话错误: {e}")
        raise
    finally:
        db.close()


async def init_db():
    """初始化数据库"""
    try:
        # 导入所有模型以确保它们被注册
        from app.models import user, travel_plan, destination, activity
        
        # 创建所有表
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ 数据库表创建成功")
        
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


async def close_db():
    """关闭数据库连接"""
    await async_engine.dispose()
    sync_engine.dispose()
    logger.info("✅ 数据库连接已关闭")
