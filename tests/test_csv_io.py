from __future__ import annotations

from datetime import date

from app.db.models import Account, Category, Transaction, User
from app.services.csv_io import export_transactions_csv, import_transactions_csv


def test_export_import_csv(db):
    db.add(User(id=1, name="default"))
    account = Account(name="現金", kind="cash", user_id=1)
    category = Category(name="食費", is_fixed=True, is_active=True, user_id=1)
    db.add_all([account, category])
    db.flush()

    tx = Transaction(
        date=date(2026, 2, 10),
        year=2026,
        month=2,
        type="expense",
        amount=1500,
        account_id=account.id,
        category_id=category.id,
        description="ランチ",
        note="社食",
        user_id=1,
    )
    db.add(tx)
    db.commit()

    content = export_transactions_csv(db, year=2026, month=2)
    assert "date,type,amount,account,to_account,category,category_free,description,note" in content
    assert "2026-02-10,expense,1500,現金,,食費,,ランチ,社食" in content

    csv_payload = (
        "date,type,amount,account,to_account,category,category_free,description,note\n"
        "2026-02-20,income,200000,給与口座,,給与,,給料,\n"
    )
    imported = import_transactions_csv(db, csv_payload.encode("utf-8"))
    assert imported == 1

    exported_after = export_transactions_csv(db, year=2026, month=2)
    assert "給与口座" in exported_after
