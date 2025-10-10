"""
旅行计划相关任务
"""

from celery import current_task
from app.core.celery import celery_app
from app.services.agent_service import AgentService
from app.core.database import AsyncSessionLocal
from loguru import logger


@celery_app.task(bind=True)
def generate_travel_plans_task(self, plan_id: int, preferences: dict = None, requirements: dict = None):
    """生成旅行方案任务"""
    try:
        logger.info(f"开始执行生成旅行方案任务，计划ID: {plan_id}")
        
        # 更新任务状态
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "开始生成方案..."}
        )
        
        # 创建数据库会话
        async def run_generation():
            async with AsyncSessionLocal() as db:
                agent_service = AgentService(db)
                
                # 更新进度
                self.update_state(
                    state="PROGRESS",
                    meta={"current": 20, "total": 100, "status": "收集数据中..."}
                )
                
                # 生成方案
                success = await agent_service.generate_travel_plans(
                    plan_id, preferences, requirements
                )
                
                if success:
                    self.update_state(
                        state="SUCCESS",
                        meta={"current": 100, "total": 100, "status": "方案生成完成"}
                    )
                    return {"status": "success", "plan_id": plan_id}
                else:
                    self.update_state(
                        state="FAILURE",
                        meta={"current": 0, "total": 100, "status": "方案生成失败"}
                    )
                    return {"status": "failed", "plan_id": plan_id}
        
        # 运行异步任务
        import asyncio
        return asyncio.run(run_generation())
        
    except Exception as e:
        logger.error(f"生成旅行方案任务失败: {e}")
        self.update_state(
            state="FAILURE",
            meta={"current": 0, "total": 100, "status": f"任务失败: {str(e)}"}
        )
        raise


@celery_app.task
def refine_travel_plan_task(plan_id: int, plan_index: int, refinements: dict):
    """细化旅行方案任务"""
    try:
        logger.info(f"开始执行细化方案任务，计划ID: {plan_id}")
        
        async def run_refinement():
            async with AsyncSessionLocal() as db:
                agent_service = AgentService(db)
                
                success = await agent_service.refine_plan(
                    plan_id, plan_index, refinements
                )
                
                return {"status": "success" if success else "failed", "plan_id": plan_id}
        
        import asyncio
        return asyncio.run(run_refinement())
        
    except Exception as e:
        logger.error(f"细化方案任务失败: {e}")
        raise


@celery_app.task
def export_travel_plan_task(plan_id: int, format: str):
    """导出旅行计划任务"""
    try:
        logger.info(f"开始执行导出任务，计划ID: {plan_id}, 格式: {format}")
        
        # 这里应该实现具体的导出逻辑
        # 例如：生成PDF、HTML、JSON等格式的文件
        
        return {
            "status": "success",
            "plan_id": plan_id,
            "format": format,
            "download_url": f"/downloads/plan_{plan_id}.{format}"
        }
        
    except Exception as e:
        logger.error(f"导出任务失败: {e}")
        raise
