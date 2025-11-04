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
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量文件: {env_path}")
else:
    print(f"⚠️ 环境变量文件不存在: {env_path}")

from app.core.config import settings
from app.core.logging_config import setup_logging

# 初始化日志系统
logger = setup_logging()
from app.core.database import init_db
from app.api.v1.api import api_router
from app.core.redis import init_redis
from app.services.background_tasks import start_background_tasks
from app.core.rate_limit import RateLimitMiddleware


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
