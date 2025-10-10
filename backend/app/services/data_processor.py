"""
数据处理服务
负责数据清洗和可信度评分
"""

from typing import List, Dict, Any
from loguru import logger
import re
import json


class DataProcessor:
    """数据处理器"""
    
    def __init__(self):
        self.trusted_sources = [
            "携程", "去哪儿", "飞猪", "booking.com", 
            "agoda", "tripadvisor", "官方"
        ]
    
    async def process_data(
        self, 
        raw_data: List[Dict[str, Any]], 
        data_type: str, 
        plan: Any
    ) -> List[Dict[str, Any]]:
        """处理原始数据"""
        try:
            logger.info(f"开始处理 {data_type} 数据，共 {len(raw_data)} 条")
            
            processed_data = []
            
            for item in raw_data:
                # 数据清洗
                cleaned_item = await self._clean_data(item, data_type)
                
                # 可信度评分
                trust_score = await self._calculate_trust_score(cleaned_item, data_type)
                cleaned_item["trust_score"] = trust_score
                
                # 数据验证
                if await self._validate_data(cleaned_item, data_type):
                    processed_data.append(cleaned_item)
            
            # 按可信度排序
            processed_data.sort(key=lambda x: x.get("trust_score", 0), reverse=True)
            
            logger.info(f"处理完成，保留 {len(processed_data)} 条有效数据")
            return processed_data
            
        except Exception as e:
            logger.error(f"数据处理失败: {e}")
            return []
    
    async def _clean_data(self, item: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """数据清洗"""
        cleaned_item = item.copy()
        
        # 通用清洗
        for key, value in cleaned_item.items():
            if isinstance(value, str):
                # 去除多余空白
                cleaned_item[key] = re.sub(r'\s+', ' ', value.strip())
                
                # 处理价格字段
                if 'price' in key.lower():
                    cleaned_item[key] = self._extract_price(value)
                
                # 处理评分字段
                if 'rating' in key.lower():
                    cleaned_item[key] = self._extract_rating(value)
        
        # 特定类型清洗
        if data_type == "flights":
            cleaned_item = await self._clean_flight_data(cleaned_item)
        elif data_type == "hotels":
            cleaned_item = await self._clean_hotel_data(cleaned_item)
        elif data_type == "attractions":
            cleaned_item = await self._clean_attraction_data(cleaned_item)
        elif data_type == "restaurants":
            cleaned_item = await self._clean_restaurant_data(cleaned_item)
        
        return cleaned_item
    
    async def _clean_flight_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """清洗航班数据"""
        # 标准化时间格式
        if "departure_time" in item:
            item["departure_time"] = self._standardize_time(item["departure_time"])
        if "arrival_time" in item:
            item["arrival_time"] = self._standardize_time(item["arrival_time"])
        
        # 计算飞行时长
        if "duration" not in item and "departure_time" in item and "arrival_time" in item:
            item["duration"] = self._calculate_duration(
                item["departure_time"], item["arrival_time"]
            )
        
        return item
    
    async def _clean_hotel_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """清洗酒店数据"""
        # 标准化设施列表
        if "amenities" in item and isinstance(item["amenities"], str):
            item["amenities"] = [a.strip() for a in item["amenities"].split(",")]
        
        return item
    
    async def _clean_attraction_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """清洗景点数据"""
        # 标准化开放时间
        if "opening_hours" in item:
            item["opening_hours"] = self._standardize_opening_hours(item["opening_hours"])
        
        return item
    
    async def _clean_restaurant_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """清洗餐厅数据"""
        # 标准化菜系类型
        if "cuisine_type" in item:
            item["cuisine_type"] = self._standardize_cuisine_type(item["cuisine_type"])
        
        return item
    
    def _extract_price(self, price_str: str) -> float:
        """提取价格数值"""
        if not price_str:
            return 0.0
        
        # 提取数字
        numbers = re.findall(r'\d+\.?\d*', price_str.replace(',', ''))
        if numbers:
            return float(numbers[0])
        return 0.0
    
    def _extract_rating(self, rating_str: str) -> float:
        """提取评分数值"""
        if not rating_str:
            return 0.0
        
        # 提取数字
        numbers = re.findall(r'\d+\.?\d*', rating_str)
        if numbers:
            rating = float(numbers[0])
            # 如果是5分制，直接返回；如果是10分制，转换为5分制
            if rating > 5:
                rating = rating / 2
            return rating
        return 0.0
    
    def _standardize_time(self, time_str: str) -> str:
        """标准化时间格式"""
        if not time_str:
            return ""
        
        # 提取时间部分
        time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
        if time_match:
            hour, minute = time_match.groups()
            return f"{hour.zfill(2)}:{minute}"
        
        return time_str
    
    def _calculate_duration(self, start_time: str, end_time: str) -> str:
        """计算时长"""
        try:
            start_hour, start_min = map(int, start_time.split(':'))
            end_hour, end_min = map(int, end_time.split(':'))
            
            start_total = start_hour * 60 + start_min
            end_total = end_hour * 60 + end_min
            
            duration_min = end_total - start_total
            if duration_min < 0:
                duration_min += 24 * 60  # 跨天
            
            hours = duration_min // 60
            minutes = duration_min % 60
            
            return f"{hours}h{minutes}m"
        except:
            return ""
    
    def _standardize_opening_hours(self, hours_str: str) -> str:
        """标准化开放时间"""
        if not hours_str:
            return ""
        
        # 简单的标准化
        hours_str = hours_str.replace("：", ":")
        hours_str = hours_str.replace("至", "-")
        
        return hours_str
    
    def _standardize_cuisine_type(self, cuisine_str: str) -> str:
        """标准化菜系类型"""
        if not cuisine_str:
            return ""
        
        # 菜系映射
        cuisine_map = {
            "中餐": "中式",
            "西餐": "西式",
            "日料": "日式",
            "韩料": "韩式",
            "泰餐": "泰式"
        }
        
        return cuisine_map.get(cuisine_str, cuisine_str)
    
    async def _calculate_trust_score(self, item: Dict[str, Any], data_type: str) -> float:
        """计算可信度评分"""
        score = 0.0
        
        # 数据源可信度
        source = item.get("source", "")
        if any(trusted in source for trusted in self.trusted_sources):
            score += 0.3
        
        # 数据完整性
        required_fields = self._get_required_fields(data_type)
        complete_fields = sum(1 for field in required_fields if item.get(field))
        completeness = complete_fields / len(required_fields) if required_fields else 0
        score += completeness * 0.4
        
        # 数据合理性
        reasonableness = await self._check_reasonableness(item, data_type)
        score += reasonableness * 0.3
        
        return min(score, 1.0)
    
    def _get_required_fields(self, data_type: str) -> List[str]:
        """获取必需字段"""
        field_map = {
            "flights": ["airline", "flight_number", "departure_time", "price"],
            "hotels": ["name", "address", "price_per_night"],
            "attractions": ["name", "category", "rating"],
            "restaurants": ["name", "cuisine_type", "rating"],
            "transportation": ["type", "name", "price"]
        }
        return field_map.get(data_type, [])
    
    async def _check_reasonableness(self, item: Dict[str, Any], data_type: str) -> float:
        """检查数据合理性"""
        score = 0.0
        
        # 价格合理性
        if "price" in item or "price_per_night" in item:
            price = item.get("price") or item.get("price_per_night", 0)
            if 0 < price < 100000:  # 合理价格范围
                score += 0.5
        
        # 评分合理性
        if "rating" in item:
            rating = item["rating"]
            if 0 <= rating <= 5:  # 合理评分范围
                score += 0.5
        
        return score
    
    async def _validate_data(self, item: Dict[str, Any], data_type: str) -> bool:
        """验证数据有效性"""
        # 基本验证
        if not item.get("name") and not item.get("title"):
            return False
        
        # 价格验证
        price_fields = ["price", "price_per_night"]
        for field in price_fields:
            if field in item and item[field] < 0:
                return False
        
        # 评分验证
        if "rating" in item and (item["rating"] < 0 or item["rating"] > 5):
            return False
        
        return True
