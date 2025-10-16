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
                place_item = {
                    "id": f"amap_place_{poi.get('id', '')}",
                    "name": poi.get("name", ""),
                    "category": poi.get("type", ""),
                    "description": poi.get("address", ""),
                    "address": poi.get("address", ""),
                    "rating": float(poi.get("rating", 0)),
                    "price": 0,  # 高德地图不提供价格信息
                    "opening_hours": poi.get("tel", ""),
                    "visit_duration": "1-2小时",
                    "tags": poi.get("tag", "").split(";") if poi.get("tag") else [],
                    "phone": poi.get("tel", ""),
                    "website": "",
                    "accessibility": "良好",
                    "source": "高德地图MCP"
                }
                places.append(place_item)
            
            return places
            
        except Exception as e:
            logger.error(f"解析高德地图地点响应失败: {e}")
            return []
    
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
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()
