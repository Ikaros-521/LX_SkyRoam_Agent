#!/usr/bin/env python3
"""
测试交通数据收集
"""

import asyncio
import sys
import os
import json
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.tools.mcp_client import MCPClient

# 加载.env环境变量
load_dotenv()

async def test_transportation():
    """测试交通数据收集"""
    print("测试交通数据收集...")
    
    try:
        client = MCPClient()
        
        # 测试交通数据获取
        departure = "杭州"
        destination = "桐乡"
        
        print(f"测试路线: {departure} -> {destination}")
        
        transportation = await client.get_transportation(departure, destination)
        
        print(f"获取到 {len(transportation)} 条交通数据")
        for i, item in enumerate(transportation):
            print(f"  交通 {i+1}:")
            print(f"    类型: {item.get('type', 'N/A')}")
            print(f"    名称: {item.get('name', 'N/A')}")
            print(f"    描述: {item.get('description', 'N/A')}")
            print(f"    距离: {item.get('distance', 0)} 公里")
            print(f"    时间: {item.get('duration', 0)} 分钟")
            print(f"    来源: {item.get('source', 'N/A')}")
            print()
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_transportation())
