"""
LX SkyRoam Agent - 主应用入口
智能旅游攻略生成系统
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router
from app.core.redis import init_redis
from app.services.background_tasks import start_background_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("🚀 启动 LX SkyRoam Agent...")
    
    # 初始化数据库
    await init_db()
    logger.info("✅ 数据库初始化完成")
    
    # 初始化Redis
    await init_redis()
    logger.info("✅ Redis初始化完成")
    
    # 启动后台任务
    await start_background_tasks()
    logger.info("✅ 后台任务启动完成")
    
    yield
    
    # 关闭时清理
    logger.info("🛑 关闭 LX SkyRoam Agent...")


# 创建FastAPI应用
app = FastAPI(
    title="LX SkyRoam Agent",
    description="智能旅游攻略生成系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# 注册API路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "LX SkyRoam Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "LX SkyRoam Agent",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
