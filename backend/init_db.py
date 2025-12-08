#!/usr/bin/env python3
"""
数据库初始化脚本

用法:
    python init_db.py                    # 智能创建表（默认，推荐）- 检查表是否存在，不存在则创建
    python init_db.py --alembic          # 使用 Alembic 迁移
    python init_db.py --force            # 强制创建所有表（即使已存在）
    python init_db.py --no-migration     # 跳过表创建，仅插入种子数据
"""

import asyncio
import sys
import os
import argparse

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import init_db
from app.core.logging_config import setup_logging
from loguru import logger

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库初始化脚本")
    parser.add_argument(
        "--alembic",
        action="store_true",
        help="使用 Alembic 迁移（不推荐，可能有迁移历史问题）"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制创建所有表（即使已存在，可能会报错）"
    )
    parser.add_argument(
        "--no-migration",
        action="store_true",
        help="跳过表创建，仅插入种子数据"
    )
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    
    try:
        logger.info("🚀 开始初始化数据库...")
        
        if args.no_migration:
            # 仅插入种子数据
            from app.core.database import seed_initial_data
            await seed_initial_data()
            logger.info("✅ 种子数据插入完成！")
        else:
            # 运行完整的初始化流程
            if args.alembic:
                # 使用 Alembic 迁移
                await init_db(use_alembic=True, create_tables_directly=False)
            elif args.force:
                # 强制创建所有表
                from app.core.database import create_tables_directly, seed_initial_data, create_database_if_not_exists
                await create_database_if_not_exists()
                await create_tables_directly()
                await seed_initial_data()
            else:
                # 默认：智能创建表（检查表是否存在，不存在则创建）
                await init_db(use_alembic=False, create_tables_directly=True)
            logger.info("✅ 数据库初始化完成！")
            
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
