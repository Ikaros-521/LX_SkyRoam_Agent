"""
LX SkyRoam Agent - 主应用入口
智能旅游攻略生成系统
"""

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.database import init_db
from app.api.v1.api import api_router
from app.core.redis import init_redis
from app.services.background_tasks import start_background_tasks
from app.core.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger = setup_logging()
    logger.info("🚀 启动 LX SkyRoam Agent...")
    
    # 初始化数据库（智能检查表是否存在，不存在则创建）
    await init_db(use_alembic=False, create_tables_directly=True)
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
    logger.info("✅ 应用关闭完成")


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

# 限流中间件（按IP）
app.add_middleware(RateLimitMiddleware)

# 挂载静态文件目录（用于图片等静态资源）
# 优先挂载静态文件路由，确保在文件不存在时能正确返回404，而不是被后续中间件或路由错误处理
STATIC_DIR = Path(__file__).parent / "uploads"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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
    # 通过命令行参数传递host和port
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=settings.DEBUG,
        log_level="info"
    )
