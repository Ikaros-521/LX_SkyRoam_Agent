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
from app.services.web_scraper import WebScraper
from app.core.redis import get_cache, set_cache, cache_key


class DataCollector:
    """数据收集器"""
    
    def __init__(self):
        self.mcp_client = MCPClient()
        self.web_scraper = WebScraper()
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def collect_flight_data(
        self, 
        destination: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """收集航班数据"""
        try:
            cache_key_str = cache_key("flights", destination, start_date.date(), end_date.date())
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的航班数据: {destination}")
                return cached_data
            
            # 使用MCP工具收集航班信息
            flight_data = await self.mcp_client.get_flights(
                destination=destination,
                departure_date=start_date.date(),
                return_date=end_date.date()
            )
            
            # 如果MCP数据不足，使用爬虫补充
            if len(flight_data) < 5:
                scraped_flights = await self.web_scraper.scrape_flights(
                    destination, start_date, end_date
                )
                flight_data.extend(scraped_flights)
            
            # 缓存数据
            await set_cache(cache_key_str, flight_data, ttl=3600)  # 1小时缓存
            
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
            
            # 如果MCP数据不足，使用爬虫补充
            if len(hotel_data) < 10:
                scraped_hotels = await self.web_scraper.scrape_hotels(
                    destination, start_date, end_date
                )
                hotel_data.extend(scraped_hotels)
            
            # 缓存数据
            await set_cache(cache_key_str, hotel_data, ttl=7200)  # 2小时缓存
            
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
            
            # 使用MCP工具收集景点信息
            attraction_data = await self.mcp_client.get_attractions(destination)
            
            # 如果MCP数据不足，使用爬虫补充
            if len(attraction_data) < 20:
                scraped_attractions = await self.web_scraper.scrape_attractions(destination)
                attraction_data.extend(scraped_attractions)
            
            # 缓存数据
            await set_cache(cache_key_str, attraction_data, ttl=86400)  # 24小时缓存
            
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
            
            # 使用MCP工具收集天气信息
            weather_data = await self.mcp_client.get_weather(
                destination=destination,
                start_date=start_date.date(),
                end_date=end_date.date()
            )
            
            # 缓存数据
            await set_cache(cache_key_str, weather_data, ttl=1800)  # 30分钟缓存
            
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
            
            # 使用MCP工具收集餐厅信息
            restaurant_data = await self.mcp_client.get_restaurants(destination)
            
            # 如果MCP数据不足，使用爬虫补充
            if len(restaurant_data) < 15:
                scraped_restaurants = await self.web_scraper.scrape_restaurants(destination)
                restaurant_data.extend(scraped_restaurants)
            
            # 缓存数据
            await set_cache(cache_key_str, restaurant_data, ttl=43200)  # 12小时缓存
            
            logger.info(f"收集到 {len(restaurant_data)} 条餐厅数据")
            return restaurant_data
            
        except Exception as e:
            logger.error(f"收集餐厅数据失败: {e}")
            return []
    
    async def collect_transportation_data(self, destination: str) -> List[Dict[str, Any]]:
        """收集交通数据"""
        try:
            cache_key_str = cache_key("transportation", destination)
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的交通数据: {destination}")
                return cached_data
            
            # 使用MCP工具收集交通信息
            transport_data = await self.mcp_client.get_transportation(destination)
            
            # 如果MCP数据不足，使用爬虫补充
            if len(transport_data) < 10:
                scraped_transport = await self.web_scraper.scrape_transportation(destination)
                transport_data.extend(scraped_transport)
            
            # 缓存数据
            await set_cache(cache_key_str, transport_data, ttl=86400)  # 24小时缓存
            
            logger.info(f"收集到 {len(transport_data)} 条交通数据")
            return transport_data
            
        except Exception as e:
            logger.error(f"收集交通数据失败: {e}")
            return []
    
    async def collect_all_data(
        self, 
        destination: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """收集所有类型的数据"""
        logger.info(f"开始收集 {destination} 的所有数据")
        
        # 并行收集所有数据
        tasks = [
            self.collect_flight_data(destination, start_date, end_date),
            self.collect_hotel_data(destination, start_date, end_date),
            self.collect_attraction_data(destination),
            self.collect_weather_data(destination, start_date, end_date),
            self.collect_restaurant_data(destination),
            self.collect_transportation_data(destination)
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
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()
