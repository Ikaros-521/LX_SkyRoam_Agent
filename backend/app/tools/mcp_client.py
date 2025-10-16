"""
MCP (Model Control Protocol) 客户端
用于调用各种第三方API和工具
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from loguru import logger
import httpx
import json

from app.core.config import settings


class MCPClient:
    """MCP客户端"""
    
    def __init__(self):
        # 配置HTTP客户端，增加超时时间和重试机制
        timeout = httpx.Timeout(60.0, connect=30.0)
        self.http_client = httpx.AsyncClient(
            timeout=timeout,
            verify=False,  # 暂时禁用SSL验证
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            proxies={}  # 禁用代理
        )
        self.base_url = "https://api.example.com"  # 示例API地址
        self._amadeus_token = None
        self._token_expires_at = None
    
    async def get_flights(
        self, 
        destination: str, 
        departure_date: date, 
        return_date: date,
        origin: str = "北京"
    ) -> List[Dict[str, Any]]:
        """获取航班信息"""
        try:
            # 检查Amadeus API配置
            if not settings.AMADEUS_CLIENT_ID or not settings.AMADEUS_CLIENT_SECRET:
                logger.warning("Amadeus API凭据未配置，返回空列表")
                return []
            
            # 获取访问令牌
            token = await self._get_amadeus_token()
            if not token:
                logger.error("无法获取Amadeus API访问令牌")
                return []
            
            # 调用Amadeus API
            flights = await self._get_amadeus_flights(origin, destination, departure_date, return_date, token)
            
            if not flights:
                logger.warning("Amadeus API未返回数据，返回空列表")
                return []
            
            logger.info(f"从Amadeus API获取到 {len(flights)} 条航班数据")
            return flights
            
        except Exception as e:
            logger.error(f"获取航班数据失败: {e}")
            return []
    
    async def _get_amadeus_token(self) -> Optional[str]:
        """获取Amadeus API访问令牌"""
        try:
            # 检查现有令牌是否有效
            if self._amadeus_token and self._token_expires_at:
                if datetime.now().timestamp() < self._token_expires_at:
                    logger.info("使用现有的有效令牌")
                    return self._amadeus_token
            
            logger.info("开始获取新的Amadeus API令牌...")
            
            # 获取新令牌
            data = {
                "grant_type": "client_credentials",
                "client_id": settings.AMADEUS_CLIENT_ID,
                "client_secret": settings.AMADEUS_CLIENT_SECRET
            }

            logger.warning(f"AMADEUS ID: {settings.AMADEUS_CLIENT_ID}， 密码: {settings.AMADEUS_CLIENT_SECRET}")
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            logger.info(f"请求URL: {settings.AMADEUS_TOKEN_URL}")
            logger.info(f"请求数据: grant_type={data['grant_type']}, client_id={data['client_id'][:10]}...")
            
            response = await self.http_client.post(
                settings.AMADEUS_TOKEN_URL,
                data=data,
                headers=headers
            )
            
            logger.info(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self._amadeus_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)  # 默认1小时
                self._token_expires_at = datetime.now().timestamp() + expires_in - 60  # 提前1分钟过期
                
                logger.info("成功获取Amadeus API访问令牌")
                return self._amadeus_token
            else:
                logger.error(f"获取Amadeus API令牌失败: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return None
                
        except httpx.TimeoutException as e:
            logger.error(f"获取Amadeus API令牌超时: {e}")
            return None
        except httpx.ConnectError as e:
            logger.error(f"连接Amadeus API失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取Amadeus API令牌异常: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None
    
    async def _get_amadeus_flights(
        self, 
        origin: str, 
        destination: str, 
        departure_date: date, 
        return_date: date,
        token: str
    ) -> List[Dict[str, Any]]:
        """调用Amadeus API获取航班数据"""
        try:
            # Amadeus API端点
            url = f"{settings.AMADEUS_API_BASE}/v2/shopping/flight-offers"
            
            # 获取城市代码
            origin_code = self._get_city_code(origin)
            destination_code = self._get_city_code(destination)
            
            if not origin_code or not destination_code:
                logger.error(f"无法获取城市代码: {origin} -> {destination}")
                return []
            
            params = {
                "originLocationCode": origin_code,
                "destinationLocationCode": destination_code,
                "departureDate": departure_date.strftime("%Y-%m-%d"),
                "adults": 1,
                "max": 10,
                "currencyCode": "CNY"
            }
            
            # 如果是往返票，添加返回日期
            if return_date and return_date > departure_date:
                params["returnDate"] = return_date.strftime("%Y-%m-%d")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"调用Amadeus API: {origin_code} -> {destination_code}, 出发: {departure_date}")
            
            response = await self.http_client.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                flights = self._parse_amadeus_flights(data)
                logger.info(f"成功解析 {len(flights)} 条航班数据")
                return flights
            elif response.status_code == 400:
                logger.warning(f"Amadeus API请求参数错误: {response.text}")
                return []
            elif response.status_code == 401:
                logger.error("Amadeus API认证失败，令牌可能已过期")
                self._amadeus_token = None  # 清除无效令牌
                return []
            else:
                logger.error(f"Amadeus API错误: {response.status_code} - {response.text}")
                return []
                    
        except Exception as e:
            logger.error(f"Amadeus API调用失败: {e}")
            return []
    
    def _parse_amadeus_flights(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析Amadeus API返回的航班数据"""
        flights = []
        
        try:
            offers = data.get("data", [])
            if not offers:
                logger.warning("Amadeus API返回的数据为空")
                return []
            
            for offer_idx, offer in enumerate(offers):
                price_info = offer.get("price", {})
                total_price = float(price_info.get("total", 0))
                currency = price_info.get("currency", "EUR")
                
                # 处理每个行程（往返票可能有多个行程）
                for itinerary_idx, itinerary in enumerate(offer.get("itineraries", [])):
                    segments = itinerary.get("segments", [])
                    if not segments:
                        continue
                    
                    # 计算总飞行时间
                    total_duration = itinerary.get("duration", "PT0H0M")
                    
                    # 计算中转次数
                    stops = max(0, len(segments) - 1)
                    
                    # 主要航段信息（第一段）
                    first_segment = segments[0]
                    last_segment = segments[-1]
                    
                    # 航空公司信息
                    carrier_code = first_segment.get("carrierCode", "")
                    flight_number = f"{carrier_code}{first_segment.get('number', '')}"
                    
                    # 时间信息
                    departure_info = first_segment.get("departure", {})
                    arrival_info = last_segment.get("arrival", {})
                    
                    departure_time = departure_info.get("at", "")
                    arrival_time = arrival_info.get("at", "")
                    
                    # 机场信息
                    origin_airport = departure_info.get("iataCode", "")
                    destination_airport = arrival_info.get("iataCode", "")
                    
                    # 构建航班信息
                    flight = {
                        "id": f"amadeus_{offer_idx}_{itinerary_idx}",
                        "airline": carrier_code,
                        "airline_name": self._get_airline_name(carrier_code),
                        "flight_number": flight_number,
                        "departure_time": departure_time,
                        "arrival_time": arrival_time,
                        "duration": self._format_duration(total_duration),
                        "price": total_price,
                        "currency": currency,
                        "price_cny": self._convert_to_cny(total_price, currency),
                        "aircraft": first_segment.get("aircraft", {}).get("code", ""),
                        "stops": stops,
                        "origin": origin_airport,
                        "destination": destination_airport,
                        "date": departure_time.split("T")[0] if "T" in departure_time else departure_time,
                        "rating": 4.2,  # 默认评分
                        "cabin_class": self._get_cabin_class(offer),
                        "baggage_allowance": self._get_baggage_info(offer),
                        "segments": self._parse_segments(segments),
                        "booking_class": offer.get("travelerPricings", [{}])[0].get("fareDetailsBySegment", [{}])[0].get("class", ""),
                        "refundable": self._is_refundable(offer),
                        "source": "amadeus"
                    }
                    
                    flights.append(flight)
                        
            logger.info(f"成功解析 {len(flights)} 条航班数据")
            return flights
            
        except Exception as e:
            logger.error(f"解析Amadeus航班数据失败: {e}")
            return []
    
    def _get_airline_name(self, carrier_code: str) -> str:
        """获取航空公司名称"""
        airline_names = {
            "CA": "中国国际航空",
            "MU": "中国东方航空", 
            "CZ": "中国南方航空",
            "HU": "海南航空",
            "3U": "四川航空",
            "9C": "春秋航空",
            "JD": "首都航空",
            "G5": "华夏航空",
            "8L": "祥鹏航空",
            "EU": "成都航空",
            "AA": "美国航空",
            "UA": "美国联合航空",
            "DL": "达美航空",
            "BA": "英国航空",
            "LH": "汉莎航空",
            "AF": "法国航空",
            "KL": "荷兰皇家航空",
            "EK": "阿联酋航空",
            "QR": "卡塔尔航空",
            "SQ": "新加坡航空",
            "TG": "泰国国际航空",
            "NH": "全日空",
            "JL": "日本航空",
            "KE": "大韩航空",
            "OZ": "韩亚航空"
        }
        return airline_names.get(carrier_code, carrier_code)
    
    def _format_duration(self, duration: str) -> str:
        """格式化飞行时间"""
        try:
            # 解析ISO 8601格式的时间 (PT2H30M)
            if duration.startswith("PT"):
                duration = duration[2:]  # 移除PT前缀
                hours = 0
                minutes = 0
                
                if "H" in duration:
                    parts = duration.split("H")
                    hours = int(parts[0])
                    duration = parts[1] if len(parts) > 1 else ""
                
                if "M" in duration:
                    minutes = int(duration.replace("M", ""))
                
                if hours > 0 and minutes > 0:
                    return f"{hours}小时{minutes}分钟"
                elif hours > 0:
                    return f"{hours}小时"
                elif minutes > 0:
                    return f"{minutes}分钟"
                else:
                    return "未知"
            else:
                return duration
        except:
            return duration
    
    def _convert_to_cny(self, price: float, currency: str) -> float:
        """转换价格为人民币（简化版本）"""
        # 简化的汇率转换，实际应用中应该使用实时汇率API
        exchange_rates = {
            "CNY": 1.0,
            "USD": 7.2,
            "EUR": 7.8,
            "GBP": 9.1,
            "JPY": 0.048,
            "KRW": 0.0055,
            "SGD": 5.3,
            "HKD": 0.92,
            "AUD": 4.8,
            "CAD": 5.3
        }
        rate = exchange_rates.get(currency, 1.0)
        return round(price * rate, 2)
    
    def _get_cabin_class(self, offer: Dict[str, Any]) -> str:
        """获取舱位等级"""
        try:
            traveler_pricings = offer.get("travelerPricings", [])
            if traveler_pricings:
                fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
                if fare_details:
                    cabin = fare_details[0].get("cabin", "ECONOMY")
                    cabin_map = {
                        "ECONOMY": "经济舱",
                        "PREMIUM_ECONOMY": "超级经济舱", 
                        "BUSINESS": "商务舱",
                        "FIRST": "头等舱"
                    }
                    return cabin_map.get(cabin, "经济舱")
        except:
            pass
        return "经济舱"
    
    def _get_baggage_info(self, offer: Dict[str, Any]) -> str:
        """获取行李额度信息"""
        try:
            traveler_pricings = offer.get("travelerPricings", [])
            if traveler_pricings:
                fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
                if fare_details:
                    included_bags = fare_details[0].get("includedCheckedBags", {})
                    if included_bags:
                        quantity = included_bags.get("quantity", 0)
                        weight = included_bags.get("weight", 0)
                        weight_unit = included_bags.get("weightUnit", "KG")
                        
                        if quantity > 0:
                            if weight > 0:
                                return f"{quantity}件，每件{weight}{weight_unit}"
                            else:
                                return f"{quantity}件"
                        elif weight > 0:
                            return f"{weight}{weight_unit}"
        except:
            pass
        return "请咨询航空公司"
    
    def _parse_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析航段信息"""
        parsed_segments = []
        for segment in segments:
            parsed_segment = {
                "carrier_code": segment.get("carrierCode", ""),
                "flight_number": segment.get("number", ""),
                "aircraft": segment.get("aircraft", {}).get("code", ""),
                "departure": {
                    "airport": segment.get("departure", {}).get("iataCode", ""),
                    "terminal": segment.get("departure", {}).get("terminal", ""),
                    "time": segment.get("departure", {}).get("at", "")
                },
                "arrival": {
                    "airport": segment.get("arrival", {}).get("iataCode", ""),
                    "terminal": segment.get("arrival", {}).get("terminal", ""),
                    "time": segment.get("arrival", {}).get("at", "")
                },
                "duration": self._format_duration(segment.get("duration", ""))
            }
            parsed_segments.append(parsed_segment)
        return parsed_segments
    
    def _is_refundable(self, offer: Dict[str, Any]) -> bool:
        """判断是否可退款"""
        try:
            traveler_pricings = offer.get("travelerPricings", [])
            if traveler_pricings:
                fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
                if fare_details:
                    fare_basis = fare_details[0].get("fareBasis", "")
                    # 简化判断逻辑，实际应该根据fare rules判断
                    return "REFUNDABLE" in fare_basis.upper()
        except:
            pass
        return False
    
    def _get_city_code(self, city: str) -> Optional[str]:
        """获取城市代码"""
        city_codes = {
            # 中国大陆主要城市
            "北京": "PEK",
            "上海": "PVG", 
            "广州": "CAN",
            "深圳": "SZX",
            "成都": "CTU",
            "杭州": "HGH",
            "南京": "NKG",
            "武汉": "WUH",
            "西安": "XIY",
            "重庆": "CKG",
            "厦门": "XMN",
            "青岛": "TAO",
            "大连": "DLC",
            "昆明": "KMG",
            "长沙": "CSX",
            "沈阳": "SHE",
            "哈尔滨": "HRB",
            "长春": "CGQ",
            "石家庄": "SJW",
            "太原": "TYN",
            "呼和浩特": "HET",
            "兰州": "LHW",
            "西宁": "XNN",
            "银川": "INC",
            "乌鲁木齐": "URC",
            "拉萨": "LXA",
            "天津": "TSN",
            "济南": "TNA",
            "郑州": "CGO",
            "合肥": "HFE",
            "南昌": "KHN",
            "福州": "FOC",
            "海口": "HAK",
            "三亚": "SYX",
            "南宁": "NNG",
            "贵阳": "KWE",
            "桂林": "KWL",
            
            # 港澳台
            "香港": "HKG",
            "台北": "TPE",
            "高雄": "KHH",
            "澳门": "MFM",
            
            # 亚洲主要城市
            "东京": "NRT",
            "大阪": "KIX",
            "首尔": "ICN",
            "釜山": "PUS",
            "曼谷": "BKK",
            "新加坡": "SIN",
            "吉隆坡": "KUL",
            "雅加达": "CGK",
            "马尼拉": "MNL",
            "胡志明市": "SGN",
            "河内": "HAN",
            "金边": "PNH",
            "仰光": "RGN",
            "达卡": "DAC",
            "加德满都": "KTM",
            "科伦坡": "CMB",
            "德里": "DEL",
            "孟买": "BOM",
            "班加罗尔": "BLR",
            "迪拜": "DXB",
            "多哈": "DOH",
            "阿布扎比": "AUH",
            "科威特": "KWI",
            "利雅得": "RUH",
            "特拉维夫": "TLV",
            
            # 欧洲主要城市
            "伦敦": "LHR",
            "巴黎": "CDG",
            "法兰克福": "FRA",
            "阿姆斯特丹": "AMS",
            "苏黎世": "ZUR",
            "维也纳": "VIE",
            "罗马": "FCO",
            "米兰": "MXP",
            "马德里": "MAD",
            "巴塞罗那": "BCN",
            "莫斯科": "SVO",
            "圣彼得堡": "LED",
            "伊斯坦布尔": "IST",
            "雅典": "ATH",
            "布拉格": "PRG",
            "华沙": "WAW",
            "布达佩斯": "BUD",
            "斯德哥尔摩": "ARN",
            "哥本哈根": "CPH",
            "奥斯陆": "OSL",
            "赫尔辛基": "HEL",
            
            # 北美主要城市
            "纽约": "JFK",
            "洛杉矶": "LAX",
            "芝加哥": "ORD",
            "旧金山": "SFO",
            "西雅图": "SEA",
            "波士顿": "BOS",
            "华盛顿": "DCA",
            "迈阿密": "MIA",
            "拉斯维加斯": "LAS",
            "多伦多": "YYZ",
            "温哥华": "YVR",
            "蒙特利尔": "YUL",
            
            # 大洋洲主要城市
            "悉尼": "SYD",
            "墨尔本": "MEL",
            "布里斯班": "BNE",
            "珀斯": "PER",
            "奥克兰": "AKL",
            
            # 非洲主要城市
            "开罗": "CAI",
            "约翰内斯堡": "JNB",
            "开普敦": "CPT",
            "卡萨布兰卡": "CMN",
            "内罗毕": "NBO",
            
            # 南美主要城市
            "圣保罗": "GRU",
            "里约热内卢": "GIG",
            "布宜诺斯艾利斯": "EZE",
            "利马": "LIM",
            "圣地亚哥": "SCL"
        }
        
        # 首先尝试精确匹配
        if city in city_codes:
            return city_codes[city]
        
        # 尝试模糊匹配（去除空格和常见后缀）
        city_clean = city.replace(" ", "").replace("市", "").replace("省", "")
        for key, code in city_codes.items():
            if key.replace(" ", "") == city_clean:
                return code
        
        # 如果都没有匹配，记录警告并返回None
        logger.warning(f"未找到城市 '{city}' 的IATA代码")
        return None
    
    
    async def get_hotels(
        self, 
        destination: str, 
        check_in: date, 
        check_out: date
    ) -> List[Dict[str, Any]]:
        """获取酒店信息"""
        try:
            # 使用Booking.com API获取真实酒店数据
            if not settings.HOTEL_API_KEY:
                logger.warning("酒店API密钥未配置，返回空列表")
                return []
            
            # 调用Booking.com API
            hotels = await self._get_booking_hotels(destination, check_in, check_out)
            
            if not hotels:
                logger.warning("Booking.com API未返回数据，返回空列表")
                return []
            
            logger.info(f"从Booking.com API获取到 {len(hotels)} 条酒店数据")
            return hotels
            
        except Exception as e:
            logger.error(f"获取酒店数据失败: {e}")
            return []
    
    async def _get_booking_hotels(
        self, 
        destination: str, 
        check_in: date, 
        check_out: date
    ) -> List[Dict[str, Any]]:
        """调用Booking.com API获取酒店数据"""
        try:
            # Booking.com API端点
            url = "https://distribution-xml.booking.com/2.0/json/hotelAvailability"
            
            params = {
                "city": destination,
                "checkin": check_in.strftime("%Y-%m-%d"),
                "checkout": check_out.strftime("%Y-%m-%d"),
                "rooms": 1,
                "adults": 2,
                "limit": 10
            }
            
            headers = {
                "Authorization": f"Bearer {settings.HOTEL_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.get(url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return self._parse_booking_hotels(data)
            else:
                logger.error(f"Booking.com API错误: {response.status_code}")
                return []
                    
        except Exception as e:
            logger.error(f"Booking.com API调用失败: {e}")
            return []
    
    def _parse_booking_hotels(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析Booking.com API返回的酒店数据"""
        hotels = []
        
        try:
            for hotel in data.get("result", []):
                hotel_data = {
                    "id": f"hotel_{len(hotels) + 1}",
                    "name": hotel.get("name", "Unknown Hotel"),
                    "address": hotel.get("address", "N/A"),
                    "rating": float(hotel.get("rating", 0)),
                    "price_per_night": float(hotel.get("price", 0)),
                    "currency": hotel.get("currency", "CNY"),
                    "amenities": hotel.get("amenities", []),
                    "room_types": hotel.get("room_types", []),
                    "check_in": hotel.get("check_in", ""),
                    "check_out": hotel.get("check_out", ""),
                    "images": hotel.get("images", []),
                    "coordinates": hotel.get("coordinates", {}),
                    "star_rating": hotel.get("star_rating", 0)
                }
                hotels.append(hotel_data)
                
            return hotels
            
        except Exception as e:
            logger.error(f"解析Booking.com酒店数据失败: {e}")
            return []
    
    
    async def get_attractions(self, destination: str) -> List[Dict[str, Any]]:
        """获取景点信息"""
        try:
            # 使用Google Places API获取真实景点数据
            if not settings.MAP_API_KEY:
                logger.warning("地图API密钥未配置，返回空列表")
                return []
            
            # 调用Google Places API
            attractions = await self._get_google_places(destination)
            
            if not attractions:
                logger.warning("Google Places API未返回数据，返回空列表")
                return []
            
            logger.info(f"从Google Places API获取到 {len(attractions)} 条景点数据")
            return attractions
            
        except Exception as e:
            logger.error(f"获取景点数据失败: {e}")
            return []
    
    async def _get_google_places(self, destination: str) -> List[Dict[str, Any]]:
        """调用Google Places API获取景点数据"""
        try:
            # Google Places API端点
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            
            params = {
                "query": f"{destination} tourist attractions",
                "key": settings.MAP_API_KEY,
                "language": "zh-CN"
            }
            
            response = await self.http_client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return self._parse_google_places(data)
            else:
                logger.error(f"Google Places API错误: {response.status_code}")
                return []
                    
        except Exception as e:
            logger.error(f"Google Places API调用失败: {e}")
            return []
    
    def _parse_google_places(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析Google Places API返回的景点数据"""
        attractions = []
        
        try:
            for place in data.get("results", []):
                attraction = {
                    "id": f"attr_{len(attractions) + 1}",
                    "name": place.get("name", "Unknown Place"),
                    "category": place.get("types", ["attraction"])[0],
                    "description": place.get("formatted_address", "N/A"),
                    "rating": float(place.get("rating", 0)),
                    "price": 0,  # Google Places不提供价格信息
                    "currency": "CNY",
                    "opening_hours": "N/A",
                    "address": place.get("formatted_address", "N/A"),
                    "coordinates": place.get("geometry", {}).get("location", {}),
                    "images": [],
                    "features": place.get("types", []),
                    "visit_duration": "1-2小时"
                }
                attractions.append(attraction)
                
            return attractions
            
        except Exception as e:
            logger.error(f"解析Google Places景点数据失败: {e}")
            return []
    
    
    async def get_weather(
        self, 
        destination: str, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """获取天气信息"""
        try:
            if not settings.WEATHER_API_KEY:
                logger.warning("天气API密钥未配置")
                return {}
            
            # 返回空数据，等待真实API实现
            weather_data = {
                "location": destination,
                "forecast": [],
                "recommendations": []
            }
            
            logger.info(f"获取到天气信息: {destination}")
            return weather_data
            
        except Exception as e:
            logger.error(f"获取天气信息失败: {e}")
            return {}
    
    async def get_restaurants(self, destination: str) -> List[Dict[str, Any]]:
        """获取餐厅信息"""
        try:
            # 返回空数据，等待真实API实现
            restaurants = []
            
            logger.info(f"获取到 {len(restaurants)} 条餐厅信息")
            return restaurants
            
        except Exception as e:
            logger.error(f"获取餐厅信息失败: {e}")
            return []
    
    async def get_transportation(self, departure: str, destination: str) -> List[Dict[str, Any]]:
        """获取交通信息"""
        try:
            # 使用MCP服务获取真实交通数据
            transportation = await self._get_mcp_transportation(departure, destination)
            
            if not transportation:
                logger.warning("MCP服务未返回数据，返回空列表")
                return []
            
            logger.info(f"从MCP服务获取到 {len(transportation)} 条交通数据")

            logger.debug(f"MCP服务返回的交通数据: {transportation}")
            return transportation
            
        except Exception as e:
            logger.error(f"获取交通数据失败: {e}")
            return []
    
    async def _get_mcp_transportation(self, departure: str, destination: str) -> List[Dict[str, Any]]:
        """通过MCP服务获取交通数据"""
        try:
            # MCP服务端点 - 从配置中获取
            mcp_endpoints = [
                settings.BAIDU_MCP_ENDPOINT,  # 百度地图MCP服务
                settings.AMAP_MCP_ENDPOINT   # 高德地图MCP服务
            ]
            
            transportation = []
            
            # 尝试百度地图MCP服务
            try:
                baidu_data = await self._call_mcp_service(
                    mcp_endpoints[0], 
                    "map_directions",
                    {
                        "origin": departure,
                        "destination": destination,
                        "model": "transit",
                        "is_china": "true"
                    }
                )
                if baidu_data:
                    transportation.extend(self._parse_mcp_transportation(baidu_data, "百度地图"))
            except Exception as e:
                logger.warning(f"百度地图MCP服务调用失败: {e}")
            
            # 尝试高德地图MCP服务
            try:
                amap_data = await self._call_mcp_service(
                    mcp_endpoints[1],
                    "route_planning",
                    {
                        "origin": departure,
                        "destination": destination,
                        "model": "transit"  # 使用公共交通模式
                    }
                )
                if amap_data:
                    transportation.extend(self._parse_mcp_transportation(amap_data, "高德地图"))
            except Exception as e:
                logger.warning(f"高德地图MCP服务调用失败: {e}")
            
            return transportation
            
        except Exception as e:
            logger.error(f"MCP服务调用失败: {e}")
            return []
    
    async def _call_mcp_service(self, endpoint: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用MCP服务"""
        try:
            # 直接调用内置的百度地图MCP功能
            if "localhost" in endpoint:
                return await self._call_builtin_baidu_maps(method, params)
            else:
                # 其他服务使用JSON-RPC协议
                return await self._call_json_rpc_mcp(endpoint, method, params)
                    
        except Exception as e:
            logger.error(f"MCP服务调用异常: {e}")
            return None
    
    async def _call_baidu_mcp_api(self, endpoint: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用百度地图MCP API"""
        try:
            # 百度地图MCP服务使用HTTP API方式
            url = endpoint
            
            # 根据方法构建请求参数
            if method == "map_directions":
                api_params = {
                    "origin": params.get("origin", ""),
                    "destination": params.get("destination", ""),
                    "mode": params.get("mode", "transit"),
                    "output": "json"
                }
            else:
                api_params = params
            
            # 使用POST方法调用百度地图API
            response = await self.http_client.post(url, json=api_params)
            if response.status_code == 200:
                result = response.json()
                # 百度地图API返回格式
                if result.get("status") == 0:
                    return result
                else:
                    logger.error(f"百度地图API错误: {result.get('message', 'Unknown error')}")
                    return None
            else:
                logger.error(f"百度地图API HTTP错误: {response.status_code}")
                return None
                    
        except Exception as e:
            logger.error(f"百度地图MCP API调用异常: {e}")
            return None
    
    async def _call_builtin_baidu_maps(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """直接调用内置的百度地图功能"""
        try:
            # 导入百度地图集成模块
            from app.tools.baidu_maps_integration import call_baidu_maps_tool
            
            logger.debug(f"调用百度地图MCP: {method}, 参数: {params}")
            
            # 调用对应的工具函数
            result = await call_baidu_maps_tool(method, params)
            
            logger.debug(f"百度地图MCP返回: {result}")
            return result
                
        except Exception as e:
            logger.error(f"内置百度地图调用异常: {e}")
            return None

    async def _call_json_rpc_mcp(self, endpoint: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用JSON-RPC MCP服务"""
        try:
            # MCP服务使用JSON-RPC协议
            url = endpoint
            
            # 构建JSON-RPC请求
            json_rpc_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(url, json=json_rpc_request, headers=headers)
            if response.status_code == 200:
                result = response.json()
                # 检查JSON-RPC响应格式
                if "result" in result:
                    content = result["result"]
                    # 处理TextContent格式（百度地图MCP返回格式）
                    if isinstance(content, list) and len(content) > 0:
                        text_content = content[0]
                        if isinstance(text_content, dict) and text_content.get("type") == "text":
                            # 解析返回的JSON文本
                            try:
                                return json.loads(text_content.get("text", "{}"))
                            except json.JSONDecodeError:
                                logger.error("MCP服务返回的文本不是有效JSON")
                                return None
                    return content
                elif "error" in result:
                    logger.error(f"MCP服务错误: {result['error']}")
                    return None
                else:
                    return result
            else:
                logger.error(f"MCP服务HTTP错误: {response.status_code}")
                return None
                    
        except Exception as e:
            logger.error(f"JSON-RPC MCP服务调用异常: {e}")
            return None
    
    def _parse_mcp_transportation(self, data: Dict[str, Any], source: str) -> List[Dict[str, Any]]:
        """解析MCP服务返回的交通数据"""
        transportation = []
        
        try:
            # 处理百度地图MCP返回的数据
            if source == "百度地图":
                # MCP服务返回的是JSON字符串，需要先解析
                if isinstance(data, str):
                    try:
                        import json
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        logger.error("MCP返回的数据不是有效的JSON格式")
                        return []
                
                # 百度地图API返回格式
                routes = data.get("result", {}).get("routes", [])
                for i, route in enumerate(routes[:2]):  # 只取前2条路线
                    transportation.append({
                        "id": f"baidu_trans_{i+1}",
                        "type": "公共交通",
                        "name": f"百度路线{i+1}",
                        "description": f"百度地图推荐路线",
                        "price": self._estimate_cost_from_route(route),
                        "currency": "CNY",
                        "operating_hours": "06:00-23:00",
                        "frequency": "3-10分钟",
                        "coverage": ["目的地"],
                        "features": ["实时路况", "多方案选择"],
                        "source": "百度地图",
                        "duration": route.get("duration", 0) // 60,
                        "distance": route.get("distance", 0) // 1000
                    })
            
            # 处理高德地图MCP返回的数据
            elif source == "高德地图":
                # MCP服务返回的是JSON字符串，需要先解析
                if isinstance(data, str):
                    try:
                        import json
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        logger.error("MCP返回的数据不是有效的JSON格式")
                        return []
                
                routes = data.get("route", {}).get("paths", [])
                for i, route in enumerate(routes[:2]):  # 只取前2条路线
                    transportation.append({
                        "id": f"amap_trans_{i+1}",
                        "type": "公共交通",
                        "name": f"高德路线{i+1}",
                        "description": f"高德地图推荐路线",
                        "price": self._estimate_cost_from_route(route),
                        "currency": "CNY",
                        "operating_hours": "06:00-23:00",
                        "frequency": "3-10分钟",
                        "coverage": ["目的地"],
                        "features": ["实时路况", "多方案选择"],
                        "source": "高德地图",
                        "duration": route.get("duration", 0) // 60,
                        "distance": route.get("distance", 0) // 1000
                    })
            
            return transportation
            
        except Exception as e:
            logger.error(f"解析MCP交通数据失败: {e}")
            logger.debug(f"原始数据: {data}")
            return []
    
    def _estimate_cost_from_route(self, route: Dict[str, Any]) -> int:
        """从路线信息估算费用"""
        try:
            # 根据距离和交通方式估算费用
            distance = route.get("distance", 0) / 1000  # 转换为公里
            duration = route.get("duration", 0) / 60    # 转换为分钟
            
            # 简单估算：地铁3元起步，公交2元起步，出租车按距离计费
            if distance < 5:
                return 3  # 地铁短途
            elif distance < 10:
                return 5  # 地铁中途
            elif distance < 20:
                return 8  # 地铁长途
            else:
                return max(10, int(distance * 0.8))  # 出租车
                
        except Exception:
            return 5  # 默认费用
    
    
    async def get_images(self, query: str, count: int = 5) -> List[str]:
        """获取图片"""
        try:
            if not settings.MAP_API_KEY:
                logger.warning("地图API密钥未配置")
                return []
            
            # 返回空数据，等待真实API实现
            images = []
            
            logger.info(f"获取到 {len(images)} 张图片")
            return images[:count]
            
        except Exception as e:
            logger.error(f"获取图片失败: {e}")
            return []
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()
