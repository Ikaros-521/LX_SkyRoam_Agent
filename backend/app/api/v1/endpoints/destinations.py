"""
目的地API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_async_db
from app.models.destination import Destination, Attraction, Restaurant

router = APIRouter()


@router.get("/")
async def get_destinations(
    skip: int = 0,
    limit: int = 100,
    country: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """获取目的地列表"""
    from sqlalchemy import select
    
    query = select(Destination)
    if country:
        query = query.where(Destination.country == country)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    destinations = result.scalars().all()
    
    return destinations


@router.get("/{destination_id}")
async def get_destination(
    destination_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """获取单个目的地详情"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(Destination)
        .options(
            selectinload(Destination.attractions),
            selectinload(Destination.restaurants)
        )
        .where(Destination.id == destination_id)
    )
    destination = result.scalar_one_or_none()
    
    if not destination:
        raise HTTPException(status_code=404, detail="目的地不存在")
    
    return destination


@router.get("/{destination_id}/attractions")
async def get_destination_attractions(
    destination_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db)
):
    """获取目的地景点列表"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Attraction)
        .where(Attraction.destination_id == destination_id)
        .offset(skip)
        .limit(limit)
    )
    attractions = result.scalars().all()
    
    return attractions


@router.get("/{destination_id}/restaurants")
async def get_destination_restaurants(
    destination_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db)
):
    """获取目的地餐厅列表"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Restaurant)
        .where(Restaurant.destination_id == destination_id)
        .offset(skip)
        .limit(limit)
    )
    restaurants = result.scalars().all()
    
    return restaurants
