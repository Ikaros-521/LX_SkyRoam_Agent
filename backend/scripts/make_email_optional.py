#!/usr/bin/env python3
"""
将 users.email 列改为可空（DROP NOT NULL），以支持注册时不填写邮箱。
使用应用的异步数据库引擎执行 DDL。

Usage:
  python scripts/make_email_optional.py
"""
import asyncio
import os
import sys
from sqlalchemy import text
from loguru import logger

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.append(backend_root)

from app.core.database import async_engine

async def make_email_nullable():
    try:
        async with async_engine.begin() as conn:
            # 检查列当前是否为 NOT NULL（PostgreSQL）
            check_sql = text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='email'
            """)
            result = await conn.execute(check_sql)
            row = result.fetchone()
            if row and row[0] == 'NO':
                await conn.execute(text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))
                logger.info("✅ 已将 users.email 改为可空 (DROP NOT NULL)")
            else:
                logger.info("✅ users.email 已是可空，无需修改")
    except Exception as e:
        logger.error(f"❌ 修改列可空性失败: {e}")
        raise

async def main():
    await make_email_nullable()

if __name__ == "__main__":
    asyncio.run(main())