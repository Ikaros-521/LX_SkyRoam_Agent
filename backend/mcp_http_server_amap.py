#!/usr/bin/env python3
"""
高德地图 MCP HTTP 服务器 (Python 版本)
提供 HTTP API 接口，支持 JSON-RPC 协议
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List
from aiohttp import web, ClientSession
from aiohttp.web import Request, Response
from dotenv import load_dotenv
from loguru import logger

# 加载环境变量
load_dotenv()

class AmapMCPHTTPServer:
    """高德地图 MCP HTTP 服务器"""
    
    def __init__(self):
        self.app = web.Application()
        self.api_key = os.getenv('AMAP_API_KEY')
        self.port = int(os.getenv('MCP_HTTP_PORT', '3002'))
        self.session = None
        self.setup_routes()
    
    def setup_routes(self):
        """设置路由"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/tools', self.list_tools)
        self.app.router.add_post('/mcp', self.handle_mcp_request)
    
    async def health_check(self, request: Request) -> Response:
        """健康检查"""
        return web.json_response({
            'status': 'ok',
            'service': 'amap-mcp-server',
            'version': '1.0.0',
            'timestamp': str(asyncio.get_event_loop().time())
        })
    
    async def list_tools(self, request: Request) -> Response:
        """列出可用工具"""
        tools = [
            {
                'name': 'transit_route',
                'description': '公交路径规划',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'origin': {'type': 'string', 'description': '起点坐标'},
                        'destination': {'type': 'string', 'description': '终点坐标'},
                        'city': {'type': 'string', 'description': '城市名称'}
                    },
                    'required': ['origin', 'destination', 'city']
                }
            },
            {
                'name': 'driving_route',
                'description': '驾车路径规划',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'origin': {'type': 'string', 'description': '起点坐标'},
                        'destination': {'type': 'string', 'description': '终点坐标'}
                    },
                    'required': ['origin', 'destination']
                }
            },
            {
                'name': 'place_search',
                'description': '搜索地点',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'keywords': {'type': 'string', 'description': '搜索关键词'},
                        'city': {'type': 'string', 'description': '城市名称'},
                        'types': {'type': 'string', 'description': 'POI类型'},
                        'page_size': {'type': 'number', 'description': '每页结果数'},
                        'page_num': {'type': 'number', 'description': '页码'}
                    },
                    'required': ['keywords']
                }
            },
            {
                'name': 'geocode',
                'description': '地理编码 - 地址转坐标',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'address': {'type': 'string', 'description': '地址'},
                        'city': {'type': 'string', 'description': '城市名称'}
                    },
                    'required': ['address']
                }
            },
            {
                'name': 'reverse_geocode',
                'description': '逆地理编码 - 坐标转地址',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'location': {'type': 'string', 'description': '坐标 (经度,纬度)'},
                        'radius': {'type': 'number', 'description': '搜索半径'}
                    },
                    'required': ['location']
                }
            },
            {
                'name': 'weather_query',
                'description': '天气查询 - 获取指定城市的天气信息',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'city': {'type': 'string', 'description': '城市编码(adcode)或城市名称'},
                        'extensions': {'type': 'string', 'description': '返回结果控制，可选值：base(返回实况天气)、all(返回预报天气)，默认base'}
                    },
                    'required': ['city']
                }
            },
            {
                'name': 'place_around',
                'description': '周边搜索 - 基于中心点坐标搜索周边POI',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'location': {'type': 'string', 'description': '中心点坐标 (经度,纬度)'},
                        'keywords': {'type': 'string', 'description': '查询关键字'},
                        'types': {'type': 'string', 'description': 'POI类型，如050000(餐饮服务)、110000(风景名胜)'},
                        'radius': {'type': 'number', 'description': '查询半径，单位米，默认5000'},
                        'offset': {'type': 'number', 'description': '每页记录数据，默认20'},
                        'page': {'type': 'number', 'description': '当前页数，默认1'}
                    },
                    'required': ['location']
                }
            }
        ]
        return web.json_response({'tools': tools})
    
    async def handle_mcp_request(self, request: Request) -> Response:
        """处理 MCP 请求"""
        try:
            data = await request.json()
            jsonrpc = data.get('jsonrpc')
            method = data.get('method')
            params = data.get('params', {})
            request_id = data.get('id')
            
            if jsonrpc != '2.0':
                return web.json_response({
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {'code': -32600, 'message': 'Invalid Request'}
                })
            
            # 处理不同的方法
            if method == 'transit_route':
                result = await self.get_transit_route(params)
            elif method == 'driving_route':
                result = await self.get_driving_route(params)
            elif method == 'place_search':
                result = await self.search_places(params)
            elif method == 'geocode':
                result = await self.geocode_address(params)
            elif method == 'reverse_geocode':
                result = await self.reverse_geocode(params)
            elif method == 'weather_query':
                result = await self.get_weather(params)
            elif method == 'place_around':
                result = await self.search_places_around(params)
            else:
                return web.json_response({
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {'code': -32601, 'message': f'Method not found: {method}'}
                })
            
            return web.json_response({
                'jsonrpc': '2.0',
                'id': request_id,
                'result': result
            })
            
        except Exception as e:
            logger.error(f'MCP 请求处理失败: {e}')
            # 安全获取request_id，避免data变量未绑定的问题
            request_id = None
            try:
                if 'data' in locals() and data:
                    request_id = data.get('id')
            except:
                pass
            return web.json_response({
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {'code': -32603, 'message': str(e)}
            })
    
    async def get_transit_route(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取公交路线"""
        origin = params.get('origin')
        destination = params.get('destination')
        city = params.get('city', '北京')
        
        if not origin or not destination:
            raise ValueError('缺少起点或终点参数')
        
        # 调用真实的高德地图 API
        try:
            result = await self.call_amap_api('transit', {
                'origin': origin,
                'destination': destination,
                'city': city,
                'output': 'json'
            })
            # 关键日志：公交返回的核心信息
            try:
                route = (result or {}).get('route', {})
                paths = route.get('paths', []) or []
                if paths:
                    first = paths[0] or {}
                    logger.info(
                        f"[AMap Transit] origin={route.get('origin')} destination={route.get('destination')} "
                        f"paths={len(paths)} distance={first.get('distance')} duration={first.get('duration')} "
                        f"strategy={first.get('strategy')} steps={len(first.get('steps') or [])}"
                    )
                else:
                    logger.info(
                        f"[AMap Transit] origin={origin} destination={destination} 无可用路径"
                    )
            except Exception as log_e:
                logger.warning(f"公交关键日志生成失败: {log_e}")
            return result
        except Exception as e:
            logger.error(f'调用高德地图API失败: {e}')
            raise Exception(f'无法获取公交路线: {e}')
    
    async def get_driving_route(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取驾车路线"""
        origin = params.get('origin')
        destination = params.get('destination')
        
        if not origin or not destination:
            raise ValueError('缺少起点或终点参数')
        
        # 如果输入的是地址名称，需要先进行地理编码
        try:
            # 检查是否是坐标格式 (经度,纬度)
            if ',' not in origin:
                logger.info(f'起点需要地理编码: {origin}')
                origin_coords = await self.geocode_address({'address': origin})
                if origin_coords.get('status') == '1' and origin_coords.get('geocodes'):
                    origin = origin_coords['geocodes'][0]['location']
                    logger.info(f'起点地理编码成功: {origin}')
                else:
                    raise Exception(f'起点地理编码失败: {origin}')
            
            if ',' not in destination:
                logger.info(f'终点需要地理编码: {destination}')
                dest_coords = await self.geocode_address({'address': destination})
                if dest_coords.get('status') == '1' and dest_coords.get('geocodes'):
                    destination = dest_coords['geocodes'][0]['location']
                    logger.info(f'终点地理编码成功: {destination}')
                else:
                    raise Exception(f'终点地理编码失败: {destination}')
            
            logger.info(f'最终坐标: {origin} -> {destination}')
            
            # 调用真实的高德地图 API
            result = await self.call_amap_api('driving', {
                'origin': origin,
                'destination': destination
            })
            # 关键日志：驾车返回的核心信息
            try:
                route = (result or {}).get('route', {})
                paths = route.get('paths', []) or []
                if paths:
                    first = paths[0] or {}
                    logger.info(
                        f"[AMap Driving] origin={route.get('origin')} destination={route.get('destination')} "
                        f"paths={len(paths)} distance={first.get('distance')} duration={first.get('duration')} "
                        f"tolls={first.get('tolls')} toll_distance={first.get('toll_distance')} "
                        f"steps={len(first.get('steps') or [])}"
                    )
                else:
                    logger.info(
                        f"[AMap Driving] origin={origin} destination={destination} 无可用路径"
                    )
            except Exception as log_e:
                logger.warning(f"驾车关键日志生成失败: {log_e}")
            return result
        except Exception as e:
            logger.error(f'调用高德地图API失败: {e}')
            raise Exception(f'无法获取驾车路线: {e}')
    
    async def call_amap_api(self, api_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用高德地图 API"""
        if not self.session:
            self.session = ClientSession()
        
        # 构建 API URL
        base_url = 'https://restapi.amap.com/v3'
        api_urls = {
            'transit': f'{base_url}/direction/transit',
            'driving': f'{base_url}/direction/driving',
            'walking': f'{base_url}/direction/walking',
            'place_search': f'{base_url}/place/text',
            'place_around': f'{base_url}/place/around',
            'geocode': f'{base_url}/geocode/geo',
            'reverse_geocode': f'{base_url}/geocode/regeo',
            'weather': f'{base_url}/weather/weatherInfo'
        }
        
        url = api_urls.get(api_type)
        if not url:
            raise ValueError(f'不支持的API类型: {api_type}')
        
        # 添加 API Key 和其他必要参数
        params['key'] = self.api_key
        params['extensions'] = 'all'  # 获取详细信息
        params['output'] = 'json'     # 使用 JSON 格式，更方便处理
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    # 获取 JSON 响应
                    result = await response.json()
                    logger.info(f'[{api_type}] 高德地图API响应: {json.dumps(result, ensure_ascii=False)[:500]}...')
                    
                    # 检查响应状态
                    if result.get('status') == '1':
                        return result
                    else:
                        raise Exception(f'[{api_type}] 高德地图API错误: {result.get("info", "未知错误")}')
                else:
                    raise Exception(f'[{api_type}] HTTP请求失败: {response.status}')
        except Exception as e:
            logger.error(f'[{api_type}] 调用高德地图API失败: {e}')
            raise
    
    async def search_places(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索地点"""
        keywords = params.get('keywords')
        city = params.get('city', '北京')
        types = params.get('types', '')
        page_size = params.get('page_size', 20)
        page_num = params.get('page_num', 1)
        
        if not keywords:
            raise ValueError('缺少搜索关键词')
        
        try:
            result = await self.call_amap_api('place_search', {
                'keywords': keywords,
                'city': city,
                'types': types,
                'page_size': page_size,
                'page_num': page_num
            })
            return result
        except Exception as e:
            logger.error(f'搜索地点失败: {e}')
            raise Exception(f'无法搜索地点: {e}')
    
    async def geocode_address(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """地理编码 - 地址转坐标"""
        address = params.get('address')
        city = params.get('city', '')
        
        if not address:
            raise ValueError('缺少地址参数')
        
        try:
            result = await self.call_amap_api('geocode', {
                'address': address,
                'city': city
            })
            return result
        except Exception as e:
            logger.error(f'地理编码失败: {e}')
            raise Exception(f'无法进行地理编码: {e}')
    
    async def reverse_geocode(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """逆地理编码 - 坐标转地址"""
        location = params.get('location')
        radius = params.get('radius', 1000)
        
        if not location:
            raise ValueError('缺少坐标参数')
        
        try:
            result = await self.call_amap_api('reverse_geocode', {
                'location': location,
                'radius': radius
            })
            return result
        except Exception as e:
            logger.error(f'逆地理编码失败: {e}')
            raise Exception(f'无法进行逆地理编码: {e}')
    
    async def get_weather(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """天气查询 - 获取指定城市的天气信息"""
        city = params.get('city')
        extensions = params.get('extensions', 'base')
        
        if not city:
            raise ValueError('缺少城市参数')
        
        # 如果输入的是城市名称而不是城市编码，需要先进行地理编码获取adcode
        try:
            # 检查是否是纯数字的城市编码格式
            if not city.isdigit():
                logger.info(f'城市名称需要地理编码: {city}')
                geocode_result = await self.geocode_address({'address': city})
                if geocode_result.get('status') == '1' and geocode_result.get('geocodes'):
                    city = geocode_result['geocodes'][0]['adcode']
                    logger.info(f'城市地理编码成功，获取adcode: {city}')
                else:
                    raise Exception(f'城市地理编码失败: {city}')
            
            logger.info(f'查询天气，城市编码: {city}, 扩展信息: {extensions}')
            
            # 调用真实的高德地图天气API
            result = await self.call_amap_api('weather', {
                'city': city,
                'extensions': extensions
            })
            
            # 关键日志：天气返回的核心信息
            try:
                if extensions == 'base':
                    # 实况天气
                    lives = result.get('lives', [])
                    if lives:
                        weather_info = lives[0]
                        logger.info(
                            f"[AMap Weather] city={weather_info.get('city')} "
                            f"weather={weather_info.get('weather')} "
                            f"temperature={weather_info.get('temperature')}°C "
                            f"humidity={weather_info.get('humidity')}% "
                            f"wind={weather_info.get('winddirection')}{weather_info.get('windpower')} "
                            f"reporttime={weather_info.get('reporttime')}"
                        )
                    else:
                        logger.info(f"[AMap Weather] city={city} 无实况天气数据")
                else:
                    # 预报天气
                    forecasts = result.get('forecasts', [])
                    if forecasts:
                        forecast_info = forecasts[0]
                        casts = forecast_info.get('casts', [])
                        logger.info(
                            f"[AMap Weather] city={forecast_info.get('city')} "
                            f"forecasts={len(casts)}天 "
                            f"reporttime={forecast_info.get('reporttime')}"
                        )
                    else:
                        logger.info(f"[AMap Weather] city={city} 无预报天气数据")
            except Exception as log_e:
                logger.warning(f"天气关键日志生成失败: {log_e}")
            
            return result
        except Exception as e:
            logger.error(f'调用高德地图天气API失败: {e}')
            raise Exception(f'无法获取天气信息: {e}')
    
    async def search_places_around(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """周边搜索 - 基于中心点坐标搜索周边POI"""
        location = params.get('location')
        keywords = params.get('keywords', '')
        types = params.get('types', '')
        radius = params.get('radius', 5000)
        offset = params.get('offset', 20)
        page = params.get('page', 1)
        
        if not location:
            raise ValueError('缺少中心点坐标参数')
        
        # 如果没有指定keywords和types，默认搜索餐饮、购物服务、生活服务、住宿服务
        if not keywords and not types:
            types = '050000|060000|070000|100000'
        
        try:
            logger.info(f'周边搜索，中心点: {location}, 关键词: {keywords}, 类型: {types}, 半径: {radius}米')
            
            # 调用真实的高德地图周边搜索API
            result = await self.call_amap_api('place_around', {
                'location': location,
                'keywords': keywords,
                'types': types,
                'radius': radius,
                'offset': offset,
                'page': page
            })
            
            # 关键日志：周边搜索返回的核心信息
            try:
                pois = result.get('pois', [])
                logger.info(
                    f"[AMap PlaceAround] location={location} keywords={keywords} types={types} "
                    f"radius={radius} pois={len(pois)} page={page}"
                )
                if pois:
                    # 记录前几个POI的基本信息
                    for i, poi in enumerate(pois[:3]):
                        logger.info(
                            f"[AMap POI {i+1}] name={poi.get('name')} type={poi.get('type')} "
                            f"address={poi.get('address')} distance={poi.get('distance')}m"
                        )
            except Exception as log_e:
                logger.warning(f"周边搜索关键日志生成失败: {log_e}")
            
            return result
        except Exception as e:
            logger.error(f'调用高德地图周边搜索API失败: {e}')
            raise Exception(f'无法进行周边搜索: {e}')
    
    async def start(self):
        """启动服务器"""
        if not self.api_key:
            raise ValueError('未配置 AMAP_API_KEY 环境变量')
        
        logger.info(f'正在启动高德地图 MCP HTTP 服务器...')
        logger.info(f'API Key: {self.api_key[:10]}...')
        
        # 创建 HTTP 会话
        self.session = ClientSession()
        
        # 启动服务器
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        logger.info(f'✅ 高德地图 MCP HTTP 服务器启动成功!')
        logger.info(f'📍 服务器地址: http://localhost:{self.port}')
        logger.info(f'🔍 健康检查: http://localhost:{self.port}/health')
        logger.info(f'🛠️  工具列表: http://localhost:{self.port}/tools')
        logger.info(f'📡 MCP 接口: http://localhost:{self.port}/mcp')
        logger.info('按 Ctrl+C 停止服务器')
        
        # 保持服务器运行
        try:
            await asyncio.Future()  # 永远等待
        except KeyboardInterrupt:
            logger.info('🛑 正在停止服务器...')
            await self.session.close()
            await runner.cleanup()
            logger.info('✅ 服务器已停止')

async def main():
    """主函数"""
    server = AmapMCPHTTPServer()
    await server.start()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('服务器已停止')
    except Exception as e:
        logger.error(f'服务器启动失败: {e}')
        sys.exit(1)
