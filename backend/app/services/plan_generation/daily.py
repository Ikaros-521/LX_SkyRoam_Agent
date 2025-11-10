"""Shared helpers for modular travel plan generation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
import copy
import math
import re

from loguru import logger

LLMRequester = Callable[..., Awaitable[Optional[Any]]]
PromptBuilder = Callable[[int, str, Optional[float]], Tuple[str, str, int, float]]
FallbackBuilder = Callable[[int, str], Dict[str, Any]]
DayEntryExtractor = Callable[[Any, int, str], Optional[Dict[str, Any]]]


def calculate_date(start_date: Optional[Any], days_offset: int) -> str:
    """Return YYYY-MM-DD string for ``start_date`` plus ``days_offset`` days."""
    if not start_date:
        return ""
    base: Optional[datetime] = None
    if isinstance(start_date, datetime):
        base = start_date
    else:
        value = str(start_date).strip()
        if not value:
            return ""
        try:
            base = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                base = datetime.strptime(value.split("T")[0], "%Y-%m-%d")
            except ValueError:
                return value
    target = base + timedelta(days=days_offset)
    return target.strftime("%Y-%m-%d")


def extract_day_entry(parsed: Any, day: int, date_str: str) -> Optional[Dict[str, Any]]:
    """Normalize the structure returned by the LLM into a per-day dictionary."""
    day_plan: Optional[Dict[str, Any]] = None
    if isinstance(parsed, dict):
        day_plan = parsed
    elif isinstance(parsed, list) and parsed:
        if isinstance(parsed[0], dict):
            day_plan = parsed[0]
    if not isinstance(day_plan, dict):
        return None
    day_plan.setdefault("day", day)
    if date_str:
        day_plan.setdefault("date", date_str)
    return day_plan


async def generate_daily_entries(
    *,
    module_name: str,
    total_days: int,
    start_date: Optional[Any],
    per_day_budget: Optional[float],
    build_prompts: PromptBuilder,
    llm_requester: LLMRequester,
    fallback_builder: FallbackBuilder,
    post_process: Optional[Callable[[Dict[str, Any], int, str], Dict[str, Any]]] = None,
    day_entry_extractor: Optional[DayEntryExtractor] = None,
) -> List[Dict[str, Any]]:
    """Generate structured daily entries with graceful fallback handling."""
    extractor = day_entry_extractor or extract_day_entry
    results: List[Dict[str, Any]] = []
    for day in range(1, max(total_days, 0) + 1):
        date_str = calculate_date(start_date, day - 1)
        try:
            system_prompt, user_prompt, max_tokens, temperature = build_prompts(
                day, date_str, per_day_budget
            )
            parsed = await llm_requester(
                system_prompt,
                user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                log_context=f"{module_name} 第{day}天",
            )
            if parsed is not None:
                day_plan = extractor(parsed, day, date_str)
                if day_plan:
                    if post_process:
                        day_plan = post_process(day_plan, day, date_str)
                    results.append(day_plan)
                    continue
            logger.warning(f"{module_name} 第{day}天LLM返回无效，启用降级方案")
        except Exception as exc:  # pragma: no cover - defensive log only
            logger.error(f"{module_name} 第{day}天生成异常: {exc}")
        results.append(fallback_builder(day, date_str))
    logger.info(f"{module_name} 按天生成完成，共 {len(results)} 天")
    return results


def get_day_entry_from_list(entries: Optional[List[Dict[str, Any]]], day: int) -> Optional[Dict[str, Any]]:
    """Return the first entry whose ``day`` matches the provided value."""
    if not entries:
        return None
    for entry in entries:
        if entry.get("day") == day:
            return entry
    return None


def extract_price_value(entry: Dict[str, Any]) -> float:
    """Extract numeric price information from a loosely structured payload."""
    price_candidates = [entry.get("price"), entry.get("average_price"), entry.get("cost")]
    for candidate in price_candidates:
        if candidate is None:
            continue
        if isinstance(candidate, (int, float)):
            return float(candidate)
        try:
            match = re.search(r"(\d+(\.\d+)?)", str(candidate))
            if match:
                return float(match.group(1))
        except Exception:
            continue
    price_range = entry.get("price_range")
    if price_range:
        try:
            match = re.search(r"(\d+(\.\d+)?)", str(price_range))
            if match:
                return float(match.group(1))
        except Exception:
            pass
    return float("inf")


def _finite_price(value: float) -> float:
    return value if math.isfinite(value) else 0.0


def build_simple_attraction_plan(
    day: int,
    date_str: str,
    attractions_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Fallback attraction plan when the LLM response is unusable."""
    selection: List[Dict[str, Any]] = []
    if attractions_data:
        start = (day - 1) * 2
        selection = attractions_data[start : start + 2]
        if not selection:
            selection = attractions_data[:2]
    selection = [copy.deepcopy(attr) for attr in selection]

    schedule: List[Dict[str, Any]] = []
    total_cost = 0.0
    for idx, attr in enumerate(selection):
        start_hour = 9 + idx * 3
        end_hour = start_hour + 3
        cost = attr.get("price") or 0
        try:
            total_cost += float(cost)
        except (TypeError, ValueError):
            pass
        schedule.append(
            {
                "time": f"{start_hour:02d}:00-{end_hour:02d}:00",
                "activity": "景点游览",
                "location": attr.get("name", "景点"),
                "description": attr.get("description", "探索当地特色景点"),
                "cost": cost or 0,
                "tips": "根据景点建议合理安排行程，提前预约可减少排队时间。",
            }
        )

    daily_tips = ["建议根据天气和人流灵活调整行程", "提前确认景点开放时间和购票方式"]
    return {
        "day": day,
        "date": date_str,
        "schedule": schedule,
        "attractions": selection,
        "estimated_cost": total_cost,
        "daily_tips": daily_tips,
    }


def build_simple_dining_plan(
    day: int,
    date_str: str,
    restaurants_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    meal_types = [("早餐", 8), ("午餐", 12), ("晚餐", 18)]
    start = (day - 1) * len(meal_types)
    selection = restaurants_data[start : start + len(meal_types)]
    if len(selection) < len(meal_types):
        selection.extend(restaurants_data[: len(meal_types) - len(selection)])
    meals: List[Dict[str, Any]] = []
    total_cost = 0.0
    iterable = selection if selection else [{} for _ in meal_types]
    for (meal_type, base_hour), restaurant in zip(meal_types, iterable):
        rest = copy.deepcopy(restaurant) if isinstance(restaurant, dict) else {}
        price_value = _finite_price(extract_price_value(rest)) if rest else 0.0
        meals.append(
            {
                "type": meal_type,
                "time": f"{base_hour:02d}:00-{base_hour + 1:02d}:00",
                "restaurant_name": rest.get("name", "当地餐厅"),
                "cuisine": rest.get("cuisine", "当地特色"),
                "recommended_dishes": [
                    {
                        "name": dish,
                        "description": "当地特色菜品",
                        "price": price_value or "依据菜单",
                        "taste": "口味适中",
                    }
                    for dish in rest.get("specialties", [])[:2]
                ]
                or [
                    {
                        "name": "招牌菜",
                        "description": "当地招牌菜品",
                        "price": price_value or "依据菜单",
                        "taste": "风味独特",
                    }
                ],
                "atmosphere": rest.get("atmosphere", "环境舒适"),
                "estimated_cost": price_value,
                "booking_tips": "高峰时段建议提前到店",
                "address": rest.get("address", ""),
            }
        )
        total_cost += price_value

    return {
        "day": day,
        "date": date_str,
        "meals": meals,
        "daily_food_cost": total_cost,
        "food_highlights": [
            meal["restaurant_name"] for meal in meals if meal.get("restaurant_name")
        ],
    }


def build_simple_transportation_plan(
    day: int,
    date_str: str,
    transportation_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    selection = transportation_data[:2] if transportation_data else []
    if not selection:
        selection = [
            {
                "type": "地铁",
                "name": "地铁1号线",
                "route": "市区→景点",
                "duration": 30,
                "distance": 10,
                "price": 5,
                "usage_tips": ["高峰期建议避开", "提前准备零钱或交通卡"],
            }
        ]

    primary_routes: List[Dict[str, Any]] = []
    total_cost = 0.0
    for route in selection:
        try:
            total_cost += float(route.get("price") or 0)
        except (TypeError, ValueError):
            pass
        primary_routes.append(copy.deepcopy(route))

    return {
        "day": day,
        "date": date_str,
        "primary_routes": primary_routes,
        "backup_routes": [],
        "daily_transport_cost": total_cost,
        "tips": ["使用默认交通建议"],
    }


def build_simple_accommodation_day(
    day: int,
    date_str: str,
    hotels_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    hotel: Dict[str, Any] = {}
    if hotels_data:
        index = (day - 1) % len(hotels_data)
        hotel = copy.deepcopy(hotels_data[index])
    price_value = _finite_price(extract_price_value(hotel)) if hotel else 0.0
    return {
        "day": day,
        "date": date_str,
        "flight": {},
        "hotel": hotel
        or {
            "name": "待定酒店",
            "address": "",
            "price_per_night": 0,
            "rating": 4.0,
            "amenities": [],
            "location_advantage": "待定",
        },
        "daily_cost": price_value,
        "accommodation_highlights": ["位置优越，交通便利"],
        "notes": ["使用默认住宿建议"],
    }
