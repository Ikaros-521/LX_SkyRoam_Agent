#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修改后的小红书爬虫获取详细笔记内容功能
"""

import asyncio
import sys
import os
import json
import nest_asyncio

# 允许嵌套事件循环
nest_asyncio.apply()

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.platforms.xhs.playwright_crawler import PlaywrightXHSCrawler

async def test_detailed_crawler():
    """测试获取详细笔记内容的功能"""
    print("开始测试小红书爬虫获取详细内容功能...")
    
    crawler = None
    try:
        # 创建爬虫实例
        crawler = PlaywrightXHSCrawler()
        
        # 初始化爬虫
        print("正在初始化爬虫...")
        await crawler.start()
        
        # 测试搜索并获取详细内容
        test_keywords = ["北京故宫"]  # 先测试一个关键词
        
        for keyword in test_keywords:
            print(f"\n{'='*50}")
            print(f"测试关键词: {keyword}")
            print(f"{'='*50}")
            
            try:
                # 搜索笔记
                notes = await crawler.search_notes(keyword, max_notes=3)
                
                if notes:
                    print(f"✅ 成功获取 {len(notes)} 条笔记")
                    
                    # 显示每条笔记的详细信息
                    for i, note in enumerate(notes, 1):
                        print(f"\n--- 笔记 {i} ---")
                        print(f"标题: {note.get('title', 'N/A')}")
                        print(f"作者: {note.get('user_info', {}).get('nickname', 'N/A')}")
                        print(f"点赞数: {note.get('liked_count', 0)}")
                        print(f"描述长度: {len(note.get('desc', ''))}")
                        
                        # 显示描述内容的前200个字符
                        desc = note.get('desc', '')
                        if desc:
                            print(f"描述预览: {desc[:200]}{'...' if len(desc) > 200 else ''}")
                        else:
                            print("描述: 无内容")
                        
                        print(f"URL: {note.get('url', 'N/A')}")
                        
                        # 检查是否获取到了详细内容
                        if len(desc) > 50:
                            print("✅ 成功获取详细描述内容")
                        else:
                            print("⚠️ 描述内容较短，可能未获取到详细内容")
                else:
                    print(f"❌ 未获取到 {keyword} 的笔记")
                    
            except Exception as e:
                print(f"❌ 搜索 {keyword} 失败: {e}")
                continue
        
        print(f"\n{'='*50}")
        print("测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理资源
        if crawler:
            try:
                await crawler.close()
                print("✅ 爬虫已关闭")
            except Exception as e:
                print(f"⚠️ 清理爬虫资源时出错: {e}")

def main():
    """主函数"""
    try:
        # 检查是否已有事件循环
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已有事件循环在运行，创建新任务
            task = asyncio.create_task(test_detailed_crawler())
            return task
        else:
            # 如果没有事件循环，直接运行
            return asyncio.run(test_detailed_crawler())
    except RuntimeError:
        # 如果没有事件循环，创建新的
        return asyncio.run(test_detailed_crawler())

if __name__ == "__main__":
    main()