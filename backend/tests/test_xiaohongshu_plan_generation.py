#!/usr/bin/env python3
"""
测试基于小红书数据的旅行方案生成功能
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.plan_generator import PlanGenerator
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

async def test_xiaohongshu_plan_generation():
    """测试基于小红书数据的方案生成"""
    logger.info("开始测试基于小红书数据的旅行方案生成...")
    
    # 创建方案生成器
    plan_generator = PlanGenerator()
    
    # 模拟处理后的数据（地图数据）
    processed_data = {
        "attractions": [
            {
                "name": "故宫博物院",
                "category": "历史文化",
                "description": "明清两代的皇家宫殿",
                "price": 60,
                "rating": 4.8,
                "address": "北京市东城区景山前街4号",
                "opening_hours": "08:30-17:00",
                "visit_duration": "3-4小时",
                "tags": ["历史", "文化", "必游"],
                "source": "百度地图"
            },
            {
                "name": "天安门广场",
                "category": "历史文化",
                "description": "世界最大的城市广场",
                "price": 0,
                "rating": 4.7,
                "address": "北京市东城区东长安街",
                "opening_hours": "全天开放",
                "visit_duration": "1-2小时",
                "tags": ["历史", "免费", "必游"],
                "source": "百度地图"
            },
            {
                "name": "颐和园",
                "category": "园林景观",
                "description": "中国古典园林之首",
                "price": 30,
                "rating": 4.6,
                "address": "北京市海淀区新建宫门路19号",
                "opening_hours": "06:30-18:00",
                "visit_duration": "3-4小时",
                "tags": ["园林", "历史", "自然"],
                "source": "百度地图"
            }
        ],
        "hotels": [
            {
                "name": "北京王府井希尔顿酒店",
                "price_per_night": 800,
                "rating": 4.5,
                "address": "北京市东城区王府井大街8号"
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
    
    # 模拟小红书数据
    raw_data = {
        "xiaohongshu_notes": [
            {
                "title": "北京故宫深度游攻略！这样玩才不虚此行",
                "author": "旅行达人小李",
                "liked_count": 1250,
                "desc": "故宫真的太震撼了！建议早上8点半开门就进去，人少拍照好看。一定要去珍宝馆和钟表馆，虽然要额外买票但绝对值得。午门进，神武门出，这样走路线最顺。记得带充电宝，拍照太费电了！推荐租个讲解器，能了解更多历史故事。",
                "location": "北京故宫博物院",
                "tag_list": ["故宫", "历史", "文化", "必游"]
            },
            {
                "title": "天安门看升旗攻略｜凌晨4点起床值得吗？",
                "author": "北京本地人",
                "liked_count": 890,
                "desc": "看升旗真的是一生必体验！夏天4:30开始，冬天要更早。建议提前一晚住在附近，我们住的王府井步行过去15分钟。升旗仪式很庄严，国歌响起的那一刻真的很感动。看完升旗可以去吃个早餐，然后直接去故宫，完美！",
                "location": "北京天安门广场",
                "tag_list": ["天安门", "升旗", "爱国", "体验"]
            },
            {
                "title": "颐和园一日游｜最美的季节和路线推荐",
                "author": "摄影师小王",
                "liked_count": 2100,
                "desc": "颐和园秋天最美！昆明湖的倒影配上红叶绝了。推荐路线：东宫门进→仁寿殿→德和园→乐寿堂→长廊→排云殿→佛香阁→昆明湖→十七孔桥。全程4小时左右。长廊里的彩绘一定要仔细看，每一幅都是艺术品。建议下午去，夕阳西下时在昆明湖边特别美。",
                "location": "北京颐和园",
                "tag_list": ["颐和园", "秋景", "摄影", "路线"]
            },
            {
                "title": "北京美食探店｜除了烤鸭还有这些宝藏小店",
                "author": "美食博主",
                "liked_count": 1680,
                "desc": "来北京不只是吃烤鸭！推荐几家本地人才知道的店：1.护国寺小吃，豆汁焦圈必试 2.老北京炸酱面，地道口味 3.稻香村的点心，伴手礼首选 4.东来顺涮羊肉，百年老店。还有王府井小吃街，虽然游客多但确实有特色小吃。",
                "location": "北京各区美食店",
                "tag_list": ["美食", "小吃", "本地", "推荐"]
            },
            {
                "title": "北京3天2夜完美行程｜第一次来北京必看",
                "author": "旅游规划师",
                "liked_count": 3200,
                "desc": "Day1: 天安门看升旗→故宫深度游→王府井觅食 Day2: 颐和园→圆明园→清华北大外观 Day3: 长城一日游→鸟巢水立方夜景。交通建议办张一卡通，地铁公交都能用。住宿推荐王府井或前门附近，交通方便。每天预算300-500元/人比较合适。",
                "location": "北京全市",
                "tag_list": ["行程", "攻略", "3天", "必看"]
            }
        ]
    }
    
    # 创建模拟计划
    plan = MockPlan()
    
    # 测试方案生成
    try:
        logger.info(f"开始生成{plan.destination}{plan.duration_days}天旅行方案...")
        
        plans = await plan_generator.generate_plans(
            processed_data=processed_data,
            plan=plan,
            preferences={"focus": "文化深度型"},
            raw_data=raw_data
        )
        
        if plans:
            logger.info(f"成功生成{len(plans)}个旅行方案")
            
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
                    
                    # 显示活动
                    activities = day_plan.get('activities', [])
                    if activities:
                        logger.info("活动安排:")
                        for activity in activities:
                            if isinstance(activity, dict):
                                logger.info(f"  {activity.get('time', 'N/A')}: {activity.get('name', 'N/A')}")
                                logger.info(f"    类型: {activity.get('type', 'N/A')}")
                                logger.info(f"    描述: {activity.get('description', 'N/A')[:100]}...")
                                logger.info(f"    费用: {activity.get('estimated_cost', 'N/A')}元")
                            else:
                                logger.info(f"  {activity}")
                    else:
                        # 显示传统格式的景点
                        attractions = day_plan.get('attractions', [])
                        if attractions:
                            logger.info("景点安排:")
                            for attraction in attractions:
                                logger.info(f"  - {attraction.get('name', 'N/A')}")
                    
                    # 显示餐饮
                    meals = day_plan.get('meals', [])
                    if meals:
                        logger.info("餐饮安排:")
                        for meal in meals:
                            logger.info(f"  {meal.get('time', 'N/A')}: {meal.get('name', 'N/A')}")
                            if 'description' in meal:
                                logger.info(f"    {meal['description']}")
                    
                    # 显示预估费用
                    cost = day_plan.get('total_estimated_cost', day_plan.get('estimated_cost', 'N/A'))
                    logger.info(f"当日预估费用: {cost}元")
                
                # 显示总费用
                total_cost = plan_data.get('total_cost', {})
                if total_cost:
                    logger.info(f"\n总预算: {total_cost.get('total', 'N/A')}元")
        else:
            logger.warning("未生成任何方案")
            
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数"""
    logger.info("=== 小红书数据驱动的旅行方案生成测试 ===")
    await test_xiaohongshu_plan_generation()
    logger.info("测试完成")

if __name__ == "__main__":
    asyncio.run(main())