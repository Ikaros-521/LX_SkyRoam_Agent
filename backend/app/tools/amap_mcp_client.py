"""
高德地图 MCP 客户端
支持 Streamable HTTP 和 SSE 方式接入
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from loguru import logger
import httpx
from app.core.config import settings


class AmapMCPClient:
    """高德地图 MCP 客户端"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=settings.MCP_TIMEOUT, proxies={})
        self.api_key = settings.AMAP_API_KEY
        self.mode = settings.AMAP_MCP_MODE
        
        # 根据模式选择URL
        if self.mode == "sse":
            self.base_url = f"{settings.AMAP_MCP_SSE_URL}?key={self.api_key}"
        else:
            self.base_url = f"{settings.AMAP_MCP_HTTP_URL}?key={self.api_key}"
    
    async def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "transit"
    ) -> List[Dict[str, Any]]:
        """获取路线规划"""
        try:
            if not self.api_key:
                logger.warning("高德地图API密钥未配置")
                return []
            
            if self.mode == "sse":
                return await self._get_directions_sse(origin, destination, mode)
            else:
                return await self._get_directions_http(origin, destination, mode)
                
        except Exception as e:
            logger.error(f"获取高德地图路线规划失败: {e}")
            return []
    
    async def _get_directions_http(
        self,
        origin: str,
        destination: str,
        mode: str
    ) -> List[Dict[str, Any]]:
        """使用 Streamable HTTP 方式获取路线规划"""
        try:
            # 构建 MCP 请求
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "transit_route" if mode == "transit" else "driving_route",
                "params": {
                    "origin": origin,
                    "destination": destination,
                    "city": "北京" if mode == "transit" else None,
                    "output": "json"
                }
            }
            
            # 移除 None 值
            mcp_request["params"] = {k: v for k, v in mcp_request["params"].items() if v is not None}
            
            # 发送请求
            response = await self.http_client.post(
                self.base_url,
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()

            # 关键日志：请求与返回的核心数据
            try:
                result_core = result.get("result", {}) if isinstance(result, dict) else {}
                route = (result_core or {}).get("route", {})
                paths = route.get("paths", []) or []
                if paths:
                    first = paths[0] or {}
                    logger.info(
                        f"[AMap Client {mode}] origin={mcp_request['params'].get('origin')} "
                        f"destination={mcp_request['params'].get('destination')} "
                        f"paths={len(paths)} distance={first.get('distance')} duration={first.get('duration')} "
                        f"steps={len(first.get('steps') or [])}"
                    )
                else:
                    logger.info(
                        f"[AMap Client {mode}] origin={mcp_request['params'].get('origin')} destination={mcp_request['params'].get('destination')} 无可用路径"
                    )
            except Exception as log_e:
                logger.warning(f"AMap客户端关键日志生成失败: {log_e}")
            
            # 解析响应
            if result.get("error"):
                logger.error(f"高德地图MCP错误: {result['error']}")
                return []
            
            return self._parse_directions_response(result.get("result", {}))
            
        except Exception as e:
            logger.error(f"高德地图HTTP MCP请求失败: {e}")
            return []
    
    async def _get_directions_sse(
        self,
        origin: str,
        destination: str,
        mode: str
    ) -> List[Dict[str, Any]]:
        """使用 SSE 方式获取路线规划"""
        try:
            # 构建 MCP 请求
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "route_planning",
                "params": {
                    "origin": origin,
                    "destination": destination,
                    "mode": mode,
                    "output": "json"
                }
            }
            
            # 发送 SSE 请求
            async with self.http_client.stream(
                "POST",
                self.base_url,
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                }
            ) as response:
                response.raise_for_status()
                
                result_data = {}
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # 移除 "data: " 前缀
                            if data.get("id") == 1:  # 匹配请求ID
                                result_data = data.get("result", {})
                                break
                        except json.JSONDecodeError:
                            continue
                
                return self._parse_directions_response(result_data)
                
        except Exception as e:
            logger.error(f"高德地图SSE MCP请求失败: {e}")
            return []
    
    def _parse_directions_response(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析高德地图路线规划响应"""
        try:
            routes = result.get("route", {}).get("paths", [])
            transportation = []
            
            for i, route in enumerate(routes[:3]):  # 取前3条路线
                # 解析路线信息
                distance = int(route.get("distance", 0))  # 米
                duration = int(route.get("duration", 0))  # 秒
                
                # 解析步骤信息
                steps = route.get("steps", [])
                route_info = []
                for step in steps:
                    step_info = {
                        "instruction": step.get("instruction", ""),
                        "distance": int(step.get("distance", 0)),
                        "duration": int(step.get("duration", 0)),
                        "road": step.get("road", "")
                    }
                    route_info.append(step_info)
                
                transport_item = {
                    "id": f"amap_route_{i+1}",
                    "type": "公共交通" if "transit" in str(route) else "自驾",
                    "name": f"高德路线{i+1}",
                    "description": f"高德地图推荐路线",
                    "duration": duration // 60,  # 转换为分钟
                    "distance": distance // 1000,  # 转换为公里
                    "price": self._estimate_cost(distance, duration),
                    "currency": "CNY",
                    "operating_hours": "06:00-23:00",
                    "frequency": "5-15分钟",
                    "coverage": ["目的地"],
                    "features": ["实时路况", "多方案选择"],
                    "route": route_info,
                    "source": "高德地图MCP"
                }
                transportation.append(transport_item)
            
            return transportation
            
        except Exception as e:
            logger.error(f"解析高德地图响应失败: {e}")
            return []
    
    def _estimate_cost(self, distance: int, duration: int) -> int:
        """估算费用"""
        # 根据距离和时长估算费用
        distance_km = distance // 1000
        duration_hours = duration // 3600
        
        # 基础费用计算
        if distance_km < 10:
            return 5  # 短距离
        elif distance_km < 50:
            return 15  # 中距离
        else:
            return 30  # 长距离
    
    async def search_places_around(
        self,
        location: str,
        keywords: str = "",
        types: str = "",
        radius: int = 5000,
        offset: int = 20,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """周边搜索地点"""
        try:
            if not self.api_key:
                logger.warning("高德地图API密钥未配置")
                return []
            
            # 构建 MCP 请求
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "place_around",
                "params": {
                    "location": location,
                    "keywords": keywords,
                    "types": types,
                    "radius": radius,
                    "offset": offset,
                    "page": page
                }
            }
            
            if self.mode == "sse":
                return await self._search_places_around_sse(mcp_request)
            else:
                return await self._search_places_around_http(mcp_request)
                
        except Exception as e:
            logger.error(f"高德地图周边搜索失败: {e}")
            return []
    
    async def _search_places_around_http(self, mcp_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """使用 HTTP 方式进行周边搜索"""
        try:
            response = await self.http_client.post(
                self.base_url,
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("error"):
                logger.error(f"高德地图周边搜索MCP错误: {result['error']}")
                return []
            
            return self._parse_places_response(result.get("result", {}))
            
        except Exception as e:
            logger.error(f"高德地图HTTP周边搜索失败: {e}")
            return []
    
    async def _search_places_around_sse(self, mcp_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """使用 SSE 方式进行周边搜索"""
        try:
            async with self.http_client.stream(
                "POST",
                self.base_url,
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                }
            ) as response:
                response.raise_for_status()
                
                result_data = {}
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("id") == 1:
                                result_data = data.get("result", {})
                                break
                        except json.JSONDecodeError:
                            continue
                
                return self._parse_places_response(result_data)
                
        except Exception as e:
            logger.error(f"高德地图SSE周边搜索失败: {e}")
            return []

    async def search_places(
        self,
        query: str,
        city: str,
        category: str = "景点"
    ) -> List[Dict[str, Any]]:
        """搜索地点"""
        try:
            if not self.api_key:
                logger.warning("高德地图API密钥未配置")
                return []
            
            # 构建 MCP 请求
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "place_search",
                "params": {
                    "keywords": query,
                    "city": city,
                    "types": self._get_place_type(category),
                    "output": "json"
                }
            }
            
            if self.mode == "sse":
                return await self._search_places_sse(mcp_request)
            else:
                return await self._search_places_http(mcp_request)
                
        except Exception as e:
            logger.error(f"高德地图地点搜索失败: {e}")
            return []
    
    async def _search_places_http(self, mcp_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """使用 HTTP 方式搜索地点"""
        try:
            response = await self.http_client.post(
                self.base_url,
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("error"):
                logger.error(f"高德地图MCP错误: {result['error']}")
                return []
            
            return self._parse_places_response(result.get("result", {}))
            
        except Exception as e:
            logger.error(f"高德地图HTTP地点搜索失败: {e}")
            return []
    
    async def _search_places_sse(self, mcp_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """使用 SSE 方式搜索地点"""
        try:
            async with self.http_client.stream(
                "POST",
                self.base_url,
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                }
            ) as response:
                response.raise_for_status()
                
                result_data = {}
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("id") == 1:
                                result_data = data.get("result", {})
                                break
                        except json.JSONDecodeError:
                            continue
                
                return self._parse_places_response(result_data)
                
        except Exception as e:
            logger.error(f"高德地图SSE地点搜索失败: {e}")
            return []
    
    def _parse_places_response(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析地点搜索响应"""
        try:
            pois = result.get("pois", [])
            places = []
            
            for poi in pois[:10]:  # 取前10个地点
                # 提取基本信息
                location_str = poi.get("location", "")
                coordinates = {}
                if location_str and "," in location_str:
                    try:
                        lng, lat = location_str.split(",")
                        coordinates = {
                            "lng": float(lng.strip()),
                            "lat": float(lat.strip())
                        }
                    except (ValueError, IndexError) as e:
                        logger.warning(f"坐标解析失败: {location_str}, 错误: {e}")
                        coordinates = {}
                
                # 提取商业扩展信息（评分、价格等）
                biz_ext = poi.get("biz_ext", {})
                rating = 0.0
                cost = ""
                if biz_ext:
                    # 安全地解析评分，处理可能的列表或其他类型
                    rating_value = biz_ext.get("rating", 0)
                    if isinstance(rating_value, (int, float)):
                        rating = float(rating_value)
                    elif isinstance(rating_value, str) and rating_value.replace(".", "").isdigit():
                        rating = float(rating_value)
                    elif isinstance(rating_value, list) and rating_value:
                        # 如果是列表，取第一个有效值
                        for item in rating_value:
                            if isinstance(item, (int, float)):
                                rating = float(item)
                                break
                            elif isinstance(item, str) and item.replace(".", "").isdigit():
                                rating = float(item)
                                break
                    
                    cost = biz_ext.get("cost", "")
                
                # 提取图片信息
                photos = []
                photo_list = poi.get("photos", [])
                if photo_list:
                    for photo in photo_list[:3]:  # 取前3张图片
                        if isinstance(photo, dict) and photo.get("url"):
                            photos.append({
                                "url": photo.get("url", ""),
                                "title": photo.get("title", "")
                            })
                
                # 提取标签
                tags = []
                tag_str = poi.get("tag", "")
                if tag_str:
                    tags = [tag.strip() for tag in tag_str.split(",") if tag.strip()]
                
                place_item = {
                    "id": f"amap_place_{poi.get('id', '')}",
                    "name": poi.get("name", ""),
                    "category": poi.get("type", ""),
                    "description": poi.get("address", ""),
                    "address": poi.get("address", ""),
                    "rating": rating,
                    "cost": cost,  # 人均消费
                    "price_range": self._get_price_range(cost),  # 价格区间
                    "coordinates": coordinates,
                    "location": location_str,
                    "phone": poi.get("tel", ""),
                    "business_area": poi.get("business_area", ""),
                    "cityname": poi.get("cityname", ""),
                    "adname": poi.get("adname", ""),  # 区域名称
                    "tags": tags,
                    "photos": photos,
                    "typecode": poi.get("typecode", ""),
                    "distance": poi.get("distance", ""),
                    "visit_duration": "1-2小时",
                    "website": "",
                    "accessibility": "良好",
                    "source": "高德地图MCP"
                }
                places.append(place_item)
            
            return places
            
        except Exception as e:
            logger.error(f"解析高德地图地点响应失败: {e}")
            return []
    
    def _get_price_range(self, cost: str) -> str:
        """根据人均消费获取价格区间"""
        if not cost:
            return "$$"
        
        try:
            # 提取数字部分
            import re
            cost_match = re.search(r'(\d+)', cost)
            if cost_match:
                cost_value = int(cost_match.group(1))
                if cost_value < 30:
                    return "$"
                elif cost_value < 80:
                    return "$$"
                elif cost_value < 150:
                    return "$$$"
                else:
                    return "$$$$"
        except:
            pass
        
        return "$$"
    
    def _get_place_type(self, category: str) -> str:
        """获取高德地图地点类型"""
        type_mapping = {
            "景点": "110000",  # 风景名胜
            "餐厅": "050000",  # 餐饮服务
            "酒店": "100000",  # 住宿服务
            "购物": "060000",  # 购物服务
            "交通": "150000",  # 交通设施服务
        }
        return type_mapping.get(category, "110000")
    
    async def get_weather(self, city: str, extensions: str = "all") -> Dict[str, Any]:
        """获取天气信息"""
        try:
            if not self.api_key:
                logger.warning("高德地图API密钥未配置")
                return {}
            
            # 构建 MCP 请求
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "weather_query",
                "params": {
                    "city": city,
                    "extensions": extensions
                }
            }
            
            if self.mode == "sse":
                return await self._get_weather_sse(mcp_request)
            else:
                return await self._get_weather_http(mcp_request)
                
        except Exception as e:
            logger.error(f"获取高德地图天气信息失败: {e}")
            return {}
    
    async def _get_weather_http(self, mcp_request: Dict[str, Any]) -> Dict[str, Any]:
        """使用 HTTP 方式获取天气信息"""
        try:
            response = await self.http_client.post(
                self.base_url,
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("error"):
                logger.error(f"高德地图天气MCP错误: {result['error']}")
                return {}
            
            return self._parse_weather_response(result.get("result", {}))
            
        except Exception as e:
            logger.error(f"高德地图HTTP天气查询失败: {e}")
            return {}
    
    async def _get_weather_sse(self, mcp_request: Dict[str, Any]) -> Dict[str, Any]:
        """使用 SSE 方式获取天气信息"""
        try:
            async with self.http_client.stream(
                "POST",
                self.base_url,
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                }
            ) as response:
                response.raise_for_status()
                
                result_data = {}
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("id") == 1:
                                result_data = data.get("result", {})
                                break
                        except json.JSONDecodeError:
                            continue
                
                return self._parse_weather_response(result_data)
                
        except Exception as e:
            logger.error(f"高德地图SSE天气查询失败: {e}")
            return {}
    
    def _parse_weather_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """解析天气响应"""
        try:
            weather_data = {
                "location": "",
                "forecast": [],
                "recommendations": []
            }
            
            # 解析实况天气
            lives = result.get("lives", [])
            if lives:
                live_weather = lives[0]
                weather_data["location"] = live_weather.get("city", "")
                weather_data["current"] = {
                    "weather": live_weather.get("weather", ""),
                    "temperature": live_weather.get("temperature", ""),
                    "humidity": live_weather.get("humidity", ""),
                    "wind_direction": live_weather.get("winddirection", ""),
                    "wind_power": live_weather.get("windpower", ""),
                    "report_time": live_weather.get("reporttime", "")
                }
            
            # 解析预报天气
            forecasts = result.get("forecasts", [])
            if forecasts:
                forecast_data = forecasts[0]
                weather_data["location"] = forecast_data.get("city", "")
                
                casts = forecast_data.get("casts", [])
                for cast in casts:
                    forecast_item = {
                        "date": cast.get("date", ""),
                        "week": cast.get("week", ""),
                        "dayweather": cast.get("dayweather", ""),
                        "nightweather": cast.get("nightweather", ""),
                        "daytemp": cast.get("daytemp", ""),
                        "nighttemp": cast.get("nighttemp", ""),
                        "daywind": cast.get("daywind", ""),
                        "nightwind": cast.get("nightwind", ""),
                        "daypower": cast.get("daypower", ""),
                        "nightpower": cast.get("nightpower", "")
                    }
                    weather_data["forecast"].append(forecast_item)
                
                # 生成天气建议
                if casts:
                    weather_data["recommendations"] = self._generate_weather_recommendations(casts)
            
            logger.info(f"解析高德地图天气数据成功: {weather_data['location']}")
            return weather_data
            
        except Exception as e:
            logger.error(f"解析高德地图天气响应失败: {e}")
            return {}
    
    def _generate_weather_recommendations(self, casts: List[Dict[str, Any]]) -> List[str]:
        """根据天气预报生成建议"""
        recommendations = []
        
        try:
            if not casts:
                return recommendations
            
            # 分析未来几天的天气
            for cast in casts[:3]:  # 分析前3天
                day_weather = cast.get("dayweather", "")
                day_temp = int(cast.get("daytemp", 0)) if cast.get("daytemp", "").isdigit() else 0
                night_temp = int(cast.get("nighttemp", 0)) if cast.get("nighttemp", "").isdigit() else 0
                
                # 温度建议
                if day_temp > 30:
                    recommendations.append("气温较高，建议穿着轻薄透气的衣物，注意防晒")
                elif day_temp < 10:
                    recommendations.append("气温较低，建议穿着保暖衣物")
                
                # 天气建议
                if "雨" in day_weather:
                    recommendations.append("有降雨，建议携带雨具")
                elif "雪" in day_weather:
                    recommendations.append("有降雪，注意保暖和路面湿滑")
                elif "晴" in day_weather:
                    recommendations.append("天气晴朗，适合户外活动")
            
            # 去重
            recommendations = list(set(recommendations))
            
        except Exception as e:
            logger.warning(f"生成天气建议失败: {e}")
        
        return recommendations
    
    async def geocode(self, address: str, city: str = "") -> Optional[Dict[str, Any]]:
        """地理编码 - 地址转坐标"""
        try:
            if not self.api_key:
                logger.warning("高德地图API密钥未配置")
                return None
            
            # 构建 MCP 请求
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "geocode",
                "params": {
                    "address": address,
                    "city": city
                }
            }
            
            if self.mode == "sse":
                return await self._geocode_sse(mcp_request)
            else:
                return await self._geocode_http(mcp_request)
                
        except Exception as e:
            logger.error(f"高德地图地理编码失败: {e}")
            return None
    
    async def _geocode_http(self, mcp_request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """使用 HTTP 方式进行地理编码"""
        try:
            response = await self.http_client.post(
                self.base_url,
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("error"):
                logger.error(f"高德地图地理编码MCP错误: {result['error']}")
                return None
            
            return self._parse_geocode_response(result.get("result", {}))
            
        except Exception as e:
            logger.error(f"高德地图HTTP地理编码失败: {e}")
            return None
    
    async def _geocode_sse(self, mcp_request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """使用 SSE 方式进行地理编码"""
        try:
            async with self.http_client.stream(
                "POST",
                self.base_url,
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                }
            ) as response:
                response.raise_for_status()
                
                result_data = {}
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("id") == 1:
                                result_data = data.get("result", {})
                                break
                        except json.JSONDecodeError:
                            continue
                
                return self._parse_geocode_response(result_data)
                
        except Exception as e:
            logger.error(f"高德地图SSE地理编码失败: {e}")
            return None
    
    def _parse_geocode_response(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析地理编码响应"""
        try:
            if not result:
                return None
            
            # 解析高德地图地理编码响应
            geocodes = result.get("geocodes", [])
            if not geocodes:
                logger.warning("地理编码未返回结果")
                return None
            
            # 取第一个结果
            geocode = geocodes[0]
            location = geocode.get("location", "")
            
            if not location:
                logger.warning("地理编码未返回坐标信息")
                return None
            
            # 解析坐标
            try:
                lng, lat = location.split(",")
                return {
                    "lng": float(lng),
                    "lat": float(lat),
                    "formatted_address": geocode.get("formatted_address", ""),
                    "level": geocode.get("level", ""),
                    "country": geocode.get("country", ""),
                    "province": geocode.get("province", ""),
                    "city": geocode.get("city", ""),
                    "district": geocode.get("district", ""),
                    "adcode": geocode.get("adcode", "")
                }
            except (ValueError, IndexError) as e:
                logger.error(f"解析坐标失败: {location}, 错误: {e}")
                return None
                
        except Exception as e:
            logger.error(f"解析地理编码响应失败: {e}")
            return None
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()
