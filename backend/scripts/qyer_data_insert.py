#!/usr/bin/env python3
"""
穷游网数据导入脚本
将爬取的景点数据导入到数据库中
"""

import asyncio
import sys
import os
import json
import re
from typing import Dict, List, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_async_session_local
from app.core.logging_config import setup_logging
from app.models.attraction_detail import AttractionDetail
from loguru import logger


def clean_text(text: str) -> str:
    """清理文本：去除空格和换行"""
    if not text:
        return ""
    # 去除所有空白字符（空格、换行、制表符等）
    cleaned = re.sub(r'\s+', '', text)
    return cleaned.strip()


def clean_address(address: str) -> str:
    """清理地址：去除(查看地图)等多余文字"""
    if not address:
        return ""
    # 去除 (查看地图) 及其变体
    cleaned = re.sub(r'\(查看地图\)', '', address, flags=re.IGNORECASE)
    cleaned = re.sub(r'\(查看地圖\)', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def parse_data(data: List[Dict[str, Any]], destination: str = "杭州", city: str = "杭州市") -> List[Dict[str, Any]]:
    """
    解析穷游网数据，按景点名称分组
    
    Args:
        data: 原始数据列表
        destination: 目的地
        city: 城市
        
    Returns:
        解析后的景点数据列表
    """
    # 按标题分组数据
    grouped_data: Dict[str, Dict[str, Any]] = {}
    
    for item in data:
        title = clean_text(item.get("标题", ""))
        if not title:
            continue
        
        # 初始化景点数据
        if title not in grouped_data:
            grouped_data[title] = {
                "name": title,
                "destination": destination,
                "city": city,
                "image_url": item.get("图片", ""),
                "address": None,
                "opening_hours_text": None,
                "price_note": None,
                "phone": None,
                "website": None,
                "level": item.get("级别", ""),  # 评分级别，可以存到extra_info
                "review_count": None,  # 点评数，可以存到extra_info
            }
        
        # 获取数据名和内容
        data_name = clean_text(item.get("数据名", ""))
        content = item.get("内容", "").strip()
        
        if not content:
            continue
        
        # 根据数据名分类处理
        if "地址" in data_name:
            grouped_data[title]["address"] = clean_address(content)
        elif "开放时间" in data_name or "开放時間" in data_name:
            grouped_data[title]["opening_hours_text"] = content
        elif "门票" in data_name:
            # 门票存到price_note
            if grouped_data[title]["price_note"]:
                grouped_data[title]["price_note"] += f"；{content}"
            else:
                grouped_data[title]["price_note"] = content
        elif "电话" in data_name or "電話" in data_name:
            grouped_data[title]["phone"] = content
        elif "到达方式" in data_name or "到達方式" in data_name:
            # 到达方式可以存到extra_info
            if "extra_info" not in grouped_data[title]:
                grouped_data[title]["extra_info"] = {}
            grouped_data[title]["extra_info"]["transportation"] = content
        
        # 提取点评数
        dping_text = item.get("dping", "")
        if dping_text:
            match = re.search(r'(\d+)', dping_text)
            if match:
                grouped_data[title]["review_count"] = int(match.group(1))
    
    # 转换为列表
    result = []
    for title, att_data in grouped_data.items():
        # 处理extra_info
        extra_info = att_data.pop("extra_info", {})
        level = att_data.pop("level", None)
        review_count = att_data.pop("review_count", None)
        
        if level:
            extra_info["rating_level"] = level
        if review_count:
            extra_info["review_count"] = review_count
        
        if extra_info:
            att_data["extra_info"] = extra_info
        
        # 移除None值的字段
        cleaned_data = {k: v for k, v in att_data.items() if v is not None}
        result.append(cleaned_data)
    
    return result


async def insert_attraction_details(data_file: str, destination: str = "杭州", city: str = "杭州市", dry_run: bool = False):
    """
    导入景点详细信息到数据库
    
    Args:
        data_file: JSON数据文件路径
        destination: 目的地
        city: 城市
        dry_run: 是否只是预览不实际插入
    """
    # 读取JSON文件
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        logger.info(f"✅ 成功读取数据文件: {data_file}，共 {len(raw_data)} 条原始记录")
    except Exception as e:
        logger.error(f"❌ 读取数据文件失败: {e}")
        return
    
    # 解析数据
    parsed_data = parse_data(raw_data, destination=destination, city=city)
    logger.info(f"✅ 解析完成，共 {len(parsed_data)} 个景点")
    
    # 预览数据
    logger.info("\n📋 预览前5个景点数据:")
    for i, item in enumerate(parsed_data[:5], 1):
        logger.info(f"\n{i}. {item.get('name', '')}")
        address = item.get('address') or ''
        opening_hours = item.get('opening_hours_text') or ''
        price_note = item.get('price_note') or ''
        image_url = item.get('image_url') or ''
        logger.info(f"   地址: {address}")
        logger.info(f"   开放时间: {opening_hours}")
        logger.info(f"   门票: {price_note}")
        logger.info(f"   图片: {image_url}")
    
    if dry_run:
        logger.info("\n🔍 预览模式，不实际插入数据")
        return
    
    # 插入数据库
    async_session_factory = get_async_session_local()
    created_count = 0
    updated_count = 0
    skipped_count = 0
    
    async with async_session_factory() as db:
        try:
            from sqlalchemy import select
            
            for item in parsed_data:
                name = item.get("name")
                if not name:
                    continue
                
                # 检查是否已存在（根据名称和目的地）
                result = await db.execute(
                    select(AttractionDetail).where(
                        AttractionDetail.name == name,
                        AttractionDetail.destination == destination
                    )
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # 更新现有记录
                    for key, value in item.items():
                        if key not in ["name", "destination"] and value is not None:
                            setattr(existing, key, value)
                    updated_count += 1
                    logger.debug(f"更新: {name}")
                else:
                    # 创建新记录
                    new_detail = AttractionDetail(**item)
                    db.add(new_detail)
                    created_count += 1
                    logger.debug(f"创建: {name}")
            
            await db.commit()
            logger.info(f"\n✅ 导入完成！")
            logger.info(f"   创建: {created_count} 条")
            logger.info(f"   更新: {updated_count} 条")
            logger.info(f"   跳过: {skipped_count} 条")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ 导入失败: {e}")
            import traceback
            logger.error(traceback.format_exc())


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="穷游网数据导入脚本")
    parser.add_argument(
        "data_file",
        type=str,
        help="JSON数据文件路径（例如: tmp/杭州.json）"
    )
    parser.add_argument(
        "--destination",
        type=str,
        default="杭州",
        help="目的地（默认: 杭州）"
    )
    parser.add_argument(
        "--city",
        type=str,
        default="杭州市",
        help="城市（默认: 杭州市）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际插入数据"
    )
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    
    # 检查文件是否存在
    if not os.path.exists(args.data_file):
        logger.error(f"❌ 数据文件不存在: {args.data_file}")
        sys.exit(1)
    
    # 执行导入
    await insert_attraction_details(
        data_file=args.data_file,
        destination=args.destination,
        city=args.city,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    # 预览模式（不实际插入，只看解析结果）
    # python scripts/qyer_data_insert.py tmp/杭州.json --dry-run

    # 实际导入（默认目的地为"杭州"，城市为"杭州市"）
    # python scripts/qyer_data_insert.py tmp/杭州.json

    # 指定目的地和城市
    # python scripts/qyer_data_insert.py tmp/杭州.json --destination 杭州 --city 杭州市
    asyncio.run(main())

