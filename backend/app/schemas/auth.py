"""
认证相关的Pydantic模式
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=6, max_length=128)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: str
    is_verified: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用户资料更新请求体"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class ChangePassword(BaseModel):
    """用户修改密码请求体"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class AdminUserUpdate(BaseModel):
    """管理员更新用户资料（支持更新用户名/邮箱/姓名）"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class AdminResetPassword(BaseModel):
    """管理员重置用户密码"""
    new_password: str = Field(..., min_length=6, max_length=128)