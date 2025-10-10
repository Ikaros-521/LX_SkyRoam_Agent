"""
AI Agent API端点
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from app.core.database import get_async_db
from app.services.agent_service import AgentService

router = APIRouter()


@router.post("/generate-plan/{plan_id}")
async def generate_travel_plan(
    plan_id: int,
    preferences: Optional[Dict[str, Any]] = None,
    requirements: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db)
):
    """生成旅行方案"""
    agent_service = AgentService(db)
    
    # 启动后台任务
    background_tasks.add_task(
        agent_service.generate_travel_plans,
        plan_id,
        preferences,
        requirements
    )
    
    return {
        "message": "旅行方案生成任务已启动",
        "plan_id": plan_id,
        "status": "generating"
    }


@router.post("/refine-plan/{plan_id}")
async def refine_travel_plan(
    plan_id: int,
    plan_index: int,
    refinements: Dict[str, Any],
    db: AsyncSession = Depends(get_async_db)
):
    """细化旅行方案"""
    agent_service = AgentService(db)
    
    success = await agent_service.refine_plan(plan_id, plan_index, refinements)
    if not success:
        raise HTTPException(status_code=400, detail="细化方案失败")
    
    return {"message": "方案细化成功"}


@router.get("/recommendations/{plan_id}")
async def get_plan_recommendations(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """获取方案推荐"""
    agent_service = AgentService(db)
    
    recommendations = await agent_service.get_plan_recommendations(plan_id)
    
    return {
        "plan_id": plan_id,
        "recommendations": recommendations
    }
