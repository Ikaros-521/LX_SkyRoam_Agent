#!/usr/bin/env python3
"""
简单的高德地图MCP测试
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载.env环境变量
load_dotenv()

from app.tools.amap_mcp_client import AmapMCPClient

async def simple_test():
    """简单测试"""
    print("=== 高德地图MCP简单测试 ===")
    
    try:
        # 创建客户端
        client = AmapMCPClient()
        print(f"✅ 客户端创建成功")
        print(f"模式: {client.mode}")
        print(f"URL: {client.base_url}")
        print(f"API密钥: {'已配置' if client.api_key else '未配置'}")
        
        if not client.api_key:
            print("❌ API密钥未配置，无法继续测试")
            return
        
        # 测试路线规划
        print("\n=== 测试路线规划 ===")
        routes = await client.get_directions(
            origin="北京",
            destination="上海",
            mode="driving"  # 改为驾车模式
        )
        
        print(f"获取到 {len(routes)} 条路线")
        if routes:
            route = routes[0]
            print(f"第一条路线:")
            print(f"  类型: {route.get('type', 'N/A')}")
            print(f"  名称: {route.get('name', 'N/A')}")
            print(f"  距离: {route.get('distance', 'N/A')}公里")
            print(f"  耗时: {route.get('duration', 'N/A')}分钟")
            print(f"  费用: {route.get('price', 'N/A')}元")
        else:
            print("⚠️ 未获取到路线数据")
        
        # 关闭客户端
        await client.close()
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simple_test())
