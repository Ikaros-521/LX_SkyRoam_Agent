"""
旅行计划数据模式
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TravelPlanBase(BaseModel):
    """旅行计划基础模式"""
    title: str = Field(..., description="计划标题")
    description: Optional[str] = Field(None, description="计划描述")
    destination: str = Field(..., description="目的地")
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")
    duration_days: int = Field(..., description="旅行天数")
    budget: Optional[float] = Field(None, description="预算")
    preferences: Optional[Dict[str, Any]] = Field(None, description="用户偏好")
    requirements: Optional[Dict[str, Any]] = Field(None, description="特殊要求")


class TravelPlanCreate(TravelPlanBase):
    """创建旅行计划模式"""
    user_id: int = Field(..., description="用户ID")


class TravelPlanUpdate(BaseModel):
    """更新旅行计划模式"""
    title: Optional[str] = None
    description: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: Optional[int] = None
    budget: Optional[float] = None
    preferences: Optional[Dict[str, Any]] = None
    requirements: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class TravelPlanItemResponse(BaseModel):
    """旅行计划项目响应模式"""
    id: int
    title: str
    description: Optional[str] = None
    item_type: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_hours: Optional[float] = None
    location: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    details: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TravelPlanResponse(TravelPlanBase):
    """旅行计划响应模式"""
    id: int
    user_id: int
    status: str
    score: Optional[float] = None
    generated_plans: Optional[List[Dict[str, Any]]] = None
    selected_plan: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    items: List[TravelPlanItemResponse] = []

    class Config:
        from_attributes = True


class TravelPlanGenerateRequest(BaseModel):
    """生成旅行方案请求模式"""
    preferences: Optional[Dict[str, Any]] = Field(None, description="生成偏好")
    requirements: Optional[Dict[str, Any]] = Field(None, description="特殊要求")
    num_plans: int = Field(3, description="生成方案数量", ge=1, le=10)


class TravelPlanListResponse(BaseModel):
    """旅行计划列表响应模式"""
    plans: List[TravelPlanResponse]
    total: int
    page: int
    page_size: int


class TravelPlanExportRequest(BaseModel):
    """导出旅行计划请求模式"""
    format: str = Field("pdf", description="导出格式", regex="^(pdf|json|html)$")
    include_images: bool = Field(True, description="是否包含图片")
    include_map: bool = Field(True, description="是否包含地图")
    language: str = Field("zh", description="导出语言")
