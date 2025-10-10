"""
目的地相关模型
"""

from sqlalchemy import Column, String, Text, Float, Integer, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Destination(BaseModel):
    """目的地模型"""
    __tablename__ = "destinations"
    
    # 基本信息
    name = Column(String(100), nullable=False, index=True)
    country = Column(String(100), nullable=False)
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    
    # 地理信息
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(String(50), nullable=True)
    
    # 描述信息
    description = Column(Text, nullable=True)
    highlights = Column(JSON, nullable=True)  # 主要亮点
    best_time_to_visit = Column(String(200), nullable=True)
    
    # 统计信息
    popularity_score = Column(Float, default=0.0, nullable=False)
    safety_score = Column(Float, nullable=True)
    cost_level = Column(String(20), nullable=True)  # low, medium, high
    
    # 媒体资源
    images = Column(JSON, nullable=True)  # 图片URL列表
    videos = Column(JSON, nullable=True)  # 视频URL列表
    
    # 关联关系
    attractions = relationship("Attraction", back_populates="destination", cascade="all, delete-orphan")
    restaurants = relationship("Restaurant", back_populates="destination", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Destination(name={self.name}, country={self.country})>"


class Attraction(BaseModel):
    """景点模型"""
    __tablename__ = "attractions"
    
    # 基本信息
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # museum, park, landmark, etc.
    description = Column(Text, nullable=True)
    
    # 位置信息
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # 营业信息
    opening_hours = Column(JSON, nullable=True)  # 营业时间
    ticket_price = Column(Float, nullable=True)
    currency = Column(String(10), default="CNY", nullable=False)
    
    # 评分信息
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0, nullable=False)
    
    # 详细信息
    features = Column(JSON, nullable=True)  # 特色功能
    accessibility = Column(JSON, nullable=True)  # 无障碍设施
    contact_info = Column(JSON, nullable=True)  # 联系方式
    
    # 媒体资源
    images = Column(JSON, nullable=True)
    website = Column(String(500), nullable=True)
    
    # 关联关系
    destination_id = Column(Integer, ForeignKey("destinations.id"), nullable=False)
    destination = relationship("Destination", back_populates="attractions")
    
    def __repr__(self):
        return f"<Attraction(name={self.name}, category={self.category})>"


class Restaurant(BaseModel):
    """餐厅模型"""
    __tablename__ = "restaurants"
    
    # 基本信息
    name = Column(String(200), nullable=False, index=True)
    cuisine_type = Column(String(100), nullable=False)  # 菜系类型
    description = Column(Text, nullable=True)
    
    # 位置信息
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # 营业信息
    opening_hours = Column(JSON, nullable=True)
    price_range = Column(String(20), nullable=True)  # $, $$, $$$, $$$$
    
    # 评分信息
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0, nullable=False)
    
    # 详细信息
    features = Column(JSON, nullable=True)  # 特色（外卖、预订等）
    contact_info = Column(JSON, nullable=True)
    menu_highlights = Column(JSON, nullable=True)  # 招牌菜
    
    # 媒体资源
    images = Column(JSON, nullable=True)
    website = Column(String(500), nullable=True)
    
    # 关联关系
    destination_id = Column(Integer, ForeignKey("destinations.id"), nullable=False)
    destination = relationship("Destination", back_populates="restaurants")
    
    def __repr__(self):
        return f"<Restaurant(name={self.name}, cuisine_type={self.cuisine_type})>"
