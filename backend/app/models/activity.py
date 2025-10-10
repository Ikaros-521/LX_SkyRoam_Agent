"""
活动相关模型
"""

from sqlalchemy import Column, String, Text, Float, Integer, JSON, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel


class ActivityType(BaseModel):
    """活动类型模型"""
    __tablename__ = "activity_types"
    
    # 基本信息
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # outdoor, indoor, cultural, adventure, etc.
    
    # 特征信息
    duration_range = Column(JSON, nullable=True)  # {"min": 1, "max": 8} 小时
    difficulty_level = Column(String(20), nullable=True)  # easy, medium, hard
    age_restriction = Column(JSON, nullable=True)  # 年龄限制
    
    # 关联关系
    activities = relationship("Activity", back_populates="activity_type", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ActivityType(name={self.name}, category={self.category})>"


class Activity(BaseModel):
    """活动模型"""
    __tablename__ = "activities"
    
    # 基本信息
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # 位置信息
    location = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # 时间信息
    duration_hours = Column(Float, nullable=True)
    best_time = Column(String(100), nullable=True)  # 最佳时间
    seasonal_availability = Column(JSON, nullable=True)  # 季节性可用性
    
    # 价格信息
    price = Column(Float, nullable=True)
    currency = Column(String(10), default="CNY", nullable=False)
    price_includes = Column(JSON, nullable=True)  # 价格包含项目
    
    # 评分信息
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0, nullable=False)
    
    # 详细信息
    requirements = Column(JSON, nullable=True)  # 参与要求
    equipment_needed = Column(JSON, nullable=True)  # 所需装备
    safety_notes = Column(Text, nullable=True)  # 安全注意事项
    
    # 媒体资源
    images = Column(JSON, nullable=True)
    videos = Column(JSON, nullable=True)
    website = Column(String(500), nullable=True)
    
    # 关联关系
    activity_type_id = Column(Integer, ForeignKey("activity_types.id"), nullable=False)
    activity_type = relationship("ActivityType", back_populates="activities")
    
    def __repr__(self):
        return f"<Activity(name={self.name}, type={self.activity_type.name if self.activity_type else 'Unknown'})>"
