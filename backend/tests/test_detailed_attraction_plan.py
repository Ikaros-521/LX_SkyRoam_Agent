#!/usr/bin/env python3
"""
测试优化后的景点方案生成，查看是否包含更多小红书攻略细节
"""

import asyncio
import json
import logging
from app.services.plan_generator import PlanGenerator
from app.services.data_collector import DataCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class MockPlan:
    def __init__(self):
        self.destination = "北京"
        self.duration_days = 3
        self.travelers = 2
        self.ageGroups = ["成年人"]
        self.budget = 5000
        self.requirements = "希望体验当地文化和美食"

async def test_detailed_attraction_plan():
    """测试详细的景点方案生成"""
    logger.info("=== 测试优化后的景点方案生成 ===")
    
    try:
        # 创建服务实例
        plan_generator = PlanGenerator()
        data_collector = plan_generator.data_collector
        
        # 创建模拟计划
        plan = MockPlan()
        
        # 模拟景点数据
        attractions_data = [
            {
                "name": "故宫博物院",
                "category": "历史文化",
                "description": "明清两代的皇家宫殿",
                "price": 60,
                "rating": 4.8,
                "address": "北京市东城区景山前街4号",
                "opening_hours": "08:30-17:00",
                "visit_time": "3-4小时",
                "tags": ["历史", "文化", "必游"]
            },
            {
                "name": "天安门广场",
                "category": "历史文化", 
                "description": "世界最大的城市广场",
                "price": 0,
                "rating": 4.7,
                "address": "北京市东城区东长安街",
                "opening_hours": "全天开放",
                "visit_time": "1-2小时",
                "tags": ["历史", "免费", "必游"]
            },
            {
                "name": "颐和园",
                "category": "园林景观",
                "description": "中国古典园林之首",
                "price": 30,
                "rating": 4.6,
                "address": "北京市海淀区新建宫门路19号",
                "opening_hours": "06:30-18:00",
                "visit_time": "3-4小时",
                "tags": ["园林", "历史", "自然"]
            }
        ]
        
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
                }
            ]
        }
        
        logger.info("开始生成详细景点方案...")
        
        # 生成景点方案
        attraction_plans = await plan_generator._generate_attraction_plans(
            attractions_data, plan, None, raw_data
        )
        
        if attraction_plans:
            logger.info(f"成功生成 {len(attraction_plans)} 天的景点方案")
            
            # 详细输出每天的方案
            for day_plan in attraction_plans:
                logger.info(f"\n=== 第{day_plan.get('day', '?')}天方案 ===")
                logger.info(f"日期: {day_plan.get('date', 'N/A')}")
                
                # 输出时间安排
                if 'schedule' in day_plan:
                    logger.info("时间安排:")
                    for schedule in day_plan['schedule']:
                        logger.info(f"  {schedule.get('time', 'N/A')}: {schedule.get('location', 'N/A')}")
                        logger.info(f"    活动: {schedule.get('description', 'N/A')}")
                        logger.info(f"    建议: {schedule.get('tips', 'N/A')}")
                        logger.info(f"    费用: {schedule.get('cost', 0)}元")
                
                # 输出景点详情
                if 'attractions' in day_plan:
                    logger.info("景点详情:")
                    for attraction in day_plan['attractions']:
                        logger.info(f"  景点: {attraction.get('name', 'N/A')}")
                        logger.info(f"    最佳游览时间: {attraction.get('best_visit_time', 'N/A')}")
                        logger.info(f"    亮点: {attraction.get('highlights', [])}")
                        logger.info(f"    拍照点: {attraction.get('photography_spots', [])}")
                        if 'route_tips' in attraction:
                            logger.info(f"    路线建议: {attraction.get('route_tips', 'N/A')}")
                        if 'experience_tips' in attraction:
                            logger.info(f"    体验建议: {attraction.get('experience_tips', [])}")
                
                # 输出当日建议
                if 'daily_tips' in day_plan:
                    logger.info(f"当日建议: {day_plan['daily_tips']}")
                
                logger.info(f"当日费用: {day_plan.get('estimated_cost', 0)}元")
        else:
            logger.error("景点方案生成失败")
            
        logger.info("测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_detailed_attraction_plan())