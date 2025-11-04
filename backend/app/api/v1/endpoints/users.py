"""
用户API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_async_db
from app.models.user import User
# 新增导入
from app.core.security import get_current_user, is_admin

router = APIRouter()


@router.get("/")
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户列表（仅管理员）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可查看用户列表")
    from sqlalchemy import select
    
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    
    return users


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个用户（管理员或本人）"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.travel_plans))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if not (is_admin(current_user) or current_user.id == user_id):
        raise HTTPException(status_code=403, detail="仅管理员或本人可查看该信息")
    
    return user
