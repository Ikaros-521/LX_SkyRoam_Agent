"""
用户API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_async_db
from app.models.user import User
# 新增导入
from app.core.security import get_current_user, is_admin, verify_password, get_password_hash
from app.schemas.auth import UserOut, UserUpdate, ChangePassword, AdminUserUpdate, AdminResetPassword

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


@router.get("/me", response_model=UserOut)
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


@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """更新当前用户资料（邮箱、姓名）"""
    from sqlalchemy import select, and_

    # 邮箱唯一性校验（如果提供了且变更了）
    if payload.email is not None and payload.email != current_user.email:
        email_exists = await db.execute(
            select(User).where(and_(User.email == payload.email, User.id != current_user.id))
        )
        if email_exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已被占用")
        current_user.email = payload.email

    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    payload: ChangePassword,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """修改当前用户密码，需验证旧密码"""
    # 验证旧密码
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    # 更新为新密码哈希
    current_user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
    return {"message": "密码已更新"}


@router.patch("/{user_id}")
async def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """管理员更新用户资料（用户名/邮箱/姓名）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可更新用户")
    from sqlalchemy import select, and_

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 用户名唯一性校验
    if payload.username is not None and payload.username != user.username:
        username_exists = await db.execute(
            select(User).where(and_(User.username == payload.username, User.id != user_id))
        )
        if username_exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="用户名已被占用")
        user.username = payload.username

    # 邮箱唯一性校验
    if payload.email is not None and payload.email != user.email:
        email_exists = await db.execute(
            select(User).where(and_(User.email == payload.email, User.id != user_id))
        )
        if email_exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已被占用")
        user.email = payload.email

    if payload.full_name is not None:
        user.full_name = payload.full_name

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    payload: AdminResetPassword,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """管理员重置用户密码"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可重置密码")
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
    return {"message": "密码已重置"}


@router.delete("/{user_id}")
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """管理员删除用户（级联删除其旅行计划）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可删除用户")
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    await db.delete(user)
    await db.commit()
    return {"message": "用户已删除"}
