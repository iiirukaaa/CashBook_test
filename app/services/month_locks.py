from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MonthlyLock


def is_month_locked(db: Session, year: int, month: int) -> bool:
    lock = db.scalar(
        select(MonthlyLock).where(MonthlyLock.year == year, MonthlyLock.month == month)
    )
    return bool(lock and lock.is_locked)


def set_month_lock(db: Session, year: int, month: int, is_locked: bool) -> MonthlyLock:
    lock = db.scalar(
        select(MonthlyLock).where(MonthlyLock.year == year, MonthlyLock.month == month)
    )
    if not lock:
        lock = MonthlyLock(year=year, month=month, is_locked=is_locked, user_id=1)
        db.add(lock)
    else:
        lock.is_locked = is_locked
    db.commit()
    db.refresh(lock)
    return lock
