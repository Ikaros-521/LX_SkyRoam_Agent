"""
认证与用户会话API端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import timedelta

from app.core.database import get_async_db
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, Token, UserOut

router = APIRouter()


@router.post("/register", response_model=UserOut)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_async_db)):
    # 动态构建唯一性检查：用户名必查，邮箱在提供时才检查
    filters = [User.username == user_in.username]
    if user_in.email is not None:
        filters.append(User.email == user_in.email)

    existing = await db.execute(select(User).where(or_(*filters)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

    # 如果 email 为 None，生成一个默认的 email（使用 example.com 作为示例域名）
    email = user_in.email
    if email is None:
        email = f"{user_in.username}@example.com"

    user = User(
        username=user_in.username,
        email=email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role='user',
        is_verified=True,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(form: UserLogin, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    access_token = create_access_token(
        data={"sub": str(user.id)},
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user