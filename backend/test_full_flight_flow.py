#!/usr/bin/env python3
"""
测试完整的航班数据流程
从 Amadeus API 获取数据 -> 数据收集 -> 计划生成 -> 前端显示
"""

import asyncio
import json
import sys
import os
from datetime import date, datetime, timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.tools.mcp_client import MCPClient
from app.services.data_collector import DataCollector
from app.services.plan_generator import PlanGenerator
from app.core.config import settings

async def test_flight_data_flow():
    """测试完整的航班数据流程"""
    print("🚀 开始测试完整的航班数据流程...")
    
    # 测试参数
    destination = "上海"
    departure_date = date.today() + timedelta(days=7)  # 一周后
    return_date = departure_date + timedelta(days=3)   # 3天后返回
    origin = "北京"
    
    print(f"📍 测试路线: {origin} -> {destination}")
    print(f"📅 出发日期: {departure_date}")
    print(f"📅 返回日期: {return_date}")
    print("-" * 50)
    
    try:
        # 步骤 1: 测试 MCP Client 航班数据获取
        print("1️⃣ 测试 MCP Client 航班数据获取...")
        mcp_client = MCPClient()
        
        flights = await mcp_client.get_flights(
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            origin=origin
        )
        
        if flights:
            print(f"✅ 成功获取 {len(flights)} 条航班数据")
            print(f"📊 示例航班数据:")
            for i, flight in enumerate(flights[:2]):  # 显示前2条
                print(f"   航班 {i+1}: {flight.get('flight_number')} - {flight.get('airline_name')} - ¥{flight.get('price_cny', flight.get('price'))}")
        else:
            print("❌ 未获取到航班数据")
            return False
        
        print("-" * 50)
        
        # 步骤 2: 测试 DataCollector 航班数据收集
        print("2️⃣ 测试 DataCollector 航班数据收集...")
        data_collector = DataCollector()
        
        collected_flights = await data_collector.collect_flight_data(
            departure=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date
        )
        
        if collected_flights:
            print(f"✅ DataCollector 成功收集 {len(collected_flights)} 条航班数据")
            print(f"📊 收集的数据包含字段: {list(collected_flights[0].keys()) if collected_flights else []}")
        else:
            print("❌ DataCollector 未收集到航班数据")
            return False
        
        print("-" * 50)
        
        # 步骤 3: 测试 PlanGenerator 航班数据格式化
        print("3️⃣ 测试 PlanGenerator 航班数据格式化...")
        plan_generator = PlanGenerator()
        
        formatted_flights = plan_generator._format_data_for_llm(collected_flights, 'flight')
        
        if formatted_flights and formatted_flights != "暂无数据":
            print(f"✅ PlanGenerator 成功格式化航班数据")
            print(f"📝 格式化后的数据预览:")
            # 显示前200个字符
            preview = formatted_flights[:200] + "..." if len(formatted_flights) > 200 else formatted_flights
            print(f"   {preview}")
        else:
            print("❌ PlanGenerator 格式化失败")
            return False
        
        print("-" * 50)
        
        # 步骤 4: 验证数据结构完整性
        print("4️⃣ 验证数据结构完整性...")
        
        required_fields = [
            'flight_number', 'airline_name', 'departure_time', 'arrival_time',
            'duration', 'price_cny', 'cabin_class', 'stops', 'origin', 'destination'
        ]
        
        sample_flight = collected_flights[0]
        missing_fields = []
        
        for field in required_fields:
            if field not in sample_flight or sample_flight[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"⚠️  缺少字段: {missing_fields}")
        else:
            print("✅ 所有必需字段都存在")
        
        # 验证数据类型
        print("🔍 验证数据类型:")
        print(f"   flight_number: {type(sample_flight.get('flight_number'))} = {sample_flight.get('flight_number')}")
        print(f"   price_cny: {type(sample_flight.get('price_cny'))} = {sample_flight.get('price_cny')}")
        print(f"   stops: {type(sample_flight.get('stops'))} = {sample_flight.get('stops')}")
        print(f"   duration: {type(sample_flight.get('duration'))} = {sample_flight.get('duration')}")
        
        print("-" * 50)
        
        # 步骤 5: 生成测试用的 JSON 数据
        print("5️⃣ 生成测试用的 JSON 数据...")
        
        test_data = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "route": f"{origin} -> {destination}",
                "departure_date": departure_date.isoformat(),
                "return_date": return_date.isoformat(),
                "total_flights": len(collected_flights)
            },
            "raw_flights": flights[:3],  # 原始 API 数据
            "processed_flights": collected_flights[:3],  # 处理后的数据
            "formatted_for_llm": formatted_flights  # LLM 格式化数据
        }
        
        # 保存测试数据
        test_file = project_root / "test_flight_data.json"
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ 测试数据已保存到: {test_file}")
        
        print("-" * 50)
        print("🎉 完整的航班数据流程测试成功!")
        print(f"📈 总结:")
        print(f"   - Amadeus API: {len(flights)} 条原始数据")
        print(f"   - DataCollector: {len(collected_flights)} 条处理数据")
        print(f"   - PlanGenerator: 格式化成功")
        print(f"   - 数据完整性: {'✅ 通过' if not missing_fields else '⚠️ 部分缺失'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        print(f"详细错误信息: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(test_flight_data_flow())
    
    if success:
        print("\n🚀 下一步: 在前端创建一个旅行计划来查看航班信息显示效果")
        print("   1. 访问 http://localhost:3000")
        print("   2. 创建一个新的旅行计划")
        print("   3. 选择北京到上海的路线")
        print("   4. 查看生成的计划中的航班信息显示")
    else:
        print("\n❌ 测试失败，请检查错误信息并修复问题")
    
    sys.exit(0 if success else 1)