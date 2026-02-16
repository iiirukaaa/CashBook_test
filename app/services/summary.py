from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.models import MonthlyBalance, Transaction


def _sum_amount(db: Session, *conditions) -> int:
    value = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(and_(*conditions)))
    return int(value or 0)


def get_year_summary(db: Session, year: int) -> dict[str, int]:
    income_total = _sum_amount(db, Transaction.year == year, Transaction.type == "income")
    expense_total = _sum_amount(db, Transaction.year == year, Transaction.type == "expense")
    return {
        "income_total": income_total,
        "expense_total": expense_total,
        "net": income_total - expense_total,
    }


def get_month_summary(db: Session, year: int, month: int) -> dict[str, int]:
    income_total = _sum_amount(
        db, Transaction.year == year, Transaction.month == month, Transaction.type == "income"
    )
    expense_total = _sum_amount(
        db, Transaction.year == year, Transaction.month == month, Transaction.type == "expense"
    )
    adjust_total = _sum_amount(
        db, Transaction.year == year, Transaction.month == month, Transaction.type == "adjust"
    )

    opening = db.scalar(
        select(func.coalesce(func.sum(MonthlyBalance.opening_balance), 0)).where(
            MonthlyBalance.year == year,
            MonthlyBalance.month == month,
        )
    )
    opening_balance = int(opening or 0)

    return {
        "income_total": income_total,
        "expense_total": expense_total,
        "net": income_total - expense_total,
        "opening_balance": opening_balance,
        "adjust_total": adjust_total,
    }
