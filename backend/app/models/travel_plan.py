"""
旅行计划模型
"""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel


class TravelPlan(BaseModel):
    """旅行计划模型"""
    __tablename__ = "travel_plans"
    
    # 基本信息
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # 旅行参数
    destination = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    duration_days = Column(Integer, nullable=False)
    budget = Column(Float, nullable=True)
    
    # 用户偏好
    preferences = Column(JSON, nullable=True)  # 存储用户偏好设置
    requirements = Column(JSON, nullable=True)  # 存储特殊要求
    
    # 方案数据
    generated_plans = Column(JSON, nullable=True)  # 存储生成的多个方案
    selected_plan = Column(JSON, nullable=True)    # 用户选择的最终方案
    
    # 状态
    status = Column(String(20), default="draft", nullable=False)  # draft, generating, completed, archived
    score = Column(Float, nullable=True)  # 方案评分
    
    # 关联关系
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="travel_plans")
    
    items = relationship("TravelPlanItem", back_populates="travel_plan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TravelPlan(title={self.title}, destination={self.destination})>"


class TravelPlanItem(BaseModel):
    """旅行计划项目模型"""
    __tablename__ = "travel_plan_items"
    
    # 基本信息
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    item_type = Column(String(50), nullable=False)  # flight, hotel, attraction, restaurant, transport
    
    # 时间安排
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_hours = Column(Float, nullable=True)
    
    # 位置信息
    location = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    coordinates = Column(JSON, nullable=True)  # {"lat": 0, "lng": 0}
    
    # 详细信息
    details = Column(JSON, nullable=True)  # 存储具体信息（价格、评分、联系方式等）
    images = Column(JSON, nullable=True)   # 存储图片URL列表
    
    # 关联关系
    travel_plan_id = Column(Integer, ForeignKey("travel_plans.id"), nullable=False)
    travel_plan = relationship("TravelPlan", back_populates="items")
    
    def __repr__(self):
        return f"<TravelPlanItem(title={self.title}, type={self.item_type})>"
