"""
OpenAI配置相关API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import asyncio

from app.core.database import get_async_db
from app.tools.openai_client import openai_client

router = APIRouter()


@router.get("/config")
async def get_openai_config():
    """获取OpenAI配置信息"""
    try:
        config = openai_client.get_client_info()
        return {
            "status": "success",
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/test")
async def test_openai_connection():
    """测试OpenAI连接"""
    try:
        # 测试简单的文本生成
        response = await openai_client.generate_text(
            prompt="请简单介绍一下你自己",
            max_tokens=100
        )
        
        return {
            "status": "success",
            "message": "OpenAI连接测试成功",
            "response": response,
            "config": openai_client.get_client_info()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"OpenAI连接测试失败: {str(e)}",
            "config": openai_client.get_client_info()
        }


@router.post("/generate-plan")
async def generate_ai_plan(
    destination: str,
    duration_days: int,
    budget: float,
    preferences: list,
    requirements: str = ""
):
    """使用AI生成旅行计划"""
    try:
        plan = await openai_client.generate_travel_plan(
            destination=destination,
            duration_days=duration_days,
            budget=budget,
            preferences=preferences,
            requirements=requirements
        )
        
        return {
            "status": "success",
            "plan": plan
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成计划失败: {str(e)}")


@router.post("/analyze-data")
async def analyze_travel_data(
    data: Dict[str, Any],
    analysis_type: str = "comprehensive"
):
    """分析旅行数据"""
    try:
        analysis = await openai_client.analyze_travel_data(
            data=data,
            analysis_type=analysis_type
        )
        
        return {
            "status": "success",
            "analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据分析失败: {str(e)}")


@router.post("/optimize-plan")
async def optimize_travel_plan(
    current_plan: Dict[str, Any],
    optimization_goals: list
):
    """优化旅行计划"""
    try:
        optimized_plan = await openai_client.optimize_travel_plan(
            current_plan=current_plan,
            optimization_goals=optimization_goals
        )
        
        return {
            "status": "success",
            "optimized_plan": optimized_plan
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计划优化失败: {str(e)}")
