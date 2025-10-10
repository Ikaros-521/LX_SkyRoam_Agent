#!/usr/bin/env python3
"""
数据库初始化脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import init_db
from loguru import logger

async def main():
    """主函数"""
    try:
        logger.info("🚀 开始初始化数据库...")
        await init_db()
        logger.info("✅ 数据库初始化完成！")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
