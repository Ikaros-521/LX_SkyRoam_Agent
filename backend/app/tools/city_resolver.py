"""
城市名解析工具
使用geopy和高德地图API进行智能城市名解析
"""

import asyncio
import httpx
from typing import Optional, Dict, Any
from loguru import logger
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from app.core.config import settings


class CityResolver:
    """城市名解析器"""
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="LX-SkyRoam-Agent/1.0")
        self.http_client = httpx.AsyncClient(timeout=10.0)
        self.api_key = settings.AMAP_API_KEY
        
        # 常见地名映射（作为备用）
        self.city_mapping = {
            "千岛湖": "杭州",
            "西湖": "杭州", 
            "西溪湿地": "杭州",
            "天安门": "北京",
            "故宫": "北京",
            "长城": "北京",
            "外滩": "上海",
            "东方明珠": "上海",
            "小蛮腰": "广州",
            "珠江": "广州",
            "大雁塔": "西安",
            "兵马俑": "西安",
            "夫子庙": "南京",
            "中山陵": "南京",
            "拙政园": "苏州",
            "虎丘": "苏州",
            "鼓浪屿": "厦门",
            "南普陀": "厦门",
            "黄鹤楼": "武汉",
            "东湖": "武汉",
            "橘子洲": "长沙",
            "岳麓山": "长沙",
            "趵突泉": "济南",
            "大明湖": "济南",
            "五大道": "天津",
            "海河": "天津",
            "天坛": "北京",
            "颐和园": "北京",
            "圆明园": "北京",
            "什刹海": "北京",
            "王府井": "北京",
            "三里屯": "北京",
            "陆家嘴": "上海",
            "南京路": "上海",
            "豫园": "上海",
            "田子坊": "上海",
            "新天地": "上海",
            "珠江新城": "广州",
            "天河城": "广州",
            "上下九": "广州",
            "北京路": "广州",
            "春熙路": "成都",
            "宽窄巷子": "成都",
            "锦里": "成都",
            "大熊猫基地": "成都",
            "解放碑": "重庆",
            "洪崖洞": "重庆",
            "朝天门": "重庆",
            "磁器口": "重庆",
            "钟楼": "西安",
            "回民街": "西安",
            "华清宫": "西安",
            "芙蓉园": "西安",
            "总统府": "南京",
            "雨花台": "南京",
            "玄武湖": "南京",
            "鸡鸣寺": "南京",
            "留园": "苏州",
            "狮子林": "苏州",
            "寒山寺": "苏州",
            "周庄": "苏州",
            "曾厝垵": "厦门",
            "环岛路": "厦门",
            "厦门大学": "厦门",
            "南普陀寺": "厦门",
            "户部巷": "武汉",
            "江汉路": "武汉",
            "武汉大学": "武汉",
            "黄鹤楼公园": "武汉",
            "坡子街": "长沙",
            "太平街": "长沙",
            "湖南大学": "长沙",
            "岳麓书院": "长沙",
            "泉城广场": "济南",
            "千佛山": "济南",
            "黑虎泉": "济南",
            "芙蓉街": "济南",
            "古文化街": "天津",
            "天津之眼": "天津",
            "意式风情街": "天津",
            "瓷房子": "天津"
        }
    
    async def resolve_city(self, destination: str) -> str:
        """
        解析城市名
        优先级：高德地图API > OpenStreetMap > 本地映射
        """
        try:
            # 1. 尝试使用高德地图API进行地理编码
            city_name = await self._resolve_with_amap(destination)
            if city_name:
                logger.info(f"高德地图API解析: {destination} -> {city_name}")
                return city_name
            
            # 2. 尝试使用OpenStreetMap
            city_name = await self._resolve_with_osm(destination)
            if city_name:
                logger.info(f"OpenStreetMap解析: {destination} -> {city_name}")
                return city_name
            
            # 3. 使用本地映射
            city_name = self._resolve_with_mapping(destination)
            if city_name:
                logger.info(f"本地映射解析: {destination} -> {city_name}")
                return city_name
            
            # 4. 默认返回原目的地
            logger.warning(f"无法解析城市名: {destination}")
            return destination
            
        except Exception as e:
            logger.error(f"城市名解析失败: {e}")
            return destination
    
    async def _resolve_with_amap(self, destination: str) -> Optional[str]:
        """使用高德地图API解析城市名"""
        try:
            if not self.api_key:
                return None
            
            url = "https://restapi.amap.com/v3/geocode/geo"
            params = {
                "key": self.api_key,
                "address": destination,
                "output": "json"
            }
            
            response = await self.http_client.get(url, params=params)
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "1" and result.get("geocodes"):
                    geocode = result["geocodes"][0]
                    # 提取城市名（通常是省市区中的市）
                    address_components = geocode.get("formatted_address", "").split()
                    if len(address_components) >= 2:
                        # 通常格式：省 市 区/县
                        city = address_components[1]
                        return city
            return None
            
        except Exception as e:
            logger.debug(f"高德地图API解析失败: {e}")
            return None
    
    async def _resolve_with_osm(self, destination: str) -> Optional[str]:
        """使用OpenStreetMap解析城市名"""
        try:
            # 使用geopy的Nominatim服务
            location = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.geolocator.geocode(f"{destination}, China", timeout=5)
            )
            
            if location:
                # 解析地址组件
                address = location.raw.get("display_name", "")
                # 尝试提取城市名
                parts = address.split(", ")
                for part in parts:
                    if any(keyword in part for keyword in ["市", "区", "县"]):
                        # 移除"市"、"区"、"县"后缀
                        city = part.replace("市", "").replace("区", "").replace("县", "")
                        if len(city) >= 2:  # 至少2个字符
                            return city
            return None
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.debug(f"OpenStreetMap解析失败: {e}")
            return None
        except Exception as e:
            logger.debug(f"OpenStreetMap解析异常: {e}")
            return None
    
    def _resolve_with_mapping(self, destination: str) -> Optional[str]:
        """使用本地映射解析城市名"""
        # 直接匹配
        if destination in self.city_mapping:
            return self.city_mapping[destination]
        
        # 包含匹配
        for key, value in self.city_mapping.items():
            if key in destination:
                return value
        
        return None
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()
