"""
旅行计划数据模式
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class TravelPlanBase(BaseModel):
    """旅行计划基础模式"""
    title: str = Field(..., description="计划标题")
    description: Optional[str] = Field(None, description="计划描述")
    destination: str = Field(..., description="目的地")
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")
    
    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        """解析日期时间，确保无时区信息"""
        if isinstance(v, str):
            # 解析字符串格式的日期时间
            try:
                # 尝试解析带时区的格式
                if 'T' in v or '+' in v or 'Z' in v:
                    dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                    # 转换为无时区的本地时间
                    return dt.replace(tzinfo=None)
                else:
                    # 解析无时区格式
                    return datetime.fromisoformat(v)
            except ValueError:
                # 如果解析失败，尝试其他格式
                from dateutil import parser
                dt = parser.parse(v)
                return dt.replace(tzinfo=None)
        return v
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
    items: Optional[List[TravelPlanItemResponse]] = None

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        """自定义ORM转换，避免懒加载问题"""
        data = {
            'id': obj.id,
            'title': obj.title,
            'description': obj.description,
            'destination': obj.destination,
            'start_date': obj.start_date,
            'end_date': obj.end_date,
            'duration_days': obj.duration_days,
            'budget': obj.budget,
            'preferences': obj.preferences,
            'requirements': obj.requirements,
            'user_id': obj.user_id,
            'status': obj.status,
            'score': obj.score,
            'generated_plans': obj.generated_plans,
            'selected_plan': obj.selected_plan,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'items': []  # 初始化为空列表，避免访问关系属性
        }
        return cls(**data)


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
    format: str = Field("pdf", description="导出格式", pattern="^(pdf|json|html)$")
    include_images: bool = Field(True, description="是否包含图片")
    include_map: bool = Field(True, description="是否包含地图")
    language: str = Field("zh", description="导出语言")
