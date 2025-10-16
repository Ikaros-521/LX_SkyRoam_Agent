#!/usr/bin/env python3
"""
直接测试MCP服务器的周边搜索功能
"""
import asyncio
import aiohttp
import json

async def test_mcp_place_around():
    """测试MCP服务器的周边搜索功能"""
    print("开始测试MCP服务器周边搜索功能...")
    
    # MCP服务器地址
    mcp_url = "http://localhost:3002/mcp"
    
    # 测试数据
    test_location = "116.397128,39.916527"  # 天安门广场坐标
    
    async with aiohttp.ClientSession() as session:
        try:
            # 1. 测试餐厅周边搜索
            print("\n1. 测试餐厅周边搜索...")
            restaurant_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "place_around",
                "params": {
                    "location": test_location,
                    "keywords": "餐厅",
                    "types": "050000",
                    "radius": 5000,
                    "offset": 10
                }
            }
            
            async with session.post(mcp_url, json=restaurant_request) as response:
                if response.status == 200:
                    result = await response.json()
                    if "error" in result:
                        print(f"   搜索失败: {result.get('error', '未知错误')}")
                    elif "result" in result:
                        api_result = result.get("result", {})
                        if isinstance(api_result, dict) and "pois" in api_result:
                            restaurants = api_result.get("pois", [])
                            print(f"   找到 {len(restaurants)} 家餐厅:")
                            for i, restaurant in enumerate(restaurants[:5], 1):
                                print(f"   {i}. {restaurant.get('name', '未知餐厅')} - {restaurant.get('address', '地址未知')}")
                        else:
                            print(f"   响应数据格式异常: {api_result}")
                    else:
                        print(f"   响应格式异常: {result}")
                else:
                    print(f"   HTTP请求失败: {response.status}")
            
            # 2. 测试景点周边搜索
            print("\n2. 测试景点周边搜索...")
            attraction_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "place_around",
                "params": {
                    "location": test_location,
                    "keywords": "景点",
                    "types": "110000",
                    "radius": 10000,
                    "offset": 10
                }
            }
            
            async with session.post(mcp_url, json=attraction_request) as response:
                if response.status == 200:
                    result = await response.json()
                    if "error" in result:
                        print(f"   搜索失败: {result.get('error', '未知错误')}")
                    elif "result" in result:
                        api_result = result.get("result", {})
                        if isinstance(api_result, dict) and "pois" in api_result:
                            attractions = api_result.get("pois", [])
                            print(f"   找到 {len(attractions)} 个景点:")
                            for i, attraction in enumerate(attractions[:5], 1):
                                print(f"   {i}. {attraction.get('name', '未知景点')} - {attraction.get('address', '地址未知')}")
                        else:
                            print(f"   响应数据格式异常: {api_result}")
                    else:
                        print(f"   响应格式异常: {result}")
                else:
                    print(f"   HTTP请求失败: {response.status}")
            
            # 3. 测试博物馆周边搜索
            print("\n3. 测试博物馆周边搜索...")
            museum_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "place_around",
                "params": {
                    "location": test_location,
                    "keywords": "博物馆",
                    "types": "140700",
                    "radius": 15000,
                    "offset": 10
                }
            }
            
            async with session.post(mcp_url, json=museum_request) as response:
                if response.status == 200:
                    result = await response.json()
                    if "error" in result:
                        print(f"   搜索失败: {result.get('error', '未知错误')}")
                    elif "result" in result:
                        api_result = result.get("result", {})
                        if isinstance(api_result, dict) and "pois" in api_result:
                            museums = api_result.get("pois", [])
                            print(f"   找到 {len(museums)} 个博物馆:")
                            for i, museum in enumerate(museums[:5], 1):
                                print(f"   {i}. {museum.get('name', '未知博物馆')} - {museum.get('address', '地址未知')}")
                        else:
                            print(f"   响应数据格式异常: {api_result}")
                    else:
                        print(f"   响应格式异常: {result}")
                else:
                    print(f"   HTTP请求失败: {response.status}")
            
            print("\n✅ MCP服务器周边搜索功能测试完成!")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_place_around())