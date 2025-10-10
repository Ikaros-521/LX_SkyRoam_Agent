"""
用户模型
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel


class User(BaseModel):
    """用户模型"""
    __tablename__ = "users"
    
    # 基本信息
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    
    # 认证信息
    hashed_password = Column(String(255), nullable=False)
    
    # 用户偏好
    preferences = Column(Text, nullable=True)  # JSON格式存储偏好设置
    travel_history = Column(Text, nullable=True)  # JSON格式存储旅行历史
    
    # 账户状态
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # 关联关系
    travel_plans = relationship("TravelPlan", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        try:
            # 安全地获取属性，避免触发懒加载
            obj_id = getattr(self, 'id', 'N/A')
            return f"<User(id={obj_id})>"
        except Exception:
            return f"<User(instance)>"
