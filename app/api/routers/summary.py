from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import MonthlySummaryRead, SummaryRead
from app.services.summary import get_month_summary, get_year_summary

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("/year/{year}", response_model=SummaryRead)
def summary_year(year: int, db: Session = Depends(get_db)) -> dict[str, int]:
    return get_year_summary(db, year)


@router.get("/month/{year}/{month}", response_model=MonthlySummaryRead)
def summary_month(year: int, month: int, db: Session = Depends(get_db)) -> dict[str, int]:
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month must be 1-12")
    return get_month_summary(db, year, month)
