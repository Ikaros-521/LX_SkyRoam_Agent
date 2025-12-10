"""
数据模型包
"""

from .user import User
from .travel_plan import TravelPlan, TravelPlanItem
from .destination import Destination
from .attraction_detail import AttractionDetail
from .base import Base

__all__ = [
    "User",
    "TravelPlan", 
    "TravelPlanItem",
    "Destination",
    "AttractionDetail",
    "Base"
]
