"""
Normalize travel plan preference keys in the database.

Usage:
    python -m backend.scripts.normalize_preferences
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.travel_plan import TravelPlan

LEGACY_KEY_MAP = {
    "travelers": ["travelers_count"],
    "ageGroups": ["age_groups"],
    "foodPreferences": ["food_preferences"],
    "dietaryRestrictions": ["dietary_restrictions"],
}


def normalize_preferences(prefs: Any) -> Tuple[Any, bool]:
    if not isinstance(prefs, dict):
        return prefs, False

    changed = False
    normalized: Dict[str, Any] = dict(prefs)

    for new_key, legacy_keys in LEGACY_KEY_MAP.items():
        if new_key not in normalized:
            for legacy in legacy_keys:
                if legacy in normalized:
                    normalized[new_key] = normalized.pop(legacy)
                    changed = True
                    break
        # Remove any leftovers
        for legacy in legacy_keys:
            if legacy in normalized:
                normalized.pop(legacy)
                changed = True

    return normalized, changed


def migrate(session: Session, batch_size: int = 200) -> int:
    updated = 0
    stmt = select(TravelPlan.id, TravelPlan.preferences)
    result = session.execute(stmt)

    for plan_id, prefs in result:
        normalized, changed = normalize_preferences(prefs)
        if not changed:
            continue
        session.execute(
            TravelPlan.__table__.update()
            .where(TravelPlan.id == plan_id)
            .values(preferences=normalized)
        )
        updated += 1
        if updated % batch_size == 0:
            session.commit()
            logger.info(f"Normalized {updated} travel plans...")

    if updated % batch_size:
        session.commit()
    return updated


def main() -> None:
    logger.info("Starting travel plan preferences normalization...")
    session = SessionLocal()
    try:
        updated = migrate(session)
        logger.success(f"Normalization completed. Updated {updated} records.")
    except Exception as exc:
        session.rollback()
        logger.error(f"Normalization failed: {exc}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
