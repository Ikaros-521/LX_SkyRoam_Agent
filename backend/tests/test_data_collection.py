#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据收集功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.data_collector import DataCollector

async def test_data_collection():
    """测试数据收集功能"""
    print("开始测试数据收集功能...")
    
    # 创建数据收集器实例
    collector = DataCollector()
    
    # 测试目的地
    destination = "北京天安门"
    
    try:
        # 1. 测试餐厅数据收集
        print(f"\n1. 测试餐厅数据收集 - 目的地: {destination}")
        restaurants = await collector.collect_restaurant_data(destination)
        print(f"   收集到 {len(restaurants)} 家餐厅:")
        for i, restaurant in enumerate(restaurants[:5], 1):
            print(f"   {i}. {restaurant.get('name', '未知餐厅')} - {restaurant.get('address', '地址未知')}")
            print(f"      数据源: {restaurant.get('data_source', '未知')}")
        
        # 2. 测试景点数据收集
        print(f"\n2. 测试景点数据收集 - 目的地: {destination}")
        attractions = await collector.collect_attraction_data(destination)
        print(f"   收集到 {len(attractions)} 个景点:")
        for i, attraction in enumerate(attractions[:5], 1):
            print(f"   {i}. {attraction.get('name', '未知景点')} - {attraction.get('address', '地址未知')}")
            print(f"      数据源: {attraction.get('data_source', '未知')}")
        
        print(f"\n✅ 数据收集功能测试完成!")
        print(f"   餐厅数据: {len(restaurants)} 条")
        print(f"   景点数据: {len(attractions)} 条")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_data_collection())