#!/usr/bin/env python3
"""
测试百度地图集成功能
"""

import asyncio
import sys
import os
import json
import httpx

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.tools.baidu_maps_integration import map_directions, map_search_places

async def test_network_connectivity():
    """测试网络连接"""
    print("1. 测试网络连接...")
    
    # 测试百度地图API端点
    test_urls = [
        "https://api.map.baidu.com",
        "https://api.map.baidu.com/geocoding/v3/",
        "https://api.map.baidu.com/place/v3/region"
    ]
    
    for url in test_urls:
        try:
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.get(url)
                print(f"  ✓ {url} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"  ✗ {url} - 错误: {e}")
    
    print()

async def test_baidu_maps():
    """测试百度地图API调用"""
    print("开始测试百度地图集成功能...")
    
    # 先测试网络连接
    await test_network_connectivity()
    
    try:
        # 测试路线规划
        print("2. 测试路线规划 (北京 -> 上海)...")
        directions_result = await map_directions(
            origin="北京",
            destination="上海",
            model="driving",
            is_china="true"
        )
        print(f"路线规划状态: {directions_result.get('status', 'unknown')}")
        print(f"路线规划消息: {directions_result.get('message', 'N/A')}")
        
        print("完整路线规划响应:")
        print(json.dumps(directions_result, indent=2, ensure_ascii=False))
        
        if directions_result.get('status') == 0:
            routes = directions_result.get('result', {}).get('routes', [])
            print(f"找到 {len(routes)} 条路线")
            for i, route in enumerate(routes[:2]):  # 只显示前2条
                print(f"  路线 {i+1}:")
                print(f"    距离: {route.get('distance', 0)} 米")
                print(f"    时间: {route.get('duration', 0)} 秒")
                print(f"    交通状况: {route.get('traffic', {})}")
        else:
            print(f"路线规划失败: {directions_result.get('message', 'unknown error')}")
        
        # 测试地点搜索
        print("\n3. 测试地点搜索 (北京天安门)...")
        places_result = await map_search_places(
            query="北京天安门",
            region="北京",
            tag="景点",
            is_china="true"
        )
        print(f"地点搜索状态: {places_result.get('status', 'unknown')}")
        print(f"地点搜索消息: {places_result.get('message', 'N/A')}")
        
        print("完整地点搜索响应:")
        print(json.dumps(places_result, indent=2, ensure_ascii=False))
        
        if places_result.get('status') == 0:
            places = places_result.get('results', [])
            print(f"找到 {len(places)} 个地点")
            for i, place in enumerate(places[:3]):
                print(f"  地点 {i+1}:")
                print(f"    名称: {place.get('name', 'N/A')}")
                print(f"    地址: {place.get('address', 'N/A')}")
                print(f"    坐标: {place.get('location', {})}")
                print(f"    标签: {place.get('detail_info', {}).get('tag', 'N/A')}")
        else:
            print(f"地点搜索失败: {places_result.get('message', 'unknown error')}")
        
        # 测试景点搜索
        print("\n4. 测试景点搜索 (华山)...")
        attractions_result = await map_search_places(
            query="华山",
            region="陕西",
            tag="景点",
            is_china="true"
        )
        print(f"景点搜索状态: {attractions_result.get('status', 'unknown')}")
        print(f"景点搜索消息: {attractions_result.get('message', 'N/A')}")
        
        print("完整景点搜索响应:")
        print(json.dumps(attractions_result, indent=2, ensure_ascii=False))
        
        if attractions_result.get('status') == 0:
            attractions = attractions_result.get('results', [])
            print(f"找到 {len(attractions)} 个景点")
            for i, attraction in enumerate(attractions[:3]):
                print(f"  景点 {i+1}:")
                print(f"    名称: {attraction.get('name', 'N/A')}")
                print(f"    地址: {attraction.get('address', 'N/A')}")
                print(f"    坐标: {attraction.get('location', {})}")
                print(f"    标签: {attraction.get('detail_info', {}).get('tag', 'N/A')}")
        else:
            print(f"景点搜索失败: {attractions_result.get('message', 'unknown error')}")
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_baidu_maps())
