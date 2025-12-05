"""
数据收集服务
负责从各种数据源收集旅行相关信息
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from loguru import logger
import httpx

from app.core.config import settings
from app.tools.mcp_client import MCPClient
from app.tools.amap_mcp_client import AmapMCPClient
from app.tools.city_resolver import CityResolver
from app.tools.baidu_maps_integration import (
    map_directions, 
    map_search_places, 
    map_geocode,
    map_weather
)
# from app.services.web_scraper import WebScraper  # 已移除爬虫功能
from app.services.xhs_api_client import XHSAPIClient
from app.core.redis import get_cache, set_cache, cache_key


class DataCollector:
    """数据收集器"""
    
    def __init__(self):
        self.mcp_client = MCPClient()
        self.amap_client = AmapMCPClient()
        self.city_resolver = CityResolver()
        # self.web_scraper = WebScraper()  # 已移除爬虫功能
        self.xhs_client = XHSAPIClient(settings.XHS_API_BASE)  # 小红书API客户端
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            proxies={}
        )
        self.map_provider = settings.MAP_PROVIDER  # 地图服务提供商

        # 基于行程天数动态控制原始数据量的参数（全部可通过 settings / 环境变量覆盖）
        # 这些只是“期望值”，不会强行按天精确匹配，而是用于估算需要多久的数据量
        self.plan_min_attractions_per_day = int(
            getattr(settings, "PLAN_MIN_ATTRACTIONS_PER_DAY", 2)
        )
        self.plan_min_meals_per_day = int(
            getattr(settings, "PLAN_MIN_MEALS_PER_DAY", 3)
        )
        self.plan_max_hotels_per_trip = int(
            getattr(settings, "PLAN_MAX_HOTELS_PER_TRIP", 5)
        )

        # asyncio.run(self.collect_xiaohongshu_data("杭州西湖"))
    
    @staticmethod
    def _parse_price_value(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            import re
            match = re.search(r"(\d+(\.\d+)?)", str(value))
            if match:
                return float(match.group(1))
        except Exception:
            return None
        return None

    @classmethod
    def _format_price_label(cls, value: Optional[float]) -> str:
        if value is None:
            return "价格未知"
        return f"约 ¥{int(round(value))}"

    def _apply_price_metadata(self, restaurant: Dict[str, Any], raw_price: Any = None) -> Dict[str, Any]:
        """根据原始价格信息填充统一的价格字段"""
        price_value = self._parse_price_value(raw_price)
        if price_value is None:
            price_value = self._parse_price_value(
                restaurant.get("price") or restaurant.get("cost") or restaurant.get("price_range")
            )
        if price_value is not None:
            restaurant["price"] = price_value
        else:
            restaurant.pop("price", None)
        restaurant["price_range"] = self._format_price_label(price_value)
        return restaurant
    
    async def get_destination_geocode_info(self, destination: str) -> Optional[Dict[str, Any]]:
        """
        统一的地理编码获取函数
        优先使用高德地图，失败时回退到百度地图
        返回标准化的目的地地理信息
        """
        try:
            logger.info(f"获取目的地地理编码信息: {destination}")
            
            # 首先尝试使用高德地图地理编码
            try:
                amap_coords = await self.amap_client.geocode(destination)
                if amap_coords and amap_coords.get('lng') and amap_coords.get('lat'):
                    logger.info(f"高德地图地理编码成功: {destination}")
                    return {
                        'destination': destination,
                        'latitude': float(amap_coords['lat']),
                        'longitude': float(amap_coords['lng']),
                        'location_string': f"{amap_coords['lng']},{amap_coords['lat']}",  # 高德格式：经度,纬度
                        'provider': 'amap',
                        'formatted_address': amap_coords.get('formatted_address', destination),
                        'city': amap_coords.get('city', ''),
                        'district': amap_coords.get('district', ''),
                        'province': amap_coords.get('province', '')
                    }
            except Exception as e:
                logger.warning(f"高德地图地理编码失败: {destination}, 错误: {e}")
            
            # 回退到百度地图地理编码
            try:
                from app.tools.baidu_maps_integration import map_geocode
                baidu_result = await map_geocode(destination)
                
                if baidu_result.get("status") == 0:
                    location_info = baidu_result.get("result", {}).get("location", {})
                    if location_info and location_info.get('lng') and location_info.get('lat'):
                        logger.info(f"百度地图地理编码成功: {destination}")
                        return {
                            'destination': destination,
                            'latitude': float(location_info['lat']),
                            'longitude': float(location_info['lng']),
                            'location_string': f"{location_info['lng']},{location_info['lat']}",  # 经度,纬度格式
                            'provider': 'baidu',
                            'formatted_address': baidu_result.get("result", {}).get("formatted_address", destination),
                            'city': '',  # 百度地图返回的结构可能不同，需要进一步解析
                            'district': '',
                            'province': ''
                        }
            except Exception as e:
                logger.warning(f"百度地图地理编码失败: {destination}, 错误: {e}")
            
            logger.error(f"所有地理编码服务都失败: {destination}")
            return None
            
        except Exception as e:
            logger.error(f"获取地理编码信息时发生错误: {destination}, 错误: {e}")
            return None
    
    async def collect_flight_data(
        self, 
        departure: str,
        destination: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """收集航班数据 - 使用 Amadeus API"""
        try:
            cache_key_str = cache_key("flights", f"{departure}-{destination}", start_date.date(), end_date.date())
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的航班数据: {departure} -> {destination}")
                return cached_data
            
            logger.info(f"开始收集航班数据: {departure} -> {destination}, 出发日期: {start_date.date()}")
            
            # 使用 Amadeus API 收集航班信息
            flight_data = await self.mcp_client.get_flights(
                origin=departure,
                destination=destination,
                departure_date=start_date.date(),
                return_date=end_date.date()
            )
            
            # 验证和处理航班数据
            if flight_data:
                # 确保每个航班都有必要的字段
                validated_flights = []
                for flight in flight_data:
                    if self._validate_flight_data(flight):
                        # 添加额外的元数据
                        flight['collected_at'] = datetime.utcnow().isoformat()
                        flight['route'] = f"{departure} -> {destination}"
                        validated_flights.append(flight)
                    else:
                        logger.warning(f"航班数据验证失败: {flight.get('id', 'unknown')}")
                
                flight_data = validated_flights
                logger.info(f"成功收集并验证 {len(flight_data)} 条航班数据")
            else:
                logger.warning(f"未获取到航班数据: {departure} -> {destination}")
                flight_data = []
            
            # 缓存数据 (5分钟缓存，航班数据变化较快)
            await set_cache(cache_key_str, flight_data, ttl=300)
            
            return flight_data
            
        except Exception as e:
            logger.error(f"收集航班数据失败: {departure} -> {destination}, 错误: {e}")
            return []
    
    def _validate_flight_data(self, flight: Dict[str, Any]) -> bool:
        """验证航班数据的完整性"""
        required_fields = ['id', 'airline', 'flight_number', 'departure_time', 'arrival_time', 'price']
        
        for field in required_fields:
            if field not in flight or flight[field] is None:
                logger.warning(f"航班数据缺少必要字段: {field}")
                return False
        
        # 验证价格是否为有效数字
        try:
            float(flight['price'])
        except (ValueError, TypeError):
            logger.warning(f"航班价格格式无效: {flight.get('price')}")
            return False
        
        return True
    
    async def collect_hotel_data(
        self,
        destination: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """收集酒店数据

        注意：这里不会依赖“精确坐标范围”来调整数量，而是基于行程天数，按配置估算
        需要多少候选酒店，并在原始结果上做一个简单裁剪，避免数据过多或过少。
        """
        try:
            cache_key_str = cache_key("hotels", destination, start_date.date(), end_date.date())
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的酒店数据: {destination}")
                return cached_data
            
            hotel_data: List[Dict[str, Any]] = []

            # 根据行程天数和配置，估算期望的酒店候选数量
            try:
                days = (end_date.date() - start_date.date()).days + 1
            except Exception:
                days = 1
            days = max(days, 1)
            # 理论上多天行程也不需要太多酒店候选，按配置取一个上限
            desired_hotel_count = max(self.plan_max_hotels_per_trip, 1)
            
            # 优先使用高德地图周边搜索获取酒店信息
            try:
                # 使用统一的地理编码函数获取目的地坐标
                geocode_info = await self.get_destination_geocode_info(destination)
                if geocode_info:
                    location = geocode_info['location_string']
                    
                    # 使用高德地图周边搜索酒店
                    amap_hotels = await self.amap_client.search_places_around(
                        location=location,
                        keywords="酒店",
                        types="100000",  # 住宿服务
                        radius=10000,    # 10公里范围
                        offset=20
                    )
                    
                    # 转换高德地图数据格式
                    for hotel in amap_hotels:
                        hotel_item = {
                            "id": f"amap_hotel_{hotel.get('id', len(hotel_data) + 1)}",
                            "name": hotel.get("name", "未知酒店"),
                            "address": hotel.get("address", "地址未知"),
                            "rating": float(hotel.get("rating", 0)) if hotel.get("rating") else 4.0,
                            "price_per_night": self._estimate_hotel_price(hotel),
                            "currency": "CNY",
                            "amenities": self._parse_hotel_amenities(hotel),
                            "room_types": ["标准间", "大床房"],
                            "check_in": start_date.strftime("%Y-%m-%d"),
                            "check_out": end_date.strftime("%Y-%m-%d"),
                            "images": [],
                            "coordinates": {
                                "lng": float(hotel.get("location", "0,0").split(",")[0]),
                                "lat": float(hotel.get("location", "0,0").split(",")[1])
                            } if hotel.get("location") else {},
                            "star_rating": self._estimate_star_rating(hotel),
                            "distance": hotel.get("distance", "未知"),
                            "phone": hotel.get("tel", ""),
                            "source": "高德地图周边搜索"
                        }
                        hotel_data.append(hotel_item)
                    
                    logger.info(f"从高德地图周边搜索获取到 {len(amap_hotels)} 条酒店数据")
                else:
                    logger.warning(f"无法获取 {destination} 的坐标，跳过高德地图周边搜索")
                
            except Exception as e:
                logger.warning(f"高德地图酒店周边搜索调用失败: {e}")
            
            # 如果数据不足，使用MCP工具补充
            if len(hotel_data) < desired_hotel_count:
                try:
                    mcp_data = await self.mcp_client.get_hotels(
                        destination=destination,
                        check_in=start_date.date(),
                        check_out=end_date.date()
                    )
                    hotel_data.extend(mcp_data)
                    logger.info(f"从MCP服务补充 {len(mcp_data)} 条酒店数据")
                except Exception as e:
                    logger.warning(f"MCP酒店服务调用失败: {e}")

            # 最终对酒店列表做一次软裁剪，避免过多
            if len(hotel_data) > desired_hotel_count:
                logger.info(
                    f"根据行程天数裁剪酒店数量: 原始 {len(hotel_data)} 条，"
                    f"保留前 {desired_hotel_count} 条（可通过 PLAN_MAX_HOTELS_PER_TRIP 调整）"
                )
                hotel_data = hotel_data[:desired_hotel_count]
            
            # 缓存数据
            await set_cache(cache_key_str, hotel_data, ttl=300)  # 5分钟缓存
            
            logger.info(f"收集到 {len(hotel_data)} 条酒店数据")
            return hotel_data
            
        except Exception as e:
            logger.error(f"收集酒店数据失败: {e}")
            return []
    
    def _estimate_hotel_price(self, hotel: Dict[str, Any]) -> float:
        """根据酒店信息估算价格"""
        # 根据酒店类型和评分估算价格
        name = hotel.get("name", "").lower()
        rating = float(hotel.get("rating", 0)) if hotel.get("rating") else 4.0
        
        # 基础价格
        base_price = 200
        
        # 根据酒店名称关键词调整价格
        if any(keyword in name for keyword in ["五星", "豪华", "万豪", "希尔顿", "洲际", "凯悦"]):
            base_price = 800
        elif any(keyword in name for keyword in ["四星", "商务", "精品"]):
            base_price = 400
        elif any(keyword in name for keyword in ["三星", "快捷", "如家", "汉庭", "7天"]):
            base_price = 150
        
        # 根据评分调整价格
        price_multiplier = max(0.5, rating / 5.0)
        
        return round(base_price * price_multiplier, 2)
    
    def _parse_hotel_amenities(self, hotel: Dict[str, Any]) -> List[str]:
        """解析酒店设施信息"""
        amenities = []
        
        # 基础设施
        amenities.extend(["免费WiFi", "24小时前台", "空调"])
        
        # 根据酒店类型添加设施
        name = hotel.get("name", "").lower()
        if any(keyword in name for keyword in ["五星", "豪华", "万豪", "希尔顿", "洲际", "凯悦"]):
            amenities.extend(["健身房", "游泳池", "餐厅", "商务中心", "停车场", "客房服务"])
        elif any(keyword in name for keyword in ["四星", "商务", "精品"]):
            amenities.extend(["健身房", "餐厅", "停车场"])
        elif any(keyword in name for keyword in ["三星", "快捷"]):
            amenities.extend(["停车场"])
        
        return amenities
    
    def _estimate_star_rating(self, hotel: Dict[str, Any]) -> int:
        """估算酒店星级"""
        name = hotel.get("name", "").lower()
        rating = float(hotel.get("rating", 0)) if hotel.get("rating") else 4.0
        
        # 根据酒店名称关键词判断星级
        if any(keyword in name for keyword in ["五星", "豪华", "万豪", "希尔顿", "洲际", "凯悦"]):
            return 5
        elif any(keyword in name for keyword in ["四星", "商务", "精品"]):
            return 4
        elif any(keyword in name for keyword in ["三星"]):
            return 3
        elif any(keyword in name for keyword in ["快捷", "如家", "汉庭", "7天"]):
            return 2
        else:
            # 根据评分估算星级
            if rating >= 4.5:
                return 5
            elif rating >= 4.0:
                return 4
            elif rating >= 3.5:
                return 3
            elif rating >= 3.0:
                return 2
            else:
                return 1
    
    async def collect_attraction_data(
        self,
        destination: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """收集景点数据

        这里根据行程天数和配置，估算需要的“最少景点数量”，再结合地图/MCP结果做软裁剪或补充。
        注意：暂时不做精确的“按坐标半径动态缩放”，以免受目的地定位误差影响。
        """
        try:
            cache_key_str = cache_key(
                "attractions",
                destination,
                (start_date.date() if isinstance(start_date, datetime) else None),
                (end_date.date() if isinstance(end_date, datetime) else None),
            )
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的景点数据: {destination}")
                return cached_data
            
            attraction_data: List[Dict[str, Any]] = []

            # 估算行程天数，用于决定“期望最少景点数量”
            days = None
            if start_date and end_date:
                try:
                    days = (end_date.date() - start_date.date()).days + 1
                    if days <= 0:
                        days = None
                except Exception:
                    days = None
            if days is None:
                days = 1
            days = max(days, 1)

            desired_min_attractions = max(self.plan_min_attractions_per_day * days, 1)
            
            # 根据地图服务提供商收集景点数据
            try:
                if self.map_provider == "amap":
                    logger.info(f"使用高德地图MCP服务收集景点数据: {destination}")
                    await self._collect_amap_attraction_data(destination, attraction_data)
                else:
                    logger.info(f"使用百度地图功能收集景点数据: {destination}")
                    
                    # 搜索景点
                    places_result = await map_search_places(
                        query="景点",
                        region=destination,
                        tag="风景名胜",
                        is_china="true"
                    )
                    
                    if places_result.get("status") == 0:
                        places = places_result.get("result", {}).get("items", [])
                        for place in places:  # 先不过早裁剪，后面统一根据天数裁剪
                            attraction_item = {
                                "name": place.get("name", "景点"),
                                "category": "风景名胜",
                                "description": place.get("detail_info", {}).get("tag", "热门景点"),
                                "price": "免费" if place.get("detail_info", {}).get("price") == "0" else "收费",
                                "rating": place.get("detail_info", {}).get("overall_rating", "4.5"),
                                "address": place.get("address", ""),
                                "coordinates": {
                                    "lat": place.get("location", {}).get("lat"),
                                    "lng": place.get("location", {}).get("lng")
                                },
                                "opening_hours": place.get("detail_info", {}).get("open_time", "全天开放"),
                                "source": "百度地图API"
                            }
                            attraction_data.append(attraction_item)
                
                    # 搜索博物馆
                    museum_result = await map_search_places(
                        query="博物馆",
                        region=destination,
                        tag="科教文化服务",
                        is_china="true"
                    )
                    
                    if museum_result.get("status") == 0:
                        museums = museum_result.get("result", {}).get("items", [])
                        for museum in museums:  # 同样先全部收集，后面按天数控制总量
                            attraction_item = {
                                "name": museum.get("name", "博物馆"),
                                "category": "博物馆",
                                "description": museum.get("detail_info", {}).get("tag", "文化景点"),
                                "price": "免费" if museum.get("detail_info", {}).get("price") == "0" else "收费",
                                "rating": museum.get("detail_info", {}).get("overall_rating", "4.3"),
                                "address": museum.get("address", ""),
                                "coordinates": {
                                    "lat": museum.get("location", {}).get("lat"),
                                    "lng": museum.get("location", {}).get("lng")
                                },
                                "opening_hours": museum.get("detail_info", {}).get("open_time", "09:00-17:00"),
                                "source": "百度地图API"
                            }
                            attraction_data.append(attraction_item)
                    
                    logger.info(f"从百度地图API获取到 {len(attraction_data)} 条景点数据")
                
            except Exception as e:
                logger.warning(f"百度地图景点API调用失败: {e}")
            
            # 如果数据不足，使用MCP工具补充
            if len(attraction_data) < desired_min_attractions:
                try:
                    mcp_data = await self.mcp_client.get_attractions(destination)
                    attraction_data.extend(mcp_data)
                    logger.info(f"从MCP服务补充 {len(mcp_data)} 条景点数据")
                except Exception as e:
                    logger.warning(f"MCP景点服务调用失败: {e}")
            
            # 已移除爬虫功能，只使用百度地图和MCP数据
            
            # 根据行程天数对景点列表做一次软裁剪，避免数据过多或过少
            if len(attraction_data) > desired_min_attractions * 2:
                # 上限取“理论最少需求”的 2 倍，避免 LLM 提示太长
                new_len = desired_min_attractions * 2
                logger.info(
                    f"根据行程天数裁剪景点数量: 原始 {len(attraction_data)} 条，"
                    f"保留前 {new_len} 条（可通过 PLAN_MIN_ATTRACTIONS_PER_DAY 调整基数）"
                )
                attraction_data = attraction_data[:new_len]

            # 缓存数据
            await set_cache(cache_key_str, attraction_data, ttl=300)  # 5分钟缓存

            logger.info(
                f"收集到 {len(attraction_data)} 条景点数据（行程天数 {days} 天，"
                f"期望最少 {desired_min_attractions} 条）"
            )
            return attraction_data
            
        except Exception as e:
            logger.error(f"收集景点数据失败: {e}")
            return []
    
    async def collect_weather_data(
        self, 
        destination: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """收集天气数据"""
        try:
            cache_key_str = cache_key("weather", destination, start_date.date(), end_date.date())
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的天气数据: {destination}")
                return cached_data
            
            weather_data = {}
            
            # 根据环境变量配置选择天气数据源
            weather_source = settings.WEATHER_DATA_SOURCE.lower()
            logger.info(f"使用天气数据源: {weather_source}")
            
            if weather_source == "amap":
                # 使用高德地图天气API
                try:
                    weather_data = await self.amap_client.get_weather(
                        city=destination,
                        extensions="all"  # 获取预报天气
                    )
                    if weather_data:
                        logger.info(f"从高德地图获取到天气数据: {destination}")
                    else:
                        logger.warning(f"高德地图未返回天气数据: {destination}")
                except Exception as e:
                    logger.warning(f"高德地图天气服务调用失败: {e}")
                    
            elif weather_source == "baidu":
                # 使用百度地图天气API
                try:
                    # 暂时禁用百度地图天气API调用，等待正确的接口
                    logger.info(f"百度地图天气API暂时禁用，跳过天气数据收集: {destination}")
                except Exception as e:
                    logger.warning(f"百度地图天气服务调用失败: {e}")
                    
            elif weather_source == "openweather":
                # 使用OpenWeather API (通过MCP客户端)
                try:
                    weather_data = await self.mcp_client.get_weather(
                        destination=destination,
                        start_date=start_date.date(),
                        end_date=end_date.date()
                    )
                    if weather_data:
                        logger.info(f"从OpenWeather获取到天气数据: {destination}")
                    else:
                        logger.warning(f"OpenWeather未返回天气数据: {destination}")
                except Exception as e:
                    logger.warning(f"OpenWeather天气服务调用失败: {e}")
            
            # 如果主要数据源失败，尝试备用数据源
            if not weather_data and weather_source != "amap":
                try:
                    logger.info(f"主要天气数据源失败，尝试高德地图备用数据源: {destination}")
                    weather_data = await self.amap_client.get_weather(
                        city=destination,
                        extensions="all"
                    )
                    if weather_data:
                        logger.info(f"从高德地图备用数据源获取到天气数据: {destination}")
                except Exception as e:
                    logger.warning(f"高德地图备用天气服务调用失败: {e}")
            
            # 如果仍然没有数据，返回空字典
            if not weather_data:
                logger.warning(f"无法获取 {destination} 的天气数据")
                weather_data = {}
            
            # 缓存数据
            await set_cache(cache_key_str, weather_data, ttl=300)  # 5分钟缓存
            
            logger.info(f"收集到天气数据: {destination}")
            return weather_data
            
        except Exception as e:
            logger.error(f"收集天气数据失败: {e}")
            return {}
    
    async def collect_restaurant_data(
        self,
        destination: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """收集餐厅数据

        同样根据行程天数估算需要的餐厅数量：大致「天数 × 每天用餐次数」，并据此控制
        百度/高德/MCP 返回的数量，避免行程很长但餐厅数据太少或太多。
        """
        try:
            cache_key_str = cache_key(
                "restaurants",
                destination,
                (start_date.date() if isinstance(start_date, datetime) else None),
                (end_date.date() if isinstance(end_date, datetime) else None),
            )
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的餐厅数据: {destination}")
                return cached_data
            
            restaurant_data: List[Dict[str, Any]] = []

            # 根据行程天数估算需要的餐厅数量（粗略：天数 × 每天用餐次数）
            days = None
            if start_date and end_date:
                try:
                    days = (end_date.date() - start_date.date()).days + 1
                    if days <= 0:
                        days = None
                except Exception:
                    days = None
            if days is None:
                days = 1
            days = max(days, 1)

            desired_min_restaurants = max(self.plan_min_meals_per_day * days, 3)
            
            # 根据配置选择餐厅数据源
            restaurant_source = settings.RESTAURANT_DATA_SOURCE
            
            if restaurant_source in ["baidu", "both"]:
                # 使用内置百度地图功能
                try:
                    logger.info(f"使用内置百度地图功能收集餐厅数据: {destination}")
                    
                    # 搜索餐厅
                    restaurants_result = await map_search_places(
                        query="餐厅",
                        region=destination,
                        tag="美食",
                        is_china="true"
                    )
                    
                    if restaurants_result.get("status") == 0:
                        restaurants = restaurants_result.get("result", {}).get("items", [])
                        for restaurant in restaurants:  # 不提前裁剪
                            restaurant_item = {
                                "name": restaurant.get("name", "餐厅"),
                                "cuisine": restaurant.get("detail_info", {}).get("tag", "中餐"),
                                "rating": restaurant.get("detail_info", {}).get("overall_rating", "4.2"),
                                "address": restaurant.get("address", ""),
                                "coordinates": {
                                    "lat": restaurant.get("location", {}).get("lat"),
                                    "lng": restaurant.get("location", {}).get("lng")
                                },
                                "opening_hours": restaurant.get("detail_info", {}).get("open_time", "10:00-22:00"),
                                "specialties": restaurant.get("detail_info", {}).get("tag", "").split(",") if restaurant.get("detail_info", {}).get("tag") else ["特色菜"],
                                "source": "百度地图API"
                            }
                            restaurant_data.append(self._apply_price_metadata(
                                restaurant_item,
                                restaurant.get("detail_info", {}).get("price")
                            ))
                    
                    # 搜索特色小吃
                    snack_result = await map_search_places(
                        query="小吃",
                        region=destination,
                        tag="美食",
                        is_china="true"
                    )
                    
                    if snack_result.get("status") == 0:
                        snacks = snack_result.get("result", {}).get("items", [])
                        for snack in snacks:  # 不提前裁剪
                            restaurant_item = {
                                "name": snack.get("name", "小吃店"),
                                "cuisine": "小吃",
                                "rating": snack.get("detail_info", {}).get("overall_rating", "4.0"),
                                "address": snack.get("address", ""),
                                "coordinates": {
                                    "lat": snack.get("location", {}).get("lat"),
                                    "lng": snack.get("location", {}).get("lng")
                                },
                                "opening_hours": snack.get("detail_info", {}).get("open_time", "08:00-20:00"),
                                "specialties": ["特色小吃"],
                                "source": "百度地图API"
                            }
                            restaurant_data.append(self._apply_price_metadata(restaurant_item))
                    
                    logger.info(f"从百度地图API获取到 {len(restaurant_data)} 条餐厅数据")
                    
                except Exception as e:
                    logger.warning(f"百度地图餐厅API调用失败: {e}")
            
            if restaurant_source in ["amap", "both"]:
                # 使用高德地图周边搜索
                try:
                    logger.info(f"使用高德地图周边搜索收集餐厅数据: {destination}")
                    
                    # 使用统一的地理编码函数获取中心点坐标
                    geocode_info = await self.get_destination_geocode_info(destination)
                    
                    center_location = None
                    if geocode_info:
                        # 使用统一格式的坐标字符串
                        center_location = geocode_info['location_string']
                    
                    if center_location:
                        # 使用周边搜索获取餐厅数据
                        amap_restaurants = await self.amap_client.search_places_around(
                            location=center_location,
                            keywords="餐厅",
                            types="050000",  # 餐饮服务
                            radius=10000,    # 10公里半径
                            offset=20
                        )
                        
                        for amap_restaurant in amap_restaurants:  # 不提前裁剪
                            restaurant_item = {
                                "name": amap_restaurant.get("name", "餐厅"),
                                "cuisine": amap_restaurant.get("category", "中餐"),
                                "rating": amap_restaurant.get("rating", 4.0),
                                "cost": amap_restaurant.get("cost", ""),  # 原始人均消费字符串
                                "address": amap_restaurant.get("address", ""),
                                "coordinates": amap_restaurant.get("coordinates", {}),
                                "location": amap_restaurant.get("location", ""),
                                "phone": amap_restaurant.get("phone", ""),
                                "business_area": amap_restaurant.get("business_area", ""),
                                "cityname": amap_restaurant.get("cityname", ""),
                                "adname": amap_restaurant.get("adname", ""),
                                "opening_hours": "10:00-22:00",  # 高德地图不提供营业时间
                                "specialties": amap_restaurant.get("tags", ["特色菜"]),
                                "photos": amap_restaurant.get("photos", []),  # 餐厅图片
                                "typecode": amap_restaurant.get("typecode", ""),
                                "distance": amap_restaurant.get("distance", ""),
                                "source": "高德地图周边搜索"
                            }
                            restaurant_data.append(self._apply_price_metadata(
                                restaurant_item,
                                amap_restaurant.get("cost")
                            ))
                        
                        logger.info(f"从高德地图周边搜索获取到 {len(amap_restaurants)} 条餐厅数据")
                    else:
                        logger.warning(f"无法获取 {destination} 的坐标，跳过高德地图周边搜索")
                    
                except Exception as e:
                    logger.warning(f"高德地图餐厅周边搜索调用失败: {e}")
            
            # 如果数据仍然不足，使用MCP工具补充
            if len(restaurant_data) < desired_min_restaurants:
                try:
                    mcp_data = await self.mcp_client.get_restaurants(destination)
                    for item in mcp_data:
                        restaurant_data.append(self._apply_price_metadata(item))
                    logger.info(f"从MCP服务补充 {len(mcp_data)} 条餐厅数据")
                except Exception as e:
                    logger.warning(f"MCP餐厅服务调用失败: {e}")
            
            # 已移除爬虫功能，只使用百度地图和MCP数据
            
            # 根据行程天数对餐厅列表做一次软裁剪，避免过多
            max_restaurants = desired_min_restaurants * 2
            if len(restaurant_data) > max_restaurants:
                logger.info(
                    f"根据行程天数裁剪餐厅数量: 原始 {len(restaurant_data)} 条，"
                    f"保留前 {max_restaurants} 条（可通过 PLAN_MIN_MEALS_PER_DAY 调整基数）"
                )
                restaurant_data = restaurant_data[:max_restaurants]

            # 缓存数据
            await set_cache(cache_key_str, restaurant_data, ttl=300)  # 5分钟缓存

            logger.info(
                f"收集到 {len(restaurant_data)} 条餐厅数据（行程天数 {days} 天，"
                f"期望最少 {desired_min_restaurants} 条）"
            )
            return restaurant_data
            
        except Exception as e:
            logger.error(f"收集餐厅数据失败: {e}")
            return []
    
    async def collect_transportation_data(self, departure: str, destination: str, transportation_mode: Optional[str] = None) -> List[Dict[str, Any]]:
        """收集交通数据"""
        try:
            # 为不同出行方式生成不同的缓存键
            mode_key = transportation_mode if transportation_mode else "mixed"
            cache_key_str = cache_key("transportation", f"{departure}-{destination}-{mode_key}")
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的交通数据: {destination}, 出行方式: {transportation_mode or '混合'}")
                logger.debug(f"缓存的交通数据: {cached_data}")
                return cached_data
            
            transport_data = []
            
            # 根据地图服务提供商获取交通数据
            try:
                if self.map_provider == "amap":
                    logger.info(f"使用高德地图MCP服务收集交通数据: {destination}, 出行方式: {transportation_mode or '混合'}")
                    await self._collect_amap_transportation_data(departure, destination, transport_data, transportation_mode)
                else:
                    logger.info(f"使用百度地图功能收集交通数据: {destination}, 出行方式: {transportation_mode or '混合'}")
                    
                    # 根据出行方式收集不同的交通数据
                    if transportation_mode == "car":
                        # selves出行，获取驾车路线
                        await self._collect_driving_data(departure, destination, transport_data)
                    elif transportation_mode == "flight":
                        # 飞机出行，获取机场交通信息
                        await self._collect_flight_transport_data(departure, destination, transport_data)
                    elif transportation_mode == "train":
                        # 火车出行，获取火车站交通信息
                        await self._collect_train_transport_data(departure, destination, transport_data)
                    elif transportation_mode == "bus":
                        # 大巴出行，获取长途汽车站交通信息
                        await self._collect_bus_transport_data(departure, destination, transport_data)
                    else:
                        # 未指定或混合交通，收集所有交通方式
                        await self._collect_mixed_transport_data(departure, destination, transport_data)
                
                logger.info(f"从{self.map_provider}地图API获取到 {len(transport_data)} 条交通数据")
                
            except Exception as e:
                error_msg = str(e)
                if "不支持跨域公交路线规划" in error_msg:
                    logger.warning(f"跨城公交不支持，尝试其他交通方式: {e}")
                    # 跨城公交不支持时，提供替代方案
                    await self._add_intercity_alternatives(departure, destination, transport_data)
                else:
                    logger.warning(f"百度地图API调用失败: {e}")
                    # API失败时，不提供模拟数据，宁缺毋滥
            
            # 如果高德地图数据不足，使用MCP工具补充
            if len(transport_data) < 5 and self.map_provider != "amap":
                try:
                    mcp_data = await self.mcp_client.get_transportation(departure, destination)
                    transport_data.extend(mcp_data)
                    logger.info(f"从MCP服务补充 {len(mcp_data)} 条交通数据")
                except Exception as e:
                    logger.warning(f"MCP服务调用失败: {e}")
            elif len(transport_data) < 5:
                logger.info(f"高德地图已获取到 {len(transport_data)} 条数据，跳过MCP补充")
            
            # 已移除爬虫功能，只使用百度地图和MCP数据
            
            # 缓存数据 - 交通信息瞬息万变，缩短缓存时间
            await set_cache(cache_key_str, transport_data, ttl=1800)  # 30分钟缓存
            
            logger.info(f"收集到 {len(transport_data)} 条交通数据")
            return transport_data
            
        except Exception as e:
            logger.error(f"收集交通数据失败: {e}")
            return []
    
    def _estimate_driving_cost(self, distance_meters: int) -> str:
        """估算自驾费用"""
        distance_km = distance_meters // 1000
        
        # 基础费用计算：油费 + 过路费
        fuel_cost = distance_km * 0.6  # 每公里0.6元油费
        toll_cost = distance_km * 0.4  # 每公里0.4元过路费（估算）
        
        total_cost = fuel_cost + toll_cost
        
        return f"{total_cost:.1f}元"
    
    
    async def collect_all_data(
        self, 
        departure: str,
        destination: str, 
        start_date: datetime, 
        end_date: datetime,
        transportation_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """收集所有类型的数据"""
        logger.info(f"开始顺序收集 {destination} 的所有数据")
        data = {}

        interval_seconds = 1

        # 并发启动小红书数据收集任务（不受 MCP 并发限制）
        xhs_task = asyncio.create_task(self.collect_xiaohongshu_data(destination, start_date, end_date))

        try:
            data["flights"] = await self.collect_flight_data(departure, destination, start_date, end_date)
        except Exception as e:
            logger.exception("航班数据失败")
            data["flights"] = []
        await asyncio.sleep(interval_seconds)

        try:
            data["hotels"] = await self.collect_hotel_data(destination, start_date, end_date)
        except Exception:
            data["hotels"] = []
        await asyncio.sleep(interval_seconds)

        try:
            data["attractions"] = await self.collect_attraction_data(destination)
        except Exception:
            data["attractions"] = []
        await asyncio.sleep(interval_seconds)

        try:
            data["weather"] = await self.collect_weather_data(destination, start_date, end_date)
        except Exception:
            data["weather"] = {}
        await asyncio.sleep(interval_seconds)

        try:
            data["restaurants"] = await self.collect_restaurant_data(destination)
        except Exception:
            data["restaurants"] = []
        await asyncio.sleep(interval_seconds)

        try:
            data["transportation"] = await self.collect_transportation_data(departure, destination, transportation_mode)
        except Exception:
            data["transportation"] = []
        await asyncio.sleep(interval_seconds)

        # 等待小红书并发任务完成
        try:
            data["xiaohongshu_notes"] = await xhs_task
        except Exception as e:
            logger.exception(f"小红书数据收集失败: {e}")
            data["xiaohongshu_notes"] = []

        return data
    
    async def _collect_driving_data(self, departure: str, destination: str, transport_data: List[Dict[str, Any]]):
        """收集自驾交通数据"""
        try:
            # 使用内置百度地图功能
            from app.tools.baidu_maps_integration import map_directions
            
            directions_result = await map_directions(
                origin=departure,
                destination=destination,
                model="driving",
                is_china="true"
            )
            
            # 解析百度地图返回结果
            if directions_result and directions_result.get("status") == 0:
                routes = directions_result.get("result", {}).get("routes", [])
                for i, route in enumerate(routes[:3]):  # 取前3条路线
                    # 百度地图API返回的距离和时间字段
                    distance = route.get("distance", 0)  # 单位：米
                    duration = route.get("duration", 0)  # 单位：秒
                    
                    # 计算路况信息
                    traffic_info = route.get("traffic", {})
                    congestion_level = traffic_info.get("congestion", "未知")
                    road_conditions = traffic_info.get("road_conditions", [])
                    
                    transport_item = {
                        "id": f"baidu_driving_{i+1}",
                        "type": "自驾",
                        "name": f"驾车路线{i+1}",
                        "description": f"从{departure}到{destination}的自驾路线",
                        "duration": duration // 60 if duration > 0 else 0,  # 转换为分钟
                        "distance": distance // 1000 if distance > 0 else 0,  # 转换为公里
                        "price": int(float(self._estimate_driving_cost(distance).replace("元", ""))),
                        "currency": "CNY",
                        "operating_hours": "24小时",
                        "frequency": "随时",
                        "coverage": [destination],
                        "features": ["实时路况", "多方案选择"],
                        "route": f"驾车路线{i+1}",
                        "traffic_conditions": {
                            "congestion_level": congestion_level,
                            "road_conditions": road_conditions,
                            "real_time": True
                        },
                        "source": "百度地图API"
                    }
                    transport_data.append(transport_item)

                    logger.debug(f"收集自驾数据: {transport_item}")
                    
        except Exception as e:
            logger.warning(f"收集自驾数据失败: {e}")
    
    async def _collect_flight_transport_data(self, departure: str, destination: str, transport_data: List[Dict[str, Any]]):
        """收集飞机交通数据"""
        try:
            # 使用内置百度地图功能
            from app.tools.baidu_maps_integration import map_search_places
            
            airport_query = f"{destination}机场"
            places_result = await map_search_places(
                query=airport_query,
                region=destination,
                tag="交通设施服务",
                is_china="true"
            )
            
            # 解析百度地图返回结果
            if places_result and places_result.get("status") == 0:
                places = places_result.get("results", [])
                for place in places[:2]:  # 取前2个机场
                    transport_item = {
                        "id": f"baidu_airport_{len(transport_data)+1}",
                        "type": "机场",
                        "name": place.get('name', '机场'),
                        "description": f"{place.get('name', '机场')} - {place.get('address', '')}",
                        "duration": 120,  # 估算机场交通时间
                        "distance": 30,   # 估算距离
                        "price": 125,  # 取中间值
                        "currency": "CNY",
                        "operating_hours": "24小时",
                        "frequency": "30-60分钟",
                        "coverage": [destination],
                        "features": ["机场大巴", "出租车", "地铁"],
                        "route": place.get('name', '机场'),
                        "source": "百度地图API"
                    }
                    transport_data.append(transport_item)
                    
        except Exception as e:
            logger.warning(f"收集飞机交通数据失败: {e}")
    
    async def _collect_train_transport_data(self, departure: str, destination: str, transport_data: List[Dict[str, Any]]):
        """收集火车交通数据"""
        try:
            # 使用内置百度地图功能
            from app.tools.baidu_maps_integration import map_search_places
            
            station_query = f"{destination}火车站"
            places_result = await map_search_places(
                query=station_query,
                region=destination,
                tag="交通设施服务",
                is_china="true"
            )
            
            # 解析百度地图返回结果
            if places_result and places_result.get("status") == 0:
                places = places_result.get("results", [])
                for place in places[:2]:  # 取前2个火车站
                    transport_item = {
                        "id": f"baidu_train_{len(transport_data)+1}",
                        "type": "火车站",
                        "name": place.get('name', '火车站'),
                        "description": f"{place.get('name', '火车站')} - {place.get('address', '')}",
                        "duration": 60,  # 估算火车站交通时间
                        "distance": 15,   # 估算距离
                        "price": 30,  # 取中间值
                        "currency": "CNY",
                        "operating_hours": "05:00-23:00",
                        "frequency": "15-30分钟",
                        "coverage": [destination],
                        "features": ["公交", "地铁", "出租车"],
                        "route": place.get('name', '火车站'),
                        "source": "百度地图API"
                    }
                    transport_data.append(transport_item)
                    
        except Exception as e:
            logger.warning(f"收集火车交通数据失败: {e}")
    
    async def _collect_bus_transport_data(self, departure: str, destination: str, transport_data: List[Dict[str, Any]]):
        """收集大巴交通数据"""
        try:
            # 使用内置百度地图功能
            from app.tools.baidu_maps_integration import map_search_places
            
            bus_station_query = f"{destination}汽车站"
            places_result = await map_search_places(
                query=bus_station_query,
                region=destination,
                tag="交通设施服务",
                is_china="true"
            )
            
            # 解析百度地图返回结果
            if places_result and places_result.get("status") == 0:
                places = places_result.get("results", [])
                for place in places[:2]:  # 取前2个汽车站
                    transport_item = {
                        "id": f"baidu_bus_{len(transport_data)+1}",
                        "type": "汽车站",
                        "name": place.get('name', '汽车站'),
                        "description": f"{place.get('name', '汽车站')} - {place.get('address', '')}",
                        "duration": 45,  # 估算汽车站交通时间
                        "distance": 10,   # 估算距离
                        "price": 17,  # 取中间值
                        "currency": "CNY",
                        "operating_hours": "06:00-22:00",
                        "frequency": "10-20分钟",
                        "coverage": [destination],
                        "features": ["公交", "出租车"],
                        "route": place.get('name', '汽车站'),
                        "source": "百度地图API"
                    }
                    transport_data.append(transport_item)
                    
        except Exception as e:
            logger.warning(f"收集大巴交通数据失败: {e}")
    
    async def _collect_mixed_transport_data(self, departure: str, destination: str, transport_data: List[Dict[str, Any]]):
        """收集混合交通数据"""
        try:
            # 收集多种交通方式
            tasks = [
                self._collect_driving_data(departure, destination, transport_data),
                self._collect_flight_transport_data(departure, destination, transport_data),
                self._collect_train_transport_data(departure, destination, transport_data),
                self._collect_bus_transport_data(departure, destination, transport_data)
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 添加公共交通信息
            from app.tools.baidu_maps_integration import map_directions
            
            directions_result = await map_directions(
                origin=departure,
                destination=destination,
                model="transit",
                is_china="true"
            )
            
            # 解析百度地图返回结果
            if directions_result and directions_result.get("status") == 0:
                routes = directions_result.get("result", {}).get("routes", [])
                for i, route in enumerate(routes[:2]):  # 取前2条公交路线
                    transport_item = {
                        "id": f"baidu_transit_{i+1}",
                        "type": "公交",
                        "name": f"公交路线{i+1}",
                        "description": f"从{departure}到{destination}的公交路线",
                        "duration": route.get("duration", 0) // 60,  # 转换为分钟
                        "distance": route.get("distance", 0) // 1000,  # 转换为公里
                        "price": 5,  # 取中间值
                        "currency": "CNY",
                        "operating_hours": "06:00-23:00",
                        "frequency": "5-15分钟",
                        "coverage": [destination],
                        "features": ["实时到站", "多方案选择"],
                        "route": f"公交路线{i+1}",
                        "source": "百度地图API"
                    }
                    transport_data.append(transport_item)
                    
        except Exception as e:
            logger.warning(f"收集混合交通数据失败: {e}")
    
    async def _calculate_intercity_distance(self, departure: str, destination: str) -> tuple[int, int]:
        """计算跨城距离和时间"""
        try:
            # 根据环境变量选择地图API
            if self.map_provider == "amap":
                # 使用高德地图API获取实际距离
                amap_routes = await self.amap_client.get_directions(
                    origin=departure,
                    destination=destination,
                    mode="driving"
                )
                
                if amap_routes and len(amap_routes) > 0:
                    route = amap_routes[0]  # 取第一条路线
                    distance_km = route.get("distance", 0)
                    duration_minutes = route.get("duration", 0)
                    
                    if distance_km > 0 and duration_minutes > 0:
                        logger.info(f"从高德地图获取到{departure}到{destination}的实际距离: {distance_km}公里, 时间: {duration_minutes}分钟")
                        return int(distance_km), int(duration_minutes)
            else:
                # 使用百度地图API获取实际距离
                from app.tools.baidu_maps_integration import map_directions
                
                directions_result = await map_directions(
                    origin=departure,
                    destination=destination,
                    model="driving",
                    is_china="true"
                )
                
                if directions_result and directions_result.get("status") == 0:
                    routes = directions_result.get("result", {}).get("routes", [])
                    if routes:
                        route = routes[0]  # 取第一条路线
                        distance_meters = route.get("distance", 0)
                        duration_seconds = route.get("duration", 0)
                        
                        distance_km = distance_meters // 1000 if distance_meters > 0 else 500  # 默认500公里
                        duration_minutes = duration_seconds // 60 if duration_seconds > 0 else distance_km * 1.2  # 默认每公里1.2分钟
                        
                        logger.info(f"从百度地图获取到{departure}到{destination}的实际距离: {distance_km}公里, 时间: {duration_minutes}分钟")
                        return int(distance_km), int(duration_minutes)
            
            # 如果API调用失败，使用城市间距离估算
            city_distances = {
                ("西安", "杭州"): (1200, 720),  # 1200公里, 12小时
                ("北京", "上海"): (1200, 720),
                ("广州", "深圳"): (120, 120),
                ("成都", "重庆"): (300, 180),
                ("武汉", "长沙"): (350, 210),
            }
            
            # 尝试匹配城市对
            for (dep, dest), (dist, dur) in city_distances.items():
                if (dep in departure and dest in destination) or (dest in departure and dep in destination):
                    logger.info(f"使用预设距离: {departure}到{destination} = {dist}公里")
                    return dist, dur
            
            # 默认估算：0公里，0小时
            logger.warning(f"无法获取{departure}到{destination}的准确距离，使用默认值0公里")
            return 0, 0
            
        except Exception as e:
            logger.warning(f"计算跨城距离失败: {e}，使用默认值")
            return 0, 0

    async def _add_intercity_alternatives(self, departure: str, destination: str, transport_data: List[Dict[str, Any]]):
        """为跨城路线添加替代交通方案"""
        try:
            # 计算实际距离和时间
            distance_km, driving_duration = await self._calculate_intercity_distance(departure, destination)
            
            # 根据距离调整各种交通方式的时间和价格
            train_duration = max(60, int(distance_km * 0.5))  # 高铁速度约200km/h
            bus_duration = max(120, int(distance_km * 0.8))   # 大巴速度约125km/h
            
            train_price = max(80, int(distance_km * 0.5))     # 高铁约0.5元/公里
            bus_price = max(40, int(distance_km * 0.3))       # 大巴约0.3元/公里
            driving_price = max(60, int(distance_km * 0.8))   # 自驾约0.8元/公里（油费+过路费）
            
            # 添加高铁/火车方案
            train_item = {
                "id": f"intercity_train_{len(transport_data)+1}",
                "type": "高铁/火车",
                "name": f"{departure}到{destination}高铁",
                "description": f"从{departure}到{destination}的高铁/火车方案",
                "duration": train_duration,
                "distance": distance_km,
                "price": train_price,
                "currency": "CNY",
                "operating_hours": "06:00-22:00",
                "frequency": "30-60分钟",
                "coverage": [destination],
                "features": ["高铁", "火车", "城际列车"],
                "route": f"{departure}站-{destination}站",
                "source": "跨城替代方案"
            }
            transport_data.append(train_item)
            
            # 添加长途汽车方案
            bus_item = {
                "id": f"intercity_bus_{len(transport_data)+1}",
                "type": "长途汽车",
                "name": f"{departure}到{destination}大巴",
                "description": f"从{departure}到{destination}的长途汽车方案",
                "duration": bus_duration,
                "distance": distance_km,
                "price": bus_price,
                "currency": "CNY",
                "operating_hours": "06:00-20:00",
                "frequency": "60-120分钟",
                "coverage": [destination],
                "features": ["长途汽车", "直达"],
                "route": f"{departure}汽车站-{destination}汽车站",
                "source": "跨城替代方案"
            }
            transport_data.append(bus_item)
            
            # 添加自驾方案
            driving_item = {
                "id": f"intercity_driving_{len(transport_data)+1}",
                "type": "自驾",
                "name": f"{departure}到{destination}自驾",
                "description": f"从{departure}到{destination}的自驾方案",
                "duration": driving_duration,
                "distance": distance_km,
                "price": driving_price,
                "currency": "CNY",
                "operating_hours": "24小时",
                "frequency": "随时",
                "coverage": [destination],
                "features": ["自驾", "灵活"],
                "route": f"{departure}-{destination}",
                "source": "跨城替代方案"
            }
            transport_data.append(driving_item)
            
            logger.info(f"为跨城路线添加了3个替代方案，距离: {distance_km}公里")
            
        except Exception as e:
            logger.warning(f"添加跨城替代方案失败: {e}")
    
    async def _collect_amap_transportation_data(
        self, 
        departure: str, 
        destination: str, 
        transport_data: List[Dict[str, Any]], 
        transportation_mode: Optional[str] = None
    ):
        """使用高德地图MCP服务收集交通数据"""
        try:
            # 根据出行方式选择路线规划模式
            if transportation_mode == "car":
                mode = "driving"
            elif transportation_mode == "transit":
                mode = "transit"
            else:
                mode = "transit"  # 默认使用公共交通
            
            # 获取路线规划数据
            amap_routes = await self.amap_client.get_directions(
                origin=departure,
                destination=destination,
                mode=mode
            )
            
            if amap_routes:
                transport_data.extend(amap_routes)
                logger.info(f"从高德地图MCP获取到 {len(amap_routes)} 条交通数据")
            
            # 如果数据不足，添加替代方案
            if len(transport_data) < 3:
                await self._add_intercity_alternatives(departure, destination, transport_data)
                
        except Exception as e:
            logger.warning(f"高德地图交通数据收集失败: {e}")
            # 失败时添加替代方案
            await self._add_intercity_alternatives(departure, destination, transport_data)
    
    async def _collect_amap_attraction_data(
        self, 
        destination: str, 
        attraction_data: List[Dict[str, Any]]
    ):
        """使用高德地图周边搜索收集景点数据"""
        try:
            # 首先获取目的地的坐标
            city_name = await self.city_resolver.resolve_city(destination)
            
            # 使用统一的地理编码函数获取中心点坐标
            geocode_info = await self.get_destination_geocode_info(destination)
            
            center_location = None
            if geocode_info:
                # 使用统一格式的坐标字符串
                center_location = geocode_info['location_string']
            
            if center_location:
                # 使用周边搜索获取景点数据
                attractions = await self.amap_client.search_places_around(
                    location=center_location,
                    keywords="景点",
                    types="110000",  # 风景名胜
                    radius=20000,    # 20公里半径
                    offset=20
                )
                
                if attractions:
                    attraction_data.extend(attractions)
                    logger.info(f"从高德地图周边搜索获取到 {len(attractions)} 条景点数据")
                
                # 搜索博物馆
                museums = await self.amap_client.search_places_around(
                    location=center_location,
                    keywords="博物馆",
                    types="140700",  # 科教文化服务
                    radius=20000,    # 20公里半径
                    offset=10
                )
                
                if museums:
                    attraction_data.extend(museums)
                    logger.info(f"从高德地图周边搜索获取到 {len(museums)} 条博物馆数据")
            else:
                logger.warning(f"无法获取 {destination} 的坐标，跳过高德地图周边搜索")
        except Exception as e:
            logger.warning(f"高德地图景点数据收集失败: {e}")
    
    async def collect_xiaohongshu_data(
        self, 
        destination: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        收集小红书数据（通过API服务）
        
        Args:
            destination: 目的地名称
            start_date: 旅行开始日期（可选，用于计算天数）
            end_date: 旅行结束日期（可选，用于计算天数）
            
        Returns:
            List[Dict[str, Any]]: 小红书笔记数据列表
        """
        try:
            # 根据旅行天数自适应计算爬取数量
            days = None
            if start_date and end_date:
                try:
                    days = (end_date - start_date).days + 1
                    if days <= 0:
                        days = None
                except Exception:
                    days = None
            
            if days is not None and days > 0:
                # 每天2-3条笔记，最少3条，最多24条
                limit = max(3, min(24, days * 2 + 1))
                logger.info(f"🔍 开始收集小红书数据: {destination}，旅行天数: {days}天，检索数量: {limit}条，检索内容：{destination}旅游攻略")
            else:
                # 默认12条
                limit = 12
                logger.info(f"🔍 开始收集小红书数据: {destination}，检索内容：{destination}旅游攻略（默认数量: {limit}条）")
            
            # 使用小红书API客户端搜索笔记
            response = await self.xhs_client.search_notes(f"{destination}旅游攻略", limit=limit)
            
            if not response or response.get("status") != "success":
                logger.error(f"❌ 小红书API调用失败: {response}")
                return []
            
            # 解析API返回的笔记数据
            notes_data = []
            results = response.get("results", [])
            
            for note_data in results:
                try:
                    note_dict = {
                        "note_id": note_data.get("note_id", ""),
                        "title": note_data.get("title", ""),
                        "desc": note_data.get("desc", ""),
                        "img_urls": note_data.get("img_urls", []),
                        "tag_list": note_data.get("tag_list", []),
                        "liked_count": note_data.get("liked_count", 0),
                        "location": note_data.get("location", ""),
                        "relevance_score": note_data.get("relevance_score", 0.0),
                        "url": note_data.get("url", "")
                    }
                    notes_data.append(note_dict)
                except Exception as e:
                    logger.warning(f"⚠️ 解析笔记数据失败: {e}")
                    continue
            
            logger.info(f"✅ 成功收集到 {len(notes_data)} 条小红书数据: {destination}")
            return notes_data
            
        except Exception as e:
            logger.error(f"❌ 收集小红书数据失败: {destination}, 错误: {e}")
            logger.error("💡 请确保小红书API服务正在运行: python xhs_api_server.py")
            logger.error("🔐 如果API服务提示需要登录，请运行: python xhs_login_helper.py")
            return []
    
    def format_xiaohongshu_data_for_llm(self, destination: str, notes_data: List[Dict[str, Any]]) -> str:
        """
        将小红书数据格式化为适合LLM处理的文本
        
        Args:
            destination: 目的地名称
            notes_data: 小红书笔记数据列表
            
        Returns:
            str: 格式化后的文本
        """
        try:
            if not notes_data:
                return f"未找到关于{destination}的小红书用户分享内容。"
            
            # 直接格式化笔记数据为文本
            formatted_text = f"=== 小红书用户分享 - {destination} ===\n\n"
            
            for i, note in enumerate(notes_data, 1):
                title = note.get("title", "无标题")
                desc = note.get("desc", "")
                liked_count = note.get("liked_count", 0)
                location = note.get("location", "")
                tag_list = note.get("tag_list", [])
                
                formatted_text += f"{i}. 【{title}】\n"
                
                if desc:
                    # 限制描述长度，避免过长
                    desc_preview = desc[:200] + "..." if len(desc) > 200 else desc
                    formatted_text += f"   内容: {desc_preview}\n"
                
                if location:
                    formatted_text += f"   位置: {location}\n"
                
                if tag_list:
                    tags = ", ".join(tag_list[:5])  # 最多显示5个标签
                    formatted_text += f"   标签: {tags}\n"
                
                formatted_text += f"   点赞数: {liked_count}\n\n"
            
            formatted_text += f"以上是来自小红书的 {len(notes_data)} 条用户真实分享，可以作为{destination}旅行规划的参考。"
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"格式化小红书数据失败: {e}")
            return f"小红书数据格式化失败，但收集到 {len(notes_data)} 条相关笔记。"


    async def close(self):
        """关闭HTTP客户端"""
        try:
            await self.http_client.aclose()
        except Exception:
            pass
        try:
            await self.city_resolver.close()
        except Exception:
            pass
        try:
            await self.mcp_client.close()
        except Exception:
            pass
        try:
            await self.amap_client.close()
        except Exception:
            pass
        try:
            await self.xhs_client.close()
        except Exception:
            pass
