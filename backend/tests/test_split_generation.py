#!/usr/bin/env python3
"""
测试拆分生成功能
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.plan_generator import PlanGenerator
from app.core.config import settings

async def test_split_generation():
    """测试拆分生成功能"""
    
    # 创建计划生成器
    generator = PlanGenerator()
    
    # 测试数据 - 多个偏好的情况
    test_data = {
        "departure": "北京",
        "destination": "南昌",
        "start_date": datetime.now() + timedelta(days=7),
        "end_date": datetime.now() + timedelta(days=10),
        "duration_days": 3,
        "budget": 5000,
        "travelers": 2,
        "preferences": {
            "budget_priority": "medium",
            "activity_preference": ["culture", "food", "nature"],  # 多个偏好
            "travelers_count": 2,
            "food_preferences": ["local"],
            "dietary_restrictions": [],
            "age_groups": ["adult"]
        },
        "requirements": {
            "special_needs": "无特殊需求"
        }
    }
    
    print("开始测试拆分生成功能...")
    print(f"偏好设置: {test_data['preferences']['activity_preference']}")
    
    try:
        # 构造processed_data和plan对象
        processed_data = {
            "departure": test_data["departure"],
            "destination": test_data["destination"],
            "start_date": test_data["start_date"],
            "end_date": test_data["end_date"],
            "duration_days": test_data["duration_days"],
            "budget": test_data["budget"],
            "travelers": test_data["travelers"]
        }
        
        # 模拟plan对象
        class MockPlan:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        plan = MockPlan(test_data)
        
        # 生成方案
        plans = await generator.generate_plans(
            processed_data=processed_data,
            plan=plan,
            preferences=test_data["preferences"],
            raw_data={}
        )
        
        print(f"\n生成了 {len(plans)} 个方案:")
        for i, plan in enumerate(plans, 1):
            print(f"\n方案 {i}: {plan.get('title', '未命名方案')}")
            print(f"  类型: {plan.get('plan_type', '未知类型')}")
            print(f"  总费用: ¥{plan.get('total_cost', 0)}")
            print(f"  评分: {plan.get('score', 0):.2f}")
            
            # 显示每日行程概要
            daily_itineraries = plan.get('daily_itineraries', [])
            for day_idx, day in enumerate(daily_itineraries, 1):
                attractions = day.get('attractions', [])
                restaurants = day.get('restaurants', [])
                print(f"    第{day_idx}天: {len(attractions)}个景点, {len(restaurants)}个餐厅")
        
        print(f"\n测试完成！成功生成 {len(plans)} 个方案")
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_single_preference():
    """测试单个偏好的情况"""
    
    generator = PlanGenerator()
    
    test_data = {
        "departure": "北京",
        "destination": "南昌",
        "start_date": datetime.now() + timedelta(days=7),
        "end_date": datetime.now() + timedelta(days=10),
        "duration_days": 3,
        "budget": 5000,
        "travelers": 2,
        "preferences": {
            "budget_priority": "medium",
            "activity_preference": ["culture"],  # 单个偏好
            "travelers_count": 2,
            "food_preferences": ["local"],
            "dietary_restrictions": [],
            "age_groups": ["adult"]
        },
        "requirements": {
            "special_needs": "无特殊需求"
        }
    }
    
    print("\n开始测试单个偏好情况...")
    print(f"偏好设置: {test_data['preferences']['activity_preference']}")
    
    try:
        # 构造processed_data和plan对象
        processed_data = {
            "departure": test_data["departure"],
            "destination": test_data["destination"],
            "start_date": test_data["start_date"],
            "end_date": test_data["end_date"],
            "duration_days": test_data["duration_days"],
            "budget": test_data["budget"],
            "travelers": test_data["travelers"]
        }
        
        # 模拟plan对象
        class MockPlan:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        plan = MockPlan(test_data)
        
        plans = await generator.generate_plans(
            processed_data=processed_data,
            plan=plan,
            preferences=test_data["preferences"],
            raw_data={}
        )
        
        print(f"单个偏好生成了 {len(plans)} 个方案")
        return True
        
    except Exception as e:
        print(f"单个偏好测试失败: {e}")
        return False

if __name__ == "__main__":
    async def main():
        print("=" * 50)
        print("拆分生成功能测试")
        print("=" * 50)
        
        # 测试多个偏好
        success1 = await test_split_generation()
        
        # 测试单个偏好
        success2 = await test_single_preference()
        
        print("\n" + "=" * 50)
        if success1 and success2:
            print("所有测试通过！")
        else:
            print("部分测试失败！")
        print("=" * 50)
    
    asyncio.run(main())