"""
景点详细信息模型
用于存储手动维护的景点详细信息（联系方式、门票、营业时间等）
"""

from sqlalchemy import Column, String, Text, Float, JSON, Integer
from app.models.base import BaseModel


class AttractionDetail(BaseModel):
    """景点详细信息模型"""
    __tablename__ = "attraction_details"
    
    # 基本信息（用于匹配和标识）
    name = Column(String(200), nullable=False, index=True)  # 景点名称
    destination = Column(String(100), nullable=False, index=True)  # 所属目的地
    city = Column(String(100), nullable=True, index=True)  # 所属城市（用于精确匹配）
    
    # 联系方式
    phone = Column(String(50), nullable=True)  # 联系电话
    website = Column(String(500), nullable=True)  # 官网
    email = Column(String(100), nullable=True)  # 邮箱
    wechat = Column(String(100), nullable=True)  # 微信号/公众号
    
    # 价格信息（用于展示和计算开销）
    ticket_price = Column(Float, nullable=True)  # 成人票价格
    ticket_price_child = Column(Float, nullable=True)  # 儿童票价格
    ticket_price_student = Column(Float, nullable=True)  # 学生票价格（可选）
    currency = Column(String(10), default="CNY", nullable=False)  # 货币单位
    
    # 价格说明（文本描述，用于展示特殊情况）
    # 例如："旺季(7-8月)门票120元，淡季80元"、"学生需持学生证"、"60岁以上老人免费"
    price_note = Column(Text, nullable=True)
    
    # 营业时间
    opening_hours = Column(JSON, nullable=True)  # 营业时间（JSON格式，支持不同日期）
    # 示例格式：
    # {
    #   "周一": "08:00-18:00",
    #   "周二": "08:00-18:00",
    #   "节假日": "08:00-20:00",
    #   "备注": "节假日需提前预约"
    # }
    opening_hours_text = Column(Text, nullable=True)  # 营业时间文本描述（便于阅读）
    
    # 位置信息（用于精确匹配）
    address = Column(Text, nullable=True)  # 详细地址
    latitude = Column(Float, nullable=True)  # 纬度
    longitude = Column(Float, nullable=True)  # 经度
    
    # 图片信息
    image_url = Column(String(500), nullable=True)  # 图片链接
    
    # 其他详细信息（JSON格式，用于展示，灵活存储）
    # 常用字段示例：
    # {
    #   "recommended_duration": "2-3小时",  # 推荐游览时长
    #   "best_visit_time": "春季和秋季",     # 最佳游览时间
    #   "tips": ["建议提前预约", "拍照需注意", "有免费导览"],  # 游览提示
    #   "facilities": ["停车场", "餐厅", "纪念品店"],  # 设施
    #   "parking_info": "收费停车场，20元/天",  # 停车信息
    #   "reservation_required": false,  # 是否需要预约
    #   "reservation_url": "https://example.com"  # 预约链接
    # }
    # 注意：这个字段主要用于展示，可以灵活添加任何信息，不需要固定结构
    extra_info = Column(JSON, nullable=True)
    
    # 匹配优先级（用于自动匹配时的优先级）
    match_priority = Column(Integer, default=100, nullable=False)  # 数值越大优先级越高
    
    # 数据来源标记
    source = Column(String(50), default="manual", nullable=False)  # manual, api, etc.
    verified = Column(String(20), default="pending", nullable=False)  # pending, verified, outdated
    
    def __repr__(self):
        return f"<AttractionDetail(name={self.name}, destination={self.destination})>"
    
    def to_dict(self):
        """转换为字典格式（包含详细信息）"""
        return {
            "id": self.id,
            "name": self.name,
            "destination": self.destination,
            "city": self.city,
            "phone": self.phone,
            "website": self.website,
            "email": self.email,
            "wechat": self.wechat,
            "ticket_price": self.ticket_price,
            "ticket_price_child": self.ticket_price_child,
            "ticket_price_student": self.ticket_price_student,
            "currency": self.currency,
            "price_note": self.price_note,
            "opening_hours": self.opening_hours,
            "opening_hours_text": self.opening_hours_text,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "image_url": self.image_url,
            "extra_info": self.extra_info or {},
            "match_priority": self.match_priority,
            "source": self.source,
            "verified": self.verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

