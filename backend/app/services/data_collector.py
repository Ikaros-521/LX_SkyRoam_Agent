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
from app.core.redis import get_cache, set_cache, cache_key


class DataCollector:
    """数据收集器"""
    
    def __init__(self):
        self.mcp_client = MCPClient()
        self.amap_client = AmapMCPClient()
        self.city_resolver = CityResolver()
        # self.web_scraper = WebScraper()  # 已移除爬虫功能
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            proxies={}
        )
        self.map_provider = settings.MAP_PROVIDER  # 地图服务提供商
    
    async def collect_flight_data(
        self, 
        departure: str,
        destination: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """收集航班数据"""
        try:
            cache_key_str = cache_key("flights", f"{departure}-{destination}", start_date.date(), end_date.date())
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的航班数据: {destination}")
                return cached_data
            
            # 使用MCP工具收集航班信息
            flight_data = await self.mcp_client.get_flights(
                destination=destination,
                departure_date=start_date.date(),
                return_date=end_date.date(),
                origin=departure
            )
            
            # 已移除爬虫功能，只使用MCP数据
            
            # 缓存数据
            await set_cache(cache_key_str, flight_data, ttl=300)  # 5分钟缓存
            
            logger.info(f"收集到 {len(flight_data)} 条航班数据")
            return flight_data
            
        except Exception as e:
            logger.error(f"收集航班数据失败: {e}")
            return []
    
    async def collect_hotel_data(
        self, 
        destination: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """收集酒店数据"""
        try:
            cache_key_str = cache_key("hotels", destination, start_date.date(), end_date.date())
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的酒店数据: {destination}")
                return cached_data
            
            # 使用MCP工具收集酒店信息
            hotel_data = await self.mcp_client.get_hotels(
                destination=destination,
                check_in=start_date.date(),
                check_out=end_date.date()
            )
            
            # 已移除爬虫功能，只使用MCP数据
            
            # 缓存数据
            await set_cache(cache_key_str, hotel_data, ttl=300)  # 5分钟缓存
            
            logger.info(f"收集到 {len(hotel_data)} 条酒店数据")
            return hotel_data
            
        except Exception as e:
            logger.error(f"收集酒店数据失败: {e}")
            return []
    
    async def collect_attraction_data(self, destination: str) -> List[Dict[str, Any]]:
        """收集景点数据"""
        try:
            cache_key_str = cache_key("attractions", destination)
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的景点数据: {destination}")
                return cached_data
            
            attraction_data = []
            
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
                        for place in places[:10]:  # 取前10个景点
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
                        for museum in museums[:5]:  # 取前5个博物馆
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
            
            # 如果百度地图数据不足，使用MCP工具补充
            if len(attraction_data) < 10:
                try:
                    mcp_data = await self.mcp_client.get_attractions(destination)
                    attraction_data.extend(mcp_data)
                    logger.info(f"从MCP服务补充 {len(mcp_data)} 条景点数据")
                except Exception as e:
                    logger.warning(f"MCP景点服务调用失败: {e}")
            
            # 已移除爬虫功能，只使用百度地图和MCP数据
            
            # 缓存数据
            await set_cache(cache_key_str, attraction_data, ttl=300)  # 5分钟缓存
            
            logger.info(f"收集到 {len(attraction_data)} 条景点数据")
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
    
    async def collect_restaurant_data(self, destination: str) -> List[Dict[str, Any]]:
        """收集餐厅数据"""
        try:
            cache_key_str = cache_key("restaurants", destination)
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的餐厅数据: {destination}")
                return cached_data
            
            restaurant_data = []
            
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
                        for restaurant in restaurants[:10]:  # 取前10个餐厅
                            restaurant_item = {
                                "name": restaurant.get("name", "餐厅"),
                                "cuisine": restaurant.get("detail_info", {}).get("tag", "中餐"),
                                "rating": restaurant.get("detail_info", {}).get("overall_rating", "4.2"),
                                "price_range": "$$" if restaurant.get("detail_info", {}).get("price") else "$$$",
                                "address": restaurant.get("address", ""),
                                "coordinates": {
                                    "lat": restaurant.get("location", {}).get("lat"),
                                    "lng": restaurant.get("location", {}).get("lng")
                                },
                                "opening_hours": restaurant.get("detail_info", {}).get("open_time", "10:00-22:00"),
                                "specialties": restaurant.get("detail_info", {}).get("tag", "").split(",") if restaurant.get("detail_info", {}).get("tag") else ["特色菜"],
                                "source": "百度地图API"
                            }
                            restaurant_data.append(restaurant_item)
                    
                    # 搜索特色小吃
                    snack_result = await map_search_places(
                        query="小吃",
                        region=destination,
                        tag="美食",
                        is_china="true"
                    )
                    
                    if snack_result.get("status") == 0:
                        snacks = snack_result.get("result", {}).get("items", [])
                        for snack in snacks[:5]:  # 取前5个小吃店
                            restaurant_item = {
                                "name": snack.get("name", "小吃店"),
                                "cuisine": "小吃",
                                "rating": snack.get("detail_info", {}).get("overall_rating", "4.0"),
                                "price_range": "$",
                                "address": snack.get("address", ""),
                                "coordinates": {
                                    "lat": snack.get("location", {}).get("lat"),
                                    "lng": snack.get("location", {}).get("lng")
                                },
                                "opening_hours": snack.get("detail_info", {}).get("open_time", "08:00-20:00"),
                                "specialties": ["特色小吃"],
                                "source": "百度地图API"
                            }
                            restaurant_data.append(restaurant_item)
                    
                    logger.info(f"从百度地图API获取到 {len(restaurant_data)} 条餐厅数据")
                    
                except Exception as e:
                    logger.warning(f"百度地图餐厅API调用失败: {e}")
            
            if restaurant_source in ["amap", "both"]:
                # 使用高德地图周边搜索
                try:
                    logger.info(f"使用高德地图周边搜索收集餐厅数据: {destination}")
                    
                    # 首先获取目的地的坐标
                    city_name = await self.city_resolver.resolve_city(destination)
                    
                    # 使用高德地图地理编码获取中心点坐标
                    from app.tools.baidu_maps_integration import map_geocode
                    geocode_result = await map_geocode(destination)
                    
                    center_location = None
                    if geocode_result.get("status") == 0:
                        location_info = geocode_result.get("result", {}).get("location", {})
                        if location_info:
                            # 百度地图坐标转高德地图坐标格式 (经度,纬度)
                            center_location = f"{location_info.get('lng')},{location_info.get('lat')}"
                    
                    if center_location:
                        # 使用周边搜索获取餐厅数据
                        amap_restaurants = await self.amap_client.search_places_around(
                            location=center_location,
                            keywords="餐厅",
                            types="050000",  # 餐饮服务
                            radius=10000,    # 10公里半径
                            offset=20
                        )
                        
                        for amap_restaurant in amap_restaurants[:10]:  # 取前10个餐厅
                            restaurant_item = {
                                "name": amap_restaurant.get("name", "餐厅"),
                                "cuisine": amap_restaurant.get("category", "中餐"),
                                "rating": amap_restaurant.get("rating", 4.0),
                                "price_range": amap_restaurant.get("price_range", "$$"),
                                "cost": amap_restaurant.get("cost", ""),  # 人均消费
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
                            restaurant_data.append(restaurant_item)
                        
                        logger.info(f"从高德地图周边搜索获取到 {len(amap_restaurants)} 条餐厅数据")
                    else:
                        logger.warning(f"无法获取 {destination} 的坐标，跳过高德地图周边搜索")
                    
                except Exception as e:
                    logger.warning(f"高德地图餐厅周边搜索调用失败: {e}")
            
            # 如果数据仍然不足，使用MCP工具补充
            if len(restaurant_data) < 10:
                try:
                    mcp_data = await self.mcp_client.get_restaurants(destination)
                    restaurant_data.extend(mcp_data)
                    logger.info(f"从MCP服务补充 {len(mcp_data)} 条餐厅数据")
                except Exception as e:
                    logger.warning(f"MCP餐厅服务调用失败: {e}")
            
            # 已移除爬虫功能，只使用百度地图和MCP数据
            
            # 缓存数据
            await set_cache(cache_key_str, restaurant_data, ttl=300)  # 5分钟缓存
            
            logger.info(f"收集到 {len(restaurant_data)} 条餐厅数据")
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
                        # 自驾出行，获取驾车路线
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
        logger.info(f"开始收集 {destination} 的所有数据")
        
        # 并行收集所有数据
        tasks = [
            self.collect_flight_data(departure, destination, start_date, end_date),
            self.collect_hotel_data(destination, start_date, end_date),
            self.collect_attraction_data(destination),
            self.collect_weather_data(destination, start_date, end_date),
            self.collect_restaurant_data(destination),
            self.collect_transportation_data(departure, destination, transportation_mode)  # 根据指定出行方式收集交通数据
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "flights": results[0] if not isinstance(results[0], Exception) else [],
            "hotels": results[1] if not isinstance(results[1], Exception) else [],
            "attractions": results[2] if not isinstance(results[2], Exception) else [],
            "weather": results[3] if not isinstance(results[3], Exception) else {},
            "restaurants": results[4] if not isinstance(results[4], Exception) else [],
            "transportation": results[5] if not isinstance(results[5], Exception) else []
        }
    
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
    
    async def _add_intercity_alternatives(self, departure: str, destination: str, transport_data: List[Dict[str, Any]]):
        """为跨城路线添加替代交通方案"""
        try:
            # 添加高铁/火车方案
            train_item = {
                "id": f"intercity_train_{len(transport_data)+1}",
                "type": "高铁/火车",
                "name": f"{departure}到{destination}高铁",
                "description": f"从{departure}到{destination}的高铁/火车方案",
                "duration": 60,  # 估算时间
                "distance": 50,  # 估算距离
                "price": 80,  # 估算价格
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
                "duration": 120,  # 估算时间
                "distance": 50,  # 估算距离
                "price": 40,  # 估算价格
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
                "duration": 90,  # 估算时间
                "distance": 50,  # 估算距离
                "price": 60,  # 估算费用（油费+过路费）
                "currency": "CNY",
                "operating_hours": "24小时",
                "frequency": "随时",
                "coverage": [destination],
                "features": ["自驾", "灵活"],
                "route": f"{departure}-{destination}",
                "source": "跨城替代方案"
            }
            transport_data.append(driving_item)
            
            logger.info(f"为跨城路线添加了 {len(transport_data)} 个替代方案")
            
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
            
            # 使用百度地图地理编码获取中心点坐标
            from app.tools.baidu_maps_integration import map_geocode
            geocode_result = await map_geocode(destination)
            
            center_location = None
            if geocode_result.get("status") == 0:
                location_info = geocode_result.get("result", {}).get("location", {})
                if location_info:
                    # 百度地图坐标转高德地图坐标格式 (经度,纬度)
                    center_location = f"{location_info.get('lng')},{location_info.get('lat')}"
            
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
            logger.warning(f"高德地图景点周边搜索失败: {e}")


    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()
        await self.city_resolver.close()
