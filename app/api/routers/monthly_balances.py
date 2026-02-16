from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Account, MonthlyBalance
from app.db.session import get_db
from app.schemas import MonthlyBalanceRead, MonthlyBalanceUpsert
from app.services.month_locks import is_month_locked

router = APIRouter(prefix="/api/monthly-balance", tags=["monthly-balance"])


@router.get("/{year}/{month}", response_model=list[MonthlyBalanceRead])
def get_monthly_balances(year: int, month: int, db: Session = Depends(get_db)) -> list[MonthlyBalance]:
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month must be 1-12")

    balances = db.scalars(
        select(MonthlyBalance)
        .where(MonthlyBalance.year == year, MonthlyBalance.month == month)
        .order_by(MonthlyBalance.account_id.asc())
    ).all()
    return balances


@router.put("/{year}/{month}", response_model=MonthlyBalanceRead)
def upsert_monthly_balance(
    year: int, month: int, payload: MonthlyBalanceUpsert, db: Session = Depends(get_db)
) -> MonthlyBalance:
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month must be 1-12")
    if not db.get(Account, payload.account_id):
        raise HTTPException(status_code=404, detail="account not found")
    if is_month_locked(db, year, month):
        raise HTTPException(status_code=423, detail="month is locked")

    balance = db.scalar(
        select(MonthlyBalance).where(
            MonthlyBalance.year == year,
            MonthlyBalance.month == month,
            MonthlyBalance.account_id == payload.account_id,
        )
    )
    if not balance:
        balance = MonthlyBalance(
            year=year,
            month=month,
            account_id=payload.account_id,
            opening_balance=payload.opening_balance,
            note=payload.note,
            user_id=1,
        )
        db.add(balance)
    else:
        balance.opening_balance = payload.opening_balance
        balance.note = payload.note

    db.commit()
    db.refresh(balance)
    return balance
