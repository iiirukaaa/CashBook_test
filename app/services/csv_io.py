from __future__ import annotations

import csv
import io
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Account, Category, Transaction

CSV_HEADERS = [
    "date",
    "type",
    "amount",
    "account",
    "to_account",
    "category",
    "category_free",
    "description",
    "note",
]


def _get_or_create_account(db: Session, name: str | None) -> Account | None:
    if not name:
        return None
    account = db.scalar(select(Account).where(Account.name == name))
    if account:
        return account
    account = Account(name=name, kind="other", is_active=True, user_id=1)
    db.add(account)
    db.flush()
    return account


def _get_or_create_category(db: Session, name: str | None) -> Category | None:
    if not name:
        return None
    category = db.scalar(select(Category).where(Category.name == name))
    if category:
        return category
    category = Category(name=name, is_fixed=False, is_active=True, user_id=1)
    db.add(category)
    db.flush()
    return category


def export_transactions_csv(db: Session, year: int | None = None, month: int | None = None) -> str:
    query = select(Transaction).order_by(Transaction.date.desc(), Transaction.id.desc())
    if year is not None:
        query = query.where(Transaction.year == year)
    if month is not None:
        query = query.where(Transaction.month == month)

    rows = db.scalars(query).all()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(CSV_HEADERS)

    for tx in rows:
        writer.writerow(
            [
                tx.date.isoformat(),
                tx.type,
                tx.amount,
                tx.account.name if tx.account else "",
                tx.to_account.name if tx.to_account else "",
                tx.category.name if tx.category else "",
                tx.category_free or "",
                tx.description or "",
                tx.note or "",
            ]
        )

    return out.getvalue()


def import_transactions_csv(db: Session, content: bytes) -> int:
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    required = set(CSV_HEADERS)
    if set(reader.fieldnames or []) != required:
        raise ValueError("invalid CSV header")

    count = 0
    for row in reader:
        tx_date = date.fromisoformat((row.get("date") or "").strip())
        tx_type = (row.get("type") or "").strip()
        amount = int((row.get("amount") or "").strip())
        if amount <= 0:
            raise ValueError("amount must be positive")

        account = _get_or_create_account(db, (row.get("account") or "").strip() or None)
        to_account = _get_or_create_account(db, (row.get("to_account") or "").strip() or None)
        category = _get_or_create_category(db, (row.get("category") or "").strip() or None)

        tx = Transaction(
            date=tx_date,
            year=tx_date.year,
            month=tx_date.month,
            type=tx_type,
            amount=amount,
            account_id=account.id if account else None,
            to_account_id=to_account.id if to_account else None,
            category_id=category.id if category else None,
            category_free=(row.get("category_free") or "").strip() or None,
            description=(row.get("description") or "").strip() or None,
            note=(row.get("note") or "").strip() or None,
            user_id=1,
        )
        db.add(tx)
        count += 1

    db.commit()
    return count
