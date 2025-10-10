"""
旅行方案评分服务
"""

from typing import Dict, Any, Optional
from loguru import logger
import math


class PlanScorer:
    """方案评分器"""
    
    def __init__(self):
        self.weights = {
            "price": 0.3,      # 价格权重
            "rating": 0.25,    # 评分权重
            "convenience": 0.2, # 便利性权重
            "safety": 0.15,    # 安全性权重
            "popularity": 0.1  # 受欢迎程度权重
        }
    
    async def score_plan(
        self, 
        plan: Dict[str, Any], 
        original_plan: Any,
        preferences: Optional[Dict[str, Any]] = None
    ) -> float:
        """计算方案总分"""
        try:
            scores = {}
            
            # 价格评分
            scores["price"] = await self._score_price(plan, original_plan)
            
            # 评分评分
            scores["rating"] = await self._score_rating(plan)
            
            # 便利性评分
            scores["convenience"] = await self._score_convenience(plan)
            
            # 安全性评分
            scores["safety"] = await self._score_safety(plan)
            
            # 受欢迎程度评分
            scores["popularity"] = await self._score_popularity(plan)
            
            # 计算加权总分
            total_score = sum(
                scores[factor] * self.weights[factor] 
                for factor in self.weights
            )
            
            # 应用偏好调整
            if preferences:
                total_score = await self._apply_preference_adjustment(
                    total_score, plan, preferences
                )
            
            logger.info(f"方案评分: {total_score:.2f}, 各维度: {scores}")
            return round(total_score, 2)
            
        except Exception as e:
            logger.error(f"方案评分失败: {e}")
            return 0.0
    
    async def _score_price(self, plan: Dict[str, Any], original_plan: Any) -> float:
        """价格评分"""
        try:
            total_cost = plan.get("total_cost", {}).get("total", 0)
            budget = getattr(original_plan, 'budget', None) or 5000  # 默认预算5000元
            
            if total_cost <= 0:
                return 0.0
            
            # 价格越接近预算，评分越高
            if total_cost <= budget:
                # 在预算内，价格越低评分越高
                score = 1.0 - (total_cost / budget) * 0.3
            else:
                # 超出预算，按超出比例扣分
                over_ratio = (total_cost - budget) / budget
                score = max(0.0, 0.7 - over_ratio * 0.5)
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"价格评分失败: {e}")
            return 0.5
    
    async def _score_rating(self, plan: Dict[str, Any]) -> float:
        """评分评分"""
        try:
            ratings = []
            
            # 收集所有评分
            hotel = plan.get("hotel") or {}
            if hotel.get("rating"):
                ratings.append(hotel["rating"])
            
            flight = plan.get("flight") or {}
            if flight.get("rating"):
                ratings.append(flight["rating"])
            
            for day in plan.get("daily_itineraries", []):
                for attraction in day.get("attractions", []):
                    if attraction.get("rating"):
                        ratings.append(attraction["rating"])
            
            for restaurant in plan.get("restaurants", []):
                if restaurant.get("rating"):
                    ratings.append(restaurant["rating"])
            
            if not ratings:
                return 0.5  # 默认评分
            
            # 计算平均评分并转换为0-1分数
            avg_rating = sum(ratings) / len(ratings)
            score = avg_rating / 5.0  # 5分制转换为0-1
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"评分评分失败: {e}")
            return 0.5
    
    async def _score_convenience(self, plan: Dict[str, Any]) -> float:
        """便利性评分"""
        try:
            convenience_factors = []
            
            # 交通便利性
            transportation = plan.get("transportation", [])
            if transportation:
                convenience_factors.append(0.8)  # 有交通信息
            
            # 酒店位置便利性
            hotel = plan.get("hotel", {})
            if hotel.get("address"):
                # 简单判断：地址包含"市中心"、"商业区"等关键词
                address = hotel["address"].lower()
                if any(keyword in address for keyword in ["市中心", "商业区", "地铁", "交通便利"]):
                    convenience_factors.append(0.9)
                else:
                    convenience_factors.append(0.6)
            
            # 景点分布合理性
            daily_itineraries = plan.get("daily_itineraries", [])
            if daily_itineraries:
                # 检查每日景点数量是否合理
                for day in daily_itineraries:
                    attractions_count = len(day.get("attractions", []))
                    if 2 <= attractions_count <= 4:
                        convenience_factors.append(0.8)
                    else:
                        convenience_factors.append(0.5)
            
            if not convenience_factors:
                return 0.5
            
            return sum(convenience_factors) / len(convenience_factors)
            
        except Exception as e:
            logger.error(f"便利性评分失败: {e}")
            return 0.5
    
    async def _score_safety(self, plan: Dict[str, Any]) -> float:
        """安全性评分"""
        try:
            safety_factors = []
            
            # 航班安全性
            flight = plan.get("flight", {})
            if flight:
                airline = flight.get("airline", "").lower()
                # 知名航空公司安全性更高
                major_airlines = ["国航", "东航", "南航", "海航", "厦航"]
                if any(airline in airline for airline in major_airlines):
                    safety_factors.append(0.9)
                else:
                    safety_factors.append(0.7)
            
            # 酒店安全性
            hotel = plan.get("hotel", {})
            if hotel:
                # 星级酒店安全性更高
                rating = hotel.get("rating", 0)
                if rating >= 4.0:
                    safety_factors.append(0.9)
                elif rating >= 3.0:
                    safety_factors.append(0.7)
                else:
                    safety_factors.append(0.5)
            
            # 景点安全性
            daily_itineraries = plan.get("daily_itineraries", [])
            for day in daily_itineraries:
                for attraction in day.get("attractions", []):
                    # 知名景点安全性更高
                    name = attraction.get("name", "").lower()
                    if any(keyword in name for keyword in ["博物馆", "公园", "广场", "官方"]):
                        safety_factors.append(0.8)
                    else:
                        safety_factors.append(0.6)
            
            if not safety_factors:
                return 0.5
            
            return sum(safety_factors) / len(safety_factors)
            
        except Exception as e:
            logger.error(f"安全性评分失败: {e}")
            return 0.5
    
    async def _score_popularity(self, plan: Dict[str, Any]) -> float:
        """受欢迎程度评分"""
        try:
            popularity_factors = []
            
            # 景点受欢迎程度
            daily_itineraries = plan.get("daily_itineraries", [])
            for day in daily_itineraries:
                for attraction in day.get("attractions", []):
                    rating = attraction.get("rating", 0)
                    review_count = attraction.get("review_count", 0)
                    
                    # 综合评分和评论数量
                    if rating >= 4.5 and review_count >= 100:
                        popularity_factors.append(0.9)
                    elif rating >= 4.0 and review_count >= 50:
                        popularity_factors.append(0.7)
                    elif rating >= 3.5:
                        popularity_factors.append(0.5)
                    else:
                        popularity_factors.append(0.3)
            
            # 餐厅受欢迎程度
            for restaurant in plan.get("restaurants", []):
                rating = restaurant.get("rating", 0)
                if rating >= 4.5:
                    popularity_factors.append(0.8)
                elif rating >= 4.0:
                    popularity_factors.append(0.6)
                else:
                    popularity_factors.append(0.4)
            
            if not popularity_factors:
                return 0.5
            
            return sum(popularity_factors) / len(popularity_factors)
            
        except Exception as e:
            logger.error(f"受欢迎程度评分失败: {e}")
            return 0.5
    
    async def _apply_preference_adjustment(
        self, 
        base_score: float, 
        plan: Dict[str, Any], 
        preferences: Dict[str, Any]
    ) -> float:
        """应用偏好调整"""
        try:
            adjusted_score = base_score
            
            # 预算偏好调整
            if "budget_priority" in preferences:
                budget_priority = preferences["budget_priority"]
                if budget_priority == "low":
                    # 更重视价格
                    price_score = await self._score_price(plan, None)
                    adjusted_score = adjusted_score * 0.7 + price_score * 0.3
                elif budget_priority == "high":
                    # 更重视质量
                    rating_score = await self._score_rating(plan)
                    adjusted_score = adjusted_score * 0.7 + rating_score * 0.3
            
            # 活动偏好调整
            if "activity_preference" in preferences:
                activity_pref = preferences["activity_preference"]
                if activity_pref == "culture":
                    # 文化类活动加分
                    culture_count = self._count_culture_activities(plan)
                    adjusted_score += culture_count * 0.05
                elif activity_pref == "nature":
                    # 自然类活动加分
                    nature_count = self._count_nature_activities(plan)
                    adjusted_score += nature_count * 0.05
            
            return max(0.0, min(1.0, adjusted_score))
            
        except Exception as e:
            logger.error(f"偏好调整失败: {e}")
            return base_score
    
    def _count_culture_activities(self, plan: Dict[str, Any]) -> int:
        """统计文化类活动数量"""
        count = 0
        daily_itineraries = plan.get("daily_itineraries", [])
        
        for day in daily_itineraries:
            for attraction in day.get("attractions", []):
                category = attraction.get("category", "").lower()
                name = attraction.get("name", "").lower()
                
                if any(keyword in category or keyword in name 
                       for keyword in ["博物馆", "历史", "文化", "古迹", "艺术"]):
                    count += 1
        
        return count
    
    def _count_nature_activities(self, plan: Dict[str, Any]) -> int:
        """统计自然类活动数量"""
        count = 0
        daily_itineraries = plan.get("daily_itineraries", [])
        
        for day in daily_itineraries:
            for attraction in day.get("attractions", []):
                category = attraction.get("category", "").lower()
                name = attraction.get("name", "").lower()
                
                if any(keyword in category or keyword in name 
                       for keyword in ["公园", "山", "湖", "海", "自然", "风景"]):
                    count += 1
        
        return count
