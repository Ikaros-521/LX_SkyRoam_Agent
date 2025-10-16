#!/usr/bin/env python3
"""
百度地图集成模块
提取自mcp_server_baidu_maps，去除MCP依赖
"""

import os
import copy
import httpx
import re
from typing import Dict, Any, List, Optional
from app.core.config import settings

# 获取API密钥
api_key = os.getenv('BAIDU_MAPS_API_KEY', settings.BAIDU_MAPS_API_KEY)
api_url = "https://api.map.baidu.com"

def mask_api_key(text: str) -> str:
    """
    信息脱敏函数，主要用于给某个字符串脱敏用户的ak
    """
    if not text or not api_key:
        return text
    
    if api_key not in text:
        return text
    
    if len(api_key) <= 8:
        masked_key = api_key[:2] + '*' * (len(api_key) - 4) + api_key[-2:]
    else:
        masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
    
    return text.replace(api_key, masked_key)

def is_latlng(text: str) -> bool:
    """
    判断输入是否为经纬度坐标
    """
    pattern = r'^\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*$'
    match = re.match(pattern, text)
    if not match:
        return False
    lat, lng = float(match.group(1)), float(match.group(2))
    return -90 <= lat <= 90 and -180 <= lng <= 180

async def map_directions(
    origin: str,
    destination: str,
    model: str = "transit",
    is_china: str = "true",
    coord_type: str = "bd09ll",
    ret_coordtype: str = "bd09ll",
    steps_info: int = 1
) -> Dict[str, Any]:
    """
    路线规划服务
    """
    try:
        # 检查输入是否为地址文本
        if not is_latlng(origin):
            # 地理编码获取起点坐标
            geocode_url = f"{api_url}/geocoding/v3/" if is_china == "true" else f"{api_url}/api_geocoding_abroad/v1/"
            geocode_params = {
                "ak": api_key,
                "output": "json",
                "address": origin,
                "from": "lx_skyroam"
            }
            
            async with httpx.AsyncClient(timeout=30.0, proxies={}) as client:
                geocode_response = await client.get(geocode_url, params=geocode_params)
                geocode_response.raise_for_status()
                geocode_result = geocode_response.json()
                
                if geocode_result.get("status") != 0:
                    error_msg = geocode_result.get("message", "起点地址无效")
                    raise Exception(f"地理编码错误: {mask_api_key(error_msg)}")
                
                location = geocode_result.get("result", {}).get("location", {})
                origin = f"{location.get('lat')},{location.get('lng')}"
        
        if not is_latlng(destination):
            # 地理编码获取终点坐标
            geocode_url = f"{api_url}/geocoding/v3/" if is_china == "true" else f"{api_url}/api_geocoding_abroad/v1/"
            geocode_params = {
                "ak": api_key,
                "output": "json",
                "address": destination,
                "from": "lx_skyroam"
            }
            
            async with httpx.AsyncClient(timeout=30.0, proxies={}) as client:
                geocode_response = await client.get(geocode_url, params=geocode_params)
                geocode_response.raise_for_status()
                geocode_result = geocode_response.json()
                
                if geocode_result.get("status") != 0:
                    error_msg = geocode_result.get("message", "终点地址无效")
                    raise Exception(f"地理编码错误: {mask_api_key(error_msg)}")
                
                location = geocode_result.get("result", {}).get("location", {})
                destination = f"{location.get('lat')},{location.get('lng')}"
        
        # 路线规划 - 根据文档使用正确的API端点
        if model == "transit":
            # 公交路线规划使用专门的transit端点
            url = f"{api_url}/directionlite/v1/transit"
            params = {
                "ak": api_key,
                "output": "json",
                "origin": origin,
                "destination": destination,
                "coord_type": coord_type,
                "ret_coordtype": ret_coordtype,
                "steps_info": steps_info,
                "from": "lx_skyroam"
            }
        else:
            # 其他路线规划使用通用端点
            url = f"{api_url}/directionlite/v1/{model}" if is_china == "true" else f"{api_url}/direction_abroad/v1/{model}"
            params = {
                "ak": api_key,
                "output": "json",
                "origin": origin,
                "destination": destination,
                "coord_type": coord_type,
                "ret_coordtype": ret_coordtype,
                "from": "lx_skyroam"
            }
        
        async with httpx.AsyncClient(timeout=30.0, verify=False, proxies={}) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") != 0:
                error_msg = result.get("message", "未知错误")
                status = result.get("status")
                
                # 处理特定的错误情况
                if status == 1001:
                    raise Exception("没有公交方案")
                elif status == 1002:
                    raise Exception("不支持跨域公交路线规划")
                elif status == 1003:
                    raise Exception("路径规划失败，起终点附近可能没有车站")
                else:
                    raise Exception(f"路线规划错误: {mask_api_key(error_msg)}")
            
            return result
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP请求失败: {str(e)}"
        print(f"百度地图API请求失败: {error_msg}")
        if 'url' in locals():
            print(f"请求URL: {url}")
        if 'params' in locals():
            print(f"请求参数: {mask_api_key(str(params))}")
        # 确保错误信息完整
        if str(e):
            raise Exception(error_msg) from e
        else:
            # 如果错误描述为空，提供更具体的错误信息
            conn_error_msg = f"HTTP请求失败: 连接错误，可能是网络问题或API地址无效。请检查网络连接和API配置。"
            print(f"详细错误: {conn_error_msg}")
            raise Exception(conn_error_msg) from e
    except Exception as e:
        error_msg = f"路线规划异常: {str(e)}"
        print(f"百度地图路线规划异常: {error_msg}")
        raise Exception(error_msg) from e

async def map_search_places(
    query: str,
    region: str = "全国",
    tag: str = "",
    location: str = "",
    radius: str = "",
    is_china: str = "true"
) -> Dict[str, Any]:
    """
    地点搜索服务
    """
    try:
        params = {
            "ak": api_key,
            "output": "json",
            "query": query,
            "type": tag,
            "region_limit": "true",
            "scope": 2,
            "from": "lx_skyroam"
        }
        
        if is_china == "true":
            if location:
                url = f"{api_url}/place/v3/around"
                params["location"] = location
                params["radius"] = radius
            else:
                url = f"{api_url}/place/v3/region"
                params["region"] = region
        else:
            url = f"{api_url}/place_abroad/v1/search"
            if location:
                params["location"] = location
                params["radius"] = radius
            else:
                params["region"] = region
        
        async with httpx.AsyncClient(timeout=30.0, verify=False, proxies={}) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") != 0:
                error_msg = result.get("message", "未知错误")
                raise Exception(f"地点搜索错误: {mask_api_key(error_msg)}")
            
            return result
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP请求失败: {str(e)}"
        print(f"百度地图API请求失败: {error_msg}")
        if 'url' in locals():
            print(f"请求URL: {url}")
        if 'params' in locals():
            print(f"请求参数: {mask_api_key(str(params))}")
        # 确保错误信息完整
        if str(e):
            raise Exception(error_msg) from e
        else:
            # 如果错误描述为空，提供更具体的错误信息
            conn_error_msg = f"HTTP请求失败: 连接错误，可能是网络问题或API地址无效。请检查网络连接和API配置。"
            print(f"详细错误: {conn_error_msg}")
            raise Exception(conn_error_msg) from e
    except Exception as e:
        error_msg = f"地点搜索异常: {str(e)}"
        print(f"百度地图地点搜索异常: {error_msg}")
        raise Exception(error_msg) from e

async def map_geocode(address: str, is_china: str = "true") -> Dict[str, Any]:
    """
    地理编码服务
    """
    try:
        url = f"{api_url}/geocoding/v3/" if is_china == "true" else f"{api_url}/api_geocoding_abroad/v1/"
        params = {
            "ak": api_key,
            "output": "json",
            "address": address,
            "from": "lx_skyroam"
        }
        
        async with httpx.AsyncClient(timeout=30.0, verify=False, proxies={}) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") != 0:
                error_msg = result.get("message", "未知错误")
                raise Exception(f"地理编码错误: {mask_api_key(error_msg)}")
            
            return result
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP请求失败: {str(e)}"
        print(f"百度地图API请求失败: {error_msg}")
        if 'url' in locals():
            print(f"请求URL: {url}")
        if 'params' in locals():
            print(f"请求参数: {mask_api_key(str(params))}")
        # 确保错误信息完整
        if str(e):
            raise Exception(error_msg) from e
        else:
            # 如果错误描述为空，提供更具体的错误信息
            conn_error_msg = f"HTTP请求失败: 连接错误，可能是网络问题或API地址无效。请检查网络连接和API配置。"
            print(f"详细错误: {conn_error_msg}")
            raise Exception(conn_error_msg) from e
    except Exception as e:
        error_msg = f"地理编码异常: {str(e)}"
        print(f"百度地图地理编码异常: {error_msg}")
        raise Exception(error_msg) from e

async def map_reverse_geocode(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    逆地理编码服务
    """
    try:
        url = f"{api_url}/reverse_geocoding/v3/"
        params = {
            "ak": api_key,
            "output": "json",
            "location": f"{latitude},{longitude}",
            "extensions_road": "true",
            "extensions_poi": "1",
            "entire_poi": "1",
            "from": "lx_skyroam"
        }
        
        async with httpx.AsyncClient(timeout=30.0, verify=False, proxies={}) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") != 0:
                error_msg = result.get("message", "未知错误")
                raise Exception(f"逆地理编码错误: {mask_api_key(error_msg)}")
            
            return result
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP请求失败: {str(e)}"
        print(f"百度地图API请求失败: {error_msg}")
        if 'url' in locals():
            print(f"请求URL: {url}")
        if 'params' in locals():
            print(f"请求参数: {mask_api_key(str(params))}")
        # 确保错误信息完整
        if str(e):
            raise Exception(error_msg) from e
        else:
            # 如果错误描述为空，提供更具体的错误信息
            conn_error_msg = f"HTTP请求失败: 连接错误，可能是网络问题或API地址无效。请检查网络连接和API配置。"
            print(f"详细错误: {conn_error_msg}")
            raise Exception(conn_error_msg) from e
    except Exception as e:
        error_msg = f"逆地理编码异常: {str(e)}"
        print(f"百度地图逆地理编码异常: {error_msg}")
        raise Exception(error_msg) from e

async def map_weather(location: str = "", district_id: str = "", is_china: str = "true") -> Dict[str, Any]:
    """
    天气查询服务
    """
    try:
        url = f"{api_url}/weather/v1/?" if is_china == "true" else f"{api_url}/weather_abroad/v1/?"
        params = {
            "ak": api_key,
            "data_type": "all",
            "from": "lx_skyroam"
        }
        
        if not location:
            params["district_id"] = district_id
        else:
            params["location"] = location
        
        async with httpx.AsyncClient(timeout=30.0, verify=False, proxies={}) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") != 0:
                error_msg = result.get("message", "未知错误")
                raise Exception(f"天气查询错误: {mask_api_key(error_msg)}")
            
            return result
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP请求失败: {str(e)}"
        print(f"百度地图API请求失败: {error_msg}")
        if 'url' in locals():
            print(f"请求URL: {url}")
        if 'params' in locals():
            print(f"请求参数: {mask_api_key(str(params))}")
        # 确保错误信息完整
        if str(e):
            raise Exception(error_msg) from e
        else:
            # 如果错误描述为空，提供更具体的错误信息
            conn_error_msg = f"HTTP请求失败: 连接错误，可能是网络问题或API地址无效。请检查网络连接和API配置。"
            print(f"详细错误: {conn_error_msg}")
            raise Exception(conn_error_msg) from e
    except Exception as e:
        error_msg = f"天气查询异常: {str(e)}"
        print(f"百度地图天气查询异常: {error_msg}")
        raise Exception(error_msg) from e

# 工具函数映射
TOOL_FUNCTIONS = {
    "map_directions": map_directions,
    "map_search_places": map_search_places,
    "map_geocode": map_geocode,
    "map_reverse_geocode": map_reverse_geocode,
    "map_weather": map_weather,
    "route_planning": map_directions  # 路线规划使用map_directions
}

async def call_baidu_maps_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用百度地图工具
    """
    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError(f"未知工具: {tool_name}")
    
    func = TOOL_FUNCTIONS[tool_name]
    return await func(**arguments)
