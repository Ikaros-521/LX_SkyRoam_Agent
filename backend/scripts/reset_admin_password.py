#!/usr/bin/env python3
"""
Reset admin password using PostgreSQL pgcrypto (bcrypt) directly,
avoiding local passlib/bcrypt backend issues.

Usage:
  python scripts/reset_admin_password.py --password "Admin@123"
If --password is not provided, defaults to "Admin@123".

python scripts/reset_admin_password.py --password "Admin@123"
"""
import asyncio
import argparse
import os
import sys
from sqlalchemy import text
from loguru import logger

# Ensure backend root on sys.path
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.append(backend_root)

# Import DB engine
from app.core.database import async_engine

async def reset_password(new_password: str):
    try:
        async with async_engine.begin() as conn:
            # Ensure pgcrypto extension exists
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            # Update admin by id=1 or username='admin'
            await conn.execute(
                text(
                    "UPDATE users SET hashed_password = crypt(:pwd, gen_salt('bf')) "
                    "WHERE id = 1 OR username = 'admin'"
                ),
                {"pwd": new_password},
            )
        logger.info("✅ 管理员密码已重置为新的 bcrypt 值")
    except Exception as e:
        logger.error(f"❌ 重置密码失败: {e}")
        raise

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", type=str, default="Admin@123")
    args = parser.parse_args()
    await reset_password(args.password)

if __name__ == "__main__":
    asyncio.run(main())