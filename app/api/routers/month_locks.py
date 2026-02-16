from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import MonthlyLockRead, MonthlyLockUpsert
from app.services.month_locks import is_month_locked, set_month_lock

router = APIRouter(prefix="/api/month-lock", tags=["month-lock"])


@router.get("/{year}/{month}", response_model=MonthlyLockRead)
def get_month_lock(year: int, month: int, db: Session = Depends(get_db)) -> MonthlyLockRead:
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month must be 1-12")
    return MonthlyLockRead(year=year, month=month, is_locked=is_month_locked(db, year, month))


@router.put("/{year}/{month}", response_model=MonthlyLockRead)
def put_month_lock(
    year: int, month: int, payload: MonthlyLockUpsert, db: Session = Depends(get_db)
) -> MonthlyLockRead:
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month must be 1-12")
    lock = set_month_lock(db, year, month, payload.is_locked)
    return MonthlyLockRead.model_validate(lock)
