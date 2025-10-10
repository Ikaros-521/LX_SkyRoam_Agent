"""
旅行方案生成服务
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import random


class PlanGenerator:
    """方案生成器"""
    
    def __init__(self):
        self.max_plans = 5
        self.min_attractions_per_day = 2
        self.max_attractions_per_day = 4
    
    async def generate_plans(
        self, 
        processed_data: Dict[str, Any], 
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成多个旅行方案"""
        try:
            logger.info("开始生成旅行方案")
            
            plans = []
            
            # 生成不同风格的方案
            plan_types = [
                "经济实惠型",
                "舒适享受型", 
                "文化深度型",
                "自然风光型",
                "美食体验型"
            ]
            
            for i, plan_type in enumerate(plan_types[:self.max_plans]):
                plan_data = await self._generate_single_plan(
                    processed_data, plan, preferences, plan_type, i
                )
                if plan_data:
                    plans.append(plan_data)
            
            logger.info(f"生成了 {len(plans)} 个旅行方案")
            return plans
            
        except Exception as e:
            logger.error(f"生成旅行方案失败: {e}")
            return []
    
    async def _generate_single_plan(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]],
        plan_type: str,
        plan_index: int
    ) -> Optional[Dict[str, Any]]:
        """生成单个方案"""
        try:
            # 选择最佳航班
            flight = self._select_best_flight(processed_data.get("flights", []), plan_type)
            
            # 选择最佳酒店
            hotel = self._select_best_hotel(processed_data.get("hotels", []), plan_type)
            
            # 生成每日行程
            daily_itineraries = await self._generate_daily_itineraries(
                processed_data, plan, preferences, plan_type
            )
            
            # 选择餐厅
            restaurants = self._select_restaurants(
                processed_data.get("restaurants", []), plan_type, len(daily_itineraries)
            )
            
            # 选择交通方式
            transportation = self._select_transportation(
                processed_data.get("transportation", [])
            )
            
            # 计算总预算
            total_cost = self._calculate_total_cost(
                flight, hotel, daily_itineraries, restaurants
            )
            
            plan_data = {
                "id": f"plan_{plan_index}",
                "type": plan_type,
                "title": f"{plan.destination} {plan_type}旅行方案",
                "description": f"精心为您打造的{plan_type}旅行方案",
                "flight": flight,
                "hotel": hotel,
                "daily_itineraries": daily_itineraries,
                "restaurants": restaurants,
                "transportation": transportation,
                "total_cost": total_cost,
                "duration_days": plan.duration_days,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return plan_data
            
        except Exception as e:
            logger.error(f"生成单个方案失败: {e}")
            return None
    
    def _select_best_flight(self, flights: List[Dict[str, Any]], plan_type: str) -> Optional[Dict[str, Any]]:
        """选择最佳航班"""
        if not flights:
            return None
        
        # 根据方案类型选择航班
        if plan_type == "经济实惠型":
            # 选择最便宜的航班
            return min(flights, key=lambda x: x.get("price", float('inf')))
        elif plan_type == "舒适享受型":
            # 选择评分最高的航班
            return max(flights, key=lambda x: x.get("rating", 0))
        else:
            # 随机选择
            return random.choice(flights)
    
    def _select_best_hotel(self, hotels: List[Dict[str, Any]], plan_type: str) -> Optional[Dict[str, Any]]:
        """选择最佳酒店"""
        if not hotels:
            return None
        
        # 根据方案类型选择酒店
        if plan_type == "经济实惠型":
            return min(hotels, key=lambda x: x.get("price_per_night", float('inf')))
        elif plan_type == "舒适享受型":
            return max(hotels, key=lambda x: x.get("rating", 0))
        else:
            return random.choice(hotels)
    
    async def _generate_daily_itineraries(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]],
        plan_type: str
    ) -> List[Dict[str, Any]]:
        """生成每日行程"""
        attractions = processed_data.get("attractions", [])
        daily_itineraries = []
        
        # 根据方案类型筛选景点
        filtered_attractions = self._filter_attractions_by_type(attractions, plan_type)
        
        # 按天数分配景点
        attractions_per_day = len(filtered_attractions) // plan.duration_days
        remaining_attractions = len(filtered_attractions) % plan.duration_days
        
        start_date = plan.start_date
        
        for day in range(plan.duration_days):
            day_attractions = attractions_per_day
            if day < remaining_attractions:
                day_attractions += 1
            
            # 选择当天的景点
            day_attraction_list = filtered_attractions[
                day * attractions_per_day:(day + 1) * attractions_per_day
            ]
            
            if day < remaining_attractions:
                day_attraction_list.append(filtered_attractions[
                    plan.duration_days * attractions_per_day + day
                ])
            
            # 生成当日行程
            daily_itinerary = {
                "day": day + 1,
                "date": (start_date + timedelta(days=day)).isoformat(),
                "attractions": day_attraction_list,
                "meals": self._generate_daily_meals(day),
                "transportation": "地铁/公交",
                "estimated_cost": sum(attr.get("price", 0) for attr in day_attraction_list)
            }
            
            daily_itineraries.append(daily_itinerary)
        
        return daily_itineraries
    
    def _filter_attractions_by_type(
        self, 
        attractions: List[Dict[str, Any]], 
        plan_type: str
    ) -> List[Dict[str, Any]]:
        """根据方案类型筛选景点"""
        type_mapping = {
            "经济实惠型": ["免费", "便宜", "公园", "广场"],
            "舒适享受型": ["豪华", "高端", "度假村", "水疗"],
            "文化深度型": ["博物馆", "历史", "文化", "古迹"],
            "自然风光型": ["自然", "公园", "山", "湖", "海"],
            "美食体验型": ["美食", "餐厅", "市场", "小吃"]
        }
        
        keywords = type_mapping.get(plan_type, [])
        
        if not keywords:
            return attractions
        
        filtered = []
        for attraction in attractions:
            name = attraction.get("name", "").lower()
            category = attraction.get("category", "").lower()
            description = attraction.get("description", "").lower()
            
            if any(keyword in name or keyword in category or keyword in description 
                   for keyword in keywords):
                filtered.append(attraction)
        
        # 如果筛选结果太少，返回原始列表
        return filtered if len(filtered) >= 3 else attractions
    
    def _generate_daily_meals(self, day: int) -> List[Dict[str, Any]]:
        """生成每日餐饮安排"""
        meals = [
            {
                "type": "早餐",
                "time": "08:00",
                "suggestion": "酒店早餐或当地特色早餐"
            },
            {
                "type": "午餐", 
                "time": "12:00",
                "suggestion": "当地特色餐厅"
            },
            {
                "type": "晚餐",
                "time": "18:00", 
                "suggestion": "推荐餐厅或特色小吃"
            }
        ]
        
        return meals
    
    def _select_restaurants(
        self, 
        restaurants: List[Dict[str, Any]], 
        plan_type: str, 
        num_days: int
    ) -> List[Dict[str, Any]]:
        """选择餐厅"""
        if not restaurants:
            return []
        
        # 根据方案类型选择餐厅
        if plan_type == "经济实惠型":
            selected = sorted(restaurants, key=lambda x: x.get("price_range", "$$$$"))[:num_days]
        elif plan_type == "美食体验型":
            selected = sorted(restaurants, key=lambda x: x.get("rating", 0), reverse=True)[:num_days]
        else:
            selected = random.sample(restaurants, min(num_days, len(restaurants)))
        
        return selected
    
    def _select_transportation(self, transportation: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """选择交通方式"""
        if not transportation:
            return []
        
        # 选择最常用的交通方式
        return transportation[:3]  # 返回前3种交通方式
    
    def _calculate_total_cost(
        self,
        flight: Optional[Dict[str, Any]],
        hotel: Optional[Dict[str, Any]],
        daily_itineraries: List[Dict[str, Any]],
        restaurants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """计算总预算"""
        costs = {
            "flight": flight.get("price", 0) if flight else 0,
            "hotel": 0,
            "attractions": 0,
            "meals": 0,
            "transportation": 0,
            "total": 0
        }
        
        # 酒店费用
        if hotel:
            costs["hotel"] = hotel.get("price_per_night", 0) * len(daily_itineraries)
        
        # 景点费用
        for day in daily_itineraries:
            costs["attractions"] += day.get("estimated_cost", 0)
        
        # 餐饮费用（估算）
        costs["meals"] = len(daily_itineraries) * 3 * 50  # 每天3餐，每餐50元
        
        # 交通费用（估算）
        costs["transportation"] = len(daily_itineraries) * 20  # 每天20元交通费
        
        costs["total"] = sum(costs.values())
        
        return costs
    
    async def refine_plan(
        self, 
        current_plan: Dict[str, Any], 
        refinements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """细化方案"""
        try:
            refined_plan = current_plan.copy()
            
            # 应用细化要求
            if "budget_adjustment" in refinements:
                refined_plan = self._adjust_budget(refined_plan, refinements["budget_adjustment"])
            
            if "time_preference" in refinements:
                refined_plan = self._adjust_timing(refined_plan, refinements["time_preference"])
            
            if "activity_preference" in refinements:
                refined_plan = self._adjust_activities(refined_plan, refinements["activity_preference"])
            
            refined_plan["refined_at"] = datetime.utcnow().isoformat()
            refined_plan["refinements"] = refinements
            
            return refined_plan
            
        except Exception as e:
            logger.error(f"细化方案失败: {e}")
            return current_plan
    
    def _adjust_budget(self, plan: Dict[str, Any], adjustment: str) -> Dict[str, Any]:
        """调整预算"""
        # 实现预算调整逻辑
        return plan
    
    def _adjust_timing(self, plan: Dict[str, Any], preference: str) -> Dict[str, Any]:
        """调整时间安排"""
        # 实现时间调整逻辑
        return plan
    
    def _adjust_activities(self, plan: Dict[str, Any], preference: str) -> Dict[str, Any]:
        """调整活动安排"""
        # 实现活动调整逻辑
        return plan
    
    async def generate_recommendations(self, plan: Any) -> List[Dict[str, Any]]:
        """生成推荐"""
        recommendations = [
            {
                "type": "天气提醒",
                "content": "建议关注当地天气预报，合理安排户外活动",
                "priority": "high"
            },
            {
                "type": "交通建议",
                "content": "建议提前预订热门景点门票，避免排队等待",
                "priority": "medium"
            },
            {
                "type": "安全提醒",
                "content": "请保管好个人物品，注意人身安全",
                "priority": "high"
            }
        ]
        
        return recommendations
