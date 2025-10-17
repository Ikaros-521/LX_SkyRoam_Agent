#!/usr/bin/env python3
"""
测试重构后的地理编码功能
验证DataCollector的统一地理编码函数和PlanGenerator的集成
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.data_collector import DataCollector
from app.services.plan_generator import PlanGenerator
from app.core.config import settings

async def test_unified_geocoding():
    """测试统一的地理编码功能"""
    print("=== 测试统一地理编码功能 ===")
    
    # 初始化DataCollector
    data_collector = DataCollector()
    
    # 测试不同的目的地
    test_destinations = [
        "北京",
        "上海",
        "广州",
        "深圳",
        "杭州"
    ]
    
    for destination in test_destinations:
        print(f"\n测试目的地: {destination}")
        try:
            geocode_info = await data_collector.get_destination_geocode_info(destination)
            if geocode_info:
                print(f"  ✓ 成功获取地理编码信息:")
                print(f"    - 坐标: ({geocode_info['latitude']}, {geocode_info['longitude']})")
                print(f"    - 提供商: {geocode_info['provider']}")
                print(f"    - 格式化地址: {geocode_info['formatted_address']}")
            else:
                print(f"  ✗ 未能获取地理编码信息")
        except Exception as e:
            print(f"  ✗ 错误: {e}")

async def test_plan_generator_integration():
    """测试PlanGenerator与新地理编码功能的集成"""
    print("\n=== 测试PlanGenerator集成 ===")
    
    # 创建模拟的processed_data
    mock_processed_data = {
        'hotels': [
            {
                'name': '测试酒店',
                'latitude': 39.9042,
                'longitude': 116.4074,
                'address': '北京市朝阳区'
            }
        ],
        'attractions': [
            {
                'name': '天安门广场',
                'latitude': 39.9042,
                'longitude': 116.4074,
                'address': '北京市东城区'
            }
        ],
        'restaurants': [
            {
                'name': '测试餐厅',
                'latitude': 39.9042,
                'longitude': 116.4074,
                'address': '北京市西城区'
            }
        ]
    }
    
    # 初始化PlanGenerator
    plan_generator = PlanGenerator()
    
    # 测试_extract_destination_info方法
    destination = "北京"
    print(f"\n测试目的地: {destination}")
    
    try:
        destination_info = await plan_generator._extract_destination_info(mock_processed_data, destination)
        if destination_info:
            print(f"  ✓ 成功提取目的地信息:")
            print(f"    - 名称: {destination_info['name']}")
            print(f"    - 坐标: ({destination_info['latitude']}, {destination_info['longitude']})")
            print(f"    - 来源: {destination_info['source']}")
        else:
            print(f"  ✗ 未能提取目的地信息")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

async def main():
    """主测试函数"""
    print("开始测试重构后的地理编码功能...\n")
    
    try:
        # 测试统一地理编码功能
        await test_unified_geocoding()
        
        # 测试PlanGenerator集成
        await test_plan_generator_integration()
        
        print("\n=== 测试完成 ===")
        print("✓ 地理编码重构测试完成")
        
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())