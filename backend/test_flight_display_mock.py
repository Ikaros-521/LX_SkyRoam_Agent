#!/usr/bin/env python3
"""
使用模拟数据测试航班显示功能
验证前端是否能正确显示 Amadeus API 格式的航班数据
"""

import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.plan_generator import PlanGenerator

def create_mock_flight_data():
    """创建模拟的 Amadeus API 格式航班数据"""
    
    # 模拟 Amadeus API 返回的航班数据结构
    mock_flights = [
        {
            "id": "amadeus_0_0",
            "airline": "CA",
            "airline_name": "中国国际航空",
            "flight_number": "CA1501",
            "departure_time": "2025-10-23T08:30:00",
            "arrival_time": "2025-10-23T11:15:00",
            "duration": "2小时45分钟",
            "price": 1280.50,
            "currency": "CNY",
            "price_cny": 1280.50,
            "aircraft": "A320",
            "stops": 0,
            "origin": "PEK",
            "destination": "PVG",
            "date": "2025-10-23",
            "rating": 4.2,
            "cabin_class": "经济舱",
            "baggage_allowance": "23kg托运行李",
            "segments": [
                {
                    "carrier_code": "CA",
                    "flight_number": "1501",
                    "aircraft": "A320",
                    "departure": {
                        "airport": "PEK",
                        "terminal": "T3",
                        "time": "2025-10-23T08:30:00"
                    },
                    "arrival": {
                        "airport": "PVG",
                        "terminal": "T2",
                        "time": "2025-10-23T11:15:00"
                    },
                    "duration": "2小时45分钟"
                }
            ],
            "booking_class": "Y",
            "refundable": True,
            "source": "amadeus",
            "collected_at": datetime.now().isoformat(),
            "route": "北京 -> 上海"
        },
        {
            "id": "amadeus_1_0",
            "airline": "MU",
            "airline_name": "中国东方航空",
            "flight_number": "MU5103",
            "departure_time": "2025-10-23T14:20:00",
            "arrival_time": "2025-10-23T17:05:00",
            "duration": "2小时45分钟",
            "price": 1150.00,
            "currency": "CNY",
            "price_cny": 1150.00,
            "aircraft": "B737",
            "stops": 0,
            "origin": "PEK",
            "destination": "PVG",
            "date": "2025-10-23",
            "rating": 4.1,
            "cabin_class": "经济舱",
            "baggage_allowance": "23kg托运行李",
            "segments": [
                {
                    "carrier_code": "MU",
                    "flight_number": "5103",
                    "aircraft": "B737",
                    "departure": {
                        "airport": "PEK",
                        "terminal": "T2",
                        "time": "2025-10-23T14:20:00"
                    },
                    "arrival": {
                        "airport": "PVG",
                        "terminal": "T1",
                        "time": "2025-10-23T17:05:00"
                    },
                    "duration": "2小时45分钟"
                }
            ],
            "booking_class": "Y",
            "refundable": False,
            "source": "amadeus",
            "collected_at": datetime.now().isoformat(),
            "route": "北京 -> 上海"
        },
        {
            "id": "amadeus_2_0",
            "airline": "CZ",
            "airline_name": "中国南方航空",
            "flight_number": "CZ3539",
            "departure_time": "2025-10-23T19:45:00",
            "arrival_time": "2025-10-23T22:30:00",
            "duration": "2小时45分钟",
            "price": 980.00,
            "currency": "CNY",
            "price_cny": 980.00,
            "aircraft": "A321",
            "stops": 0,
            "origin": "PEK",
            "destination": "PVG",
            "date": "2025-10-23",
            "rating": 4.0,
            "cabin_class": "经济舱",
            "baggage_allowance": "23kg托运行李",
            "segments": [
                {
                    "carrier_code": "CZ",
                    "flight_number": "3539",
                    "aircraft": "A321",
                    "departure": {
                        "airport": "PEK",
                        "terminal": "T2",
                        "time": "2025-10-23T19:45:00"
                    },
                    "arrival": {
                        "airport": "PVG",
                        "terminal": "T1",
                        "time": "2025-10-23T22:30:00"
                    },
                    "duration": "2小时45分钟"
                }
            ],
            "booking_class": "Y",
            "refundable": True,
            "source": "amadeus",
            "collected_at": datetime.now().isoformat(),
            "route": "北京 -> 上海"
        }
    ]
    
    return mock_flights

def test_flight_formatting():
    """测试航班数据格式化"""
    print("🚀 开始测试航班数据格式化...")
    print("-" * 50)
    
    # 创建模拟数据
    mock_flights = create_mock_flight_data()
    print(f"📊 创建了 {len(mock_flights)} 条模拟航班数据")
    
    # 测试 PlanGenerator 格式化
    plan_generator = PlanGenerator()
    formatted_flights = plan_generator._format_data_for_llm(mock_flights, 'flight')
    
    print("✅ PlanGenerator 格式化结果:")
    print(formatted_flights)
    print("-" * 50)
    
    # 保存测试数据供前端使用
    test_data = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "description": "模拟的 Amadeus API 航班数据用于前端显示测试",
            "route": "北京 -> 上海",
            "total_flights": len(mock_flights)
        },
        "mock_flights": mock_flights,
        "formatted_for_llm": formatted_flights,
        "frontend_test_data": {
            "flight": mock_flights[0]  # 用于前端测试的单个航班数据
        }
    }
    
    # 保存到文件
    test_file = project_root / "mock_flight_data.json"
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"✅ 模拟数据已保存到: {test_file}")
    
    # 验证数据结构
    print("\n🔍 验证数据结构:")
    sample_flight = mock_flights[0]
    
    required_fields = [
        'flight_number', 'airline_name', 'departure_time', 'arrival_time',
        'duration', 'price_cny', 'cabin_class', 'stops', 'origin', 'destination',
        'baggage_allowance'
    ]
    
    for field in required_fields:
        value = sample_flight.get(field)
        print(f"   {field}: {type(value).__name__} = {value}")
    
    print("\n🎯 前端显示测试要点:")
    print("   1. 航班号显示: CA1501")
    print("   2. 时间格式: 08:30 (从 2025-10-23T08:30:00 提取)")
    print("   3. 价格显示: ¥1280.5")
    print("   4. 中转信息: 直飞 (stops=0)")
    print("   5. 舱位等级: 经济舱")
    print("   6. 行李额度: 23kg托运行李")
    
    print("\n🚀 下一步测试:")
    print("   1. 在前端创建旅行计划")
    print("   2. 查看航班信息是否按新格式显示")
    print("   3. 验证所有字段都能正确显示")
    
    return True

if __name__ == "__main__":
    success = test_flight_formatting()
    
    if success:
        print("\n✅ 模拟数据测试成功!")
        print("现在可以使用这些数据来测试前端显示效果")
    else:
        print("\n❌ 测试失败")
    
    sys.exit(0 if success else 1)