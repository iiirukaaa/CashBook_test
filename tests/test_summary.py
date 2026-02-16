from __future__ import annotations

from datetime import date

from app.db.models import Account, MonthlyBalance, Transaction, User
from app.services.summary import get_month_summary, get_year_summary


def test_summary_logic(db):
    db.add(User(id=1, name="default"))
    account = Account(name="現金", kind="cash", user_id=1)
    db.add(account)
    db.flush()
    db.add_all(
        [
            Transaction(date=date(2026, 2, 1), year=2026, month=2, type="income", amount=300000, user_id=1),
            Transaction(date=date(2026, 2, 2), year=2026, month=2, type="expense", amount=120000, user_id=1),
            Transaction(date=date(2026, 2, 3), year=2026, month=2, type="transfer", amount=20000, user_id=1),
            Transaction(date=date(2026, 2, 4), year=2026, month=2, type="adjust", amount=5000, user_id=1),
            Transaction(date=date(2026, 3, 1), year=2026, month=3, type="expense", amount=10000, user_id=1),
        ]
    )
    db.add(MonthlyBalance(year=2026, month=2, account_id=account.id, opening_balance=50000, user_id=1))
    db.commit()

    year_summary = get_year_summary(db, 2026)
    assert year_summary["income_total"] == 300000
    assert year_summary["expense_total"] == 130000
    assert year_summary["net"] == 170000

    month_summary = get_month_summary(db, 2026, 2)
    assert month_summary["income_total"] == 300000
    assert month_summary["expense_total"] == 120000
    assert month_summary["adjust_total"] == 5000
    assert month_summary["opening_balance"] == 50000
    assert month_summary["net"] == 180000
