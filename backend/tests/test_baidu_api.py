#!/usr/bin/env python3
"""
测试百度地图API配置和调用
"""

import os
import json
import asyncio
from app.tools.baidu_maps_integration import map_directions
from app.core.config import settings

async def test_api():
    # 检查API密钥配置
    print('BAIDU_MAPS_API_KEY环境变量:', os.environ.get('BAIDU_MAPS_API_KEY', '未设置'))
    print('settings.BAIDU_MAPS_API_KEY:', settings.BAIDU_MAPS_API_KEY or '未设置')
    
    # 测试API调用
    try:
        print('\n尝试调用百度地图API...')
        result = await map_directions('北京', '上海', 'driving', 'true')
        print('成功结果:', json.dumps(result, ensure_ascii=False, indent=2)[:200]+'...')
    except Exception as e:
        print('错误信息:', str(e))
        # 打印更详细的错误信息
        import traceback
        print('\n详细错误信息:')
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())