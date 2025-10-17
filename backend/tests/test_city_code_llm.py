#!/usr/bin/env python3
"""
LLM城市代码识别功能测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.tools.mcp_client import MCPClient
from app.core.config import settings

async def test_city_code_recognition():
    """测试LLM城市代码识别功能"""
    print("=" * 60)
    print("LLM城市代码识别功能测试")
    print("=" * 60)
    
    # 检查OpenAI配置
    print("\n1. 检查OpenAI配置...")
    print(f"OpenAI API Key: {'已配置' if settings.OPENAI_API_KEY else '未配置'}")
    print(f"OpenAI API Base: {settings.OPENAI_API_BASE}")
    print(f"OpenAI Model: {settings.OPENAI_MODEL}")
    
    if not settings.OPENAI_API_KEY:
        print("❌ OpenAI API密钥未配置，无法测试LLM功能")
        return False
    
    # 创建MCP客户端
    print("\n2. 创建MCP客户端...")
    client = MCPClient()
    
    # 测试城市代码识别
    print("\n3. 测试城市代码识别...")
    
    # 测试城市列表（包括硬编码的和需要LLM识别的）
    test_cities = [
        # 硬编码映射中存在的城市
        "北京", "上海", "广州", "深圳", "纽约", "伦敦", "巴黎", "东京",
        # 硬编码映射中不存在的城市（需要LLM识别）
        "连云港", "西湖", "苏州", "无锡", "常州", "南通", "扬州", "镇江",
        "泰州", "盐城", "淮安", "宿迁", "徐州", "温州", "嘉兴", "湖州",
        "绍兴", "金华", "衢州", "舟山", "台州", "丽水"
    ]
    
    results = {}
    
    for city in test_cities:
        try:
            print(f"\n  测试城市: {city}")
            
            # 首先测试硬编码映射
            hardcoded_result = client._get_city_code(city)
            print(f"    硬编码映射: {hardcoded_result}")
            
            # 然后测试智能识别（包含LLM）
            smart_result = await client.get_city_code(city)
            print(f"    智能识别: {smart_result}")
            
            results[city] = {
                "hardcoded": hardcoded_result,
                "smart": smart_result,
                "llm_used": hardcoded_result is None and smart_result is not None
            }
            
        except Exception as e:
            print(f"    ❌ 测试失败: {e}")
            results[city] = {
                "hardcoded": None,
                "smart": None,
                "error": str(e)
            }
    
    # 统计结果
    print("\n4. 测试结果统计...")
    total_cities = len(test_cities)
    hardcoded_success = sum(1 for r in results.values() if r.get("hardcoded"))
    smart_success = sum(1 for r in results.values() if r.get("smart"))
    llm_success = sum(1 for r in results.values() if r.get("llm_used"))
    
    print(f"  总测试城市数: {total_cities}")
    print(f"  硬编码映射成功: {hardcoded_success}")
    print(f"  智能识别成功: {smart_success}")
    print(f"  LLM识别成功: {llm_success}")
    print(f"  总体成功率: {smart_success/total_cities*100:.1f}%")
    
    # 显示LLM识别的城市
    if llm_success > 0:
        print("\n5. LLM成功识别的城市:")
        for city, result in results.items():
            if result.get("llm_used"):
                print(f"  {city} -> {result['smart']}")
    
    # 显示失败的城市
    failed_cities = [city for city, result in results.items() if not result.get("smart")]
    if failed_cities:
        print("\n6. 识别失败的城市:")
        for city in failed_cities:
            print(f"  {city}")
    
    # 显示缓存状态
    print(f"\n7. 城市代码缓存状态:")
    print(f"  缓存条目数: {len(client.city_code_cache)}")
    if client.city_code_cache:
        print("  缓存内容:")
        for city, code in client.city_code_cache.items():
            print(f"    {city} -> {code}")
    
    print("\n" + "=" * 60)
    if smart_success > hardcoded_success:
        print("✅ LLM城市代码识别功能测试成功！")
        print(f"智能识别比硬编码映射多识别了 {smart_success - hardcoded_success} 个城市")
        return True
    else:
        print("⚠️  LLM功能可能未正常工作，但硬编码映射正常")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_city_code_recognition())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)