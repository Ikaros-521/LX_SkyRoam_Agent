#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用真实小红书数据测试旅行方案生成
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.plan_generator import PlanGenerator
from app.platforms.xhs.playwright_crawler import PlaywrightXHSCrawler
from app.core.config import settings

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

class MockPlan:
    def __init__(self):
        self.destination = "北京"
        self.duration_days = 3
        self.start_date = "2024-01-15"
        self.end_date = "2024-01-17"
        self.budget = 5000
        self.departure = "上海"
        self.travelers = 2
        self.ageGroups = ["成年人"]
        self.transportation = "飞机"
        self.requirements = "希望体验当地文化和美食"

async def test_real_xiaohongshu_plan_generation():
    """测试使用真实小红书数据的旅行方案生成"""
    
    logger.info("=== 真实小红书数据驱动的旅行方案生成测试 ===")
    
    # 1. 首先获取真实的小红书数据
    logger.info("正在获取真实的小红书数据...")
    crawler = PlaywrightXHSCrawler()
    
    try:
        # 获取北京相关的小红书笔记
        xiaohongshu_notes = await crawler.search_notes("北京旅游攻略", max_notes=5)
        logger.info(f"成功获取 {len(xiaohongshu_notes)} 条小红书笔记")
        
        # 显示获取到的笔记信息
        for i, note in enumerate(xiaohongshu_notes, 1):
            logger.info(f"笔记 {i}:")
            logger.info(f"  标题: {note.get('title', 'N/A')}")
            logger.info(f"  作者: {note.get('author', 'N/A')}")
            logger.info(f"  点赞数: {note.get('likes', 0)}")
            logger.info(f"  描述长度: {len(note.get('description', ''))}")
            logger.info(f"  描述预览: {note.get('description', '')[:100]}...")
            logger.info("")
        
    except Exception as e:
        logger.error(f"获取小红书数据失败: {e}")
        # 使用备用的模拟数据
        xiaohongshu_notes = [
            {
                "title": "北京故宫深度游攻略！这样玩才不虚此行",
                "author": "旅行达人小李",
                "likes": 1250,
                "description": "故宫真的太震撼了！建议早上8点半开门就进去，人少拍照好看。一定要去珍宝馆和钟表馆，虽然要额外买票但绝对值得。午门进，神武门出，这样走路线最顺。记得带充电宝，拍照太费电了！推荐租个讲解器，能了解更多历史故事。最佳拍照点：太和殿前、御花园、角楼。避开节假日，工作日去体验更好。"
            }
        ]
        logger.info("使用备用模拟数据")
    
    finally:
        await crawler.close()
    
    # 2. 准备模拟的地图数据
    processed_data = {
        "attractions": [
            {
                "name": "故宫博物院",
                "type": "历史文化",
                "description": "明清两代的皇家宫殿",
                "price": 60,
                "rating": 4.8,
                "address": "北京市东城区景山前街4号",
                "opening_hours": "08:30-17:00",
                "duration": "3-4小时",
                "tags": ["历史", "文化", "必游"]
            },
            {
                "name": "天安门广场",
                "type": "历史文化", 
                "description": "世界最大的城市广场",
                "price": 0,
                "rating": 4.7,
                "address": "北京市东城区东长安街",
                "opening_hours": "全天开放",
                "duration": "1-2小时",
                "tags": ["历史", "免费", "必游"]
            },
            {
                "name": "颐和园",
                "type": "园林景观",
                "description": "中国古典园林之首",
                "price": 30,
                "rating": 4.6,
                "address": "北京市海淀区新建宫门路19号",
                "opening_hours": "06:30-18:00",
                "duration": "3-4小时",
                "tags": ["园林", "历史", "自然"]
            }
        ],
        "hotels": [
            {
                "name": "北京王府井希尔顿酒店",
                "price_per_night": 800,
                "rating": 4.5,
                "address": "北京市东城区王府井大街8号",
                "amenities": ["免费WiFi", "健身房", "餐厅"]
            }
        ],
        "flights": [
            {
                "airline": "中国国航",
                "departure_time": "08:00",
                "arrival_time": "10:30",
                "price": 1200,
                "rating": 4.2
            }
        ],
        "restaurants": [
            {
                "name": "全聚德烤鸭店",
                "cuisine": "北京菜",
                "price_range": "200-300",
                "rating": 4.3,
                "address": "北京市东城区前门大街30号"
            }
        ],
        "transportation": [
            {
                "type": "地铁",
                "name": "北京地铁",
                "description": "北京市轨道交通系统",
                "price": 3,
                "operating_hours": "05:00-23:30"
            }
        ]
    }
    
    # 3. 准备包含真实小红书数据的raw_data
    raw_data = {
        "xiaohongshu_notes": xiaohongshu_notes
    }
    
    # 4. 创建模拟计划并生成方案
    plan = MockPlan()
    
    try:
        logger.info("开始生成基于真实小红书数据的旅行方案...")
        
        # 创建方案生成器
        generator = PlanGenerator()
        
        # 生成方案
        plans = await generator.generate_plans(
            processed_data=processed_data,
            plan=plan,
            preferences={"focus": "文化深度型"},
            raw_data=raw_data
        )
        
        logger.info(f"成功生成 {len(plans)} 个旅行方案")
        
        # 显示生成的方案详情
        for i, plan_data in enumerate(plans, 1):
            logger.info(f"\n=== 方案 {i}: {plan_data.get('title', 'N/A')} ===")
            logger.info(f"类型: {plan_data.get('type', 'N/A')}")
            logger.info(f"描述: {plan_data.get('description', 'N/A')}")
            
            # 显示每日行程
            daily_itineraries = plan_data.get('daily_itineraries', [])
            logger.info(f"每日行程数量: {len(daily_itineraries)}")
            
            for day_plan in daily_itineraries:
                day_num = day_plan.get('day', 'N/A')
                date = day_plan.get('date', 'N/A')
                theme = day_plan.get('theme', '无主题')
                
                logger.info(f"\n--- 第{day_num}天 ({date}) - {theme} ---")
                
                # 显示活动（基于小红书数据生成的）
                activities = day_plan.get('activities', [])
                if activities:
                    logger.info("基于小红书数据的活动安排:")
                    for activity in activities:
                        if isinstance(activity, dict):
                            logger.info(f"  {activity.get('time', 'N/A')}: {activity.get('name', 'N/A')}")
                            logger.info(f"    类型: {activity.get('type', 'N/A')}")
                            logger.info(f"    描述: {activity.get('description', 'N/A')[:150]}...")
                            logger.info(f"    费用: {activity.get('estimated_cost', 'N/A')}元")
                        else:
                            logger.info(f"  {activity}")
                else:
                    # 显示传统格式的景点
                    attractions = day_plan.get('attractions', [])
                    if attractions:
                        logger.info("景点安排:")
                        for attraction in attractions:
                            logger.info(f"  - {attraction}")
                
                # 显示餐饮安排
                meals = day_plan.get('meals', [])
                if meals:
                    logger.info("餐饮安排:")
                    for meal in meals:
                        if isinstance(meal, dict):
                            logger.info(f"  {meal.get('time', 'N/A')}: {meal.get('restaurant', 'N/A')}")
                        else:
                            logger.info(f"  {meal}")
                
                # 显示当日费用
                cost = day_plan.get('estimated_cost', 'N/A')
                logger.info(f"当日预估费用: {cost}元")
            
            # 显示总预算
            total_cost = plan_data.get('total_cost', {})
            if isinstance(total_cost, dict):
                total = total_cost.get('total', 'N/A')
            else:
                total = total_cost
            logger.info(f"\n总预算: {total}元")
        
        logger.info("\n✅ 真实小红书数据测试完成！")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数"""
    await test_real_xiaohongshu_plan_generation()

if __name__ == "__main__":
    asyncio.run(main())