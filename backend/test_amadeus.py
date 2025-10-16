#!/usr/bin/env python3
"""
Amadeus API集成测试脚本
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.tools.mcp_client import MCPClient
from app.core.config import settings

async def test_amadeus_integration():
    """测试Amadeus API集成功能"""
    print("=" * 60)
    print("Amadeus API集成测试")
    print("=" * 60)
    
    # 检查配置
    print("\n1. 检查配置...")
    print(f"Amadeus Client ID: {settings.AMADEUS_CLIENT_ID[:10]}..." if settings.AMADEUS_CLIENT_ID else "未配置")
    print(f"Amadeus Client Secret: {'已配置' if settings.AMADEUS_CLIENT_SECRET else '未配置'}")
    print(f"Amadeus API Base: {settings.AMADEUS_API_BASE}")
    print(f"Amadeus Token URL: {settings.AMADEUS_TOKEN_URL}")
    
    if not settings.AMADEUS_CLIENT_ID or not settings.AMADEUS_CLIENT_SECRET:
        print("\n❌ Amadeus API凭据未配置，请检查环境变量")
        return False
    
    # 创建MCP客户端
    print("\n2. 创建MCP客户端...")
    client = MCPClient()
    
    # 测试OAuth2令牌获取
    print("\n3. 测试OAuth2令牌获取...")
    try:
        token = await client._get_amadeus_token()
        if token:
            print(f"✅ 成功获取访问令牌: {token[:20]}...")
        else:
            print("❌ 获取访问令牌失败")
            return False
    except Exception as e:
        print(f"❌ 获取访问令牌异常: {e}")
        import traceback
        print(f"详细错误信息: {traceback.format_exc()}")
        return False
    
    # 测试城市代码映射
    print("\n4. 测试城市代码映射...")
    test_cities = ["北京", "上海", "广州", "深圳", "纽约", "伦敦", "巴黎", "东京"]
    for city in test_cities:
        code = client._get_city_code(city)
        print(f"  {city} -> {code}")
    
    # 测试航班搜索
    print("\n5. 测试航班搜索...")
    
    # 计算明天的日期
    tomorrow_date = datetime.now() + timedelta(days=1)
    
    test_params = {
        "origin": "北京",
        "destination": "上海", 
        "departure_date": tomorrow_date.date(),
        "return_date": tomorrow_date.date()  # 单程票，返回日期设为同一天
    }
    
    print(f"搜索参数: {test_params}")
    
    try:
        flights = await client.get_flights(**test_params)
        
        if flights:
            print(f"✅ 成功获取 {len(flights)} 条航班信息")
            
            # 显示前3条航班信息
            for i, flight in enumerate(flights[:3]):
                print(f"\n航班 {i+1}:")
                print(f"  航班号: {flight.get('flight_number', 'N/A')}")
                print(f"  航空公司: {flight.get('airline_name', flight.get('airline', 'N/A'))}")
                print(f"  出发时间: {flight.get('departure_time', 'N/A')}")
                print(f"  到达时间: {flight.get('arrival_time', 'N/A')}")
                print(f"  飞行时间: {flight.get('duration', 'N/A')}")
                print(f"  价格: {flight.get('price', 'N/A')} {flight.get('currency', '')}")
                print(f"  人民币价格: ¥{flight.get('price_cny', 'N/A')}")
                print(f"  舱位等级: {flight.get('cabin_class', 'N/A')}")
                print(f"  中转次数: {flight.get('stops', 0)}")
                print(f"  行李额度: {flight.get('baggage_allowance', 'N/A')}")
        else:
            print("❌ 未获取到航班信息")
            return False
            
    except Exception as e:
        print(f"❌ 航班搜索异常: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ Amadeus API集成测试完成")
    print("=" * 60)
    return True

async def main():
    """主函数"""
    try:
        success = await test_amadeus_integration()
        if success:
            print("\n🎉 所有测试通过！")
            sys.exit(0)
        else:
            print("\n❌ 测试失败！")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())