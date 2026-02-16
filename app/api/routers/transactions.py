from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Account, Category, Transaction
from app.db.session import get_db
from app.schemas import TransactionCreate, TransactionRead, TransactionUpdate
from app.services.month_locks import is_month_locked
from app.services.transactions import ValidationError, validate_transaction_input

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _validate_refs(db: Session, payload: TransactionCreate | TransactionUpdate) -> None:
    if payload.account_id and not db.get(Account, payload.account_id):
        raise HTTPException(status_code=404, detail="account not found")
    if payload.to_account_id and not db.get(Account, payload.to_account_id):
        raise HTTPException(status_code=404, detail="to_account not found")
    if payload.category_id and not db.get(Category, payload.category_id):
        raise HTTPException(status_code=404, detail="category not found")


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    year: int,
    month: int,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[Transaction]:
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month must be 1-12")

    query = select(Transaction).where(Transaction.year == year, Transaction.month == month)
    if q:
        like = f"%{q}%"
        query = query.outerjoin(Account, Transaction.account_id == Account.id).outerjoin(
            Category, Transaction.category_id == Category.id
        ).where(
            or_(
                Transaction.description.ilike(like),
                Transaction.note.ilike(like),
                Transaction.category_free.ilike(like),
                Account.name.ilike(like),
                Category.name.ilike(like),
            )
        )

    query = query.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit).offset(offset)
    return db.scalars(query).all()


@router.post("", response_model=TransactionRead)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)) -> Transaction:
    if payload.date > date.today():
        raise HTTPException(status_code=422, detail="future date is not allowed")
    if is_month_locked(db, payload.date.year, payload.date.month):
        raise HTTPException(status_code=423, detail="month is locked")
    try:
        validate_transaction_input(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _validate_refs(db, payload)
    tx_date = payload.date
    tx = Transaction(**payload.model_dump(), year=tx_date.year, month=tx_date.month, user_id=1)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int, payload: TransactionUpdate, db: Session = Depends(get_db)
) -> Transaction:
    tx = db.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction not found")

    merged = tx
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(merged, key, value)
    if merged.date and merged.date > date.today():
        raise HTTPException(status_code=422, detail="future date is not allowed")
    if is_month_locked(db, tx.year, tx.month):
        raise HTTPException(status_code=423, detail="month is locked")
    if merged.date and (merged.date.year != tx.year or merged.date.month != tx.month):
        if is_month_locked(db, merged.date.year, merged.date.month):
            raise HTTPException(status_code=423, detail="target month is locked")

    try:
        validate_transaction_input(merged)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _validate_refs(db, merged)
    if merged.date:
        merged.year = merged.date.year
        merged.month = merged.date.month

    db.commit()
    db.refresh(merged)
    return merged


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    tx = db.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction not found")
    if is_month_locked(db, tx.year, tx.month):
        raise HTTPException(status_code=423, detail="month is locked")
    db.delete(tx)
    db.commit()
    return {"status": "ok"}
