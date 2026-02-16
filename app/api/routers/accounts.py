from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Account, MonthlyBalance, Transaction
from app.db.session import get_db
from app.schemas import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountRead])
def list_accounts(db: Session = Depends(get_db)) -> list[Account]:
    return db.scalars(select(Account).order_by(Account.is_active.desc(), Account.name.asc())).all()


@router.post("", response_model=AccountRead)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)) -> Account:
    account = Account(**payload.model_dump(), user_id=1)
    db.add(account)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="account name must be unique") from exc
    db.refresh(account)
    return account


@router.post("/import-json")
def import_accounts_json(payload: Any, db: Session = Depends(get_db)) -> dict[str, int]:
    try:
        items = payload if isinstance(payload, list) else payload.get("accounts", [])
        if not isinstance(items, list):
            raise ValueError("accounts must be list")
        existing_names = {name for (name,) in db.execute(select(Account.name)).all()}
        created = 0
        for item in items:
            name = str(item.get("name", "")).strip()
            if not name or name in existing_names:
                continue
            kind = str(item.get("kind", "other") or "other")
            note = item.get("note")
            db.add(Account(name=name, kind=kind, note=note, is_active=True, user_id=1))
            existing_names.add(name)
            created += 1
        db.commit()
        return {"created": created}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid json payload: {exc}") from exc


@router.put("/{account_id}", response_model=AccountRead)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)) -> Account:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="account name must be unique") from exc

    db.refresh(account)
    return account


@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    for tx in db.scalars(select(Transaction).where(Transaction.account_id == account_id)).all():
        tx.account_id = None
    for tx in db.scalars(select(Transaction).where(Transaction.to_account_id == account_id)).all():
        tx.to_account_id = None
    for bal in db.scalars(select(MonthlyBalance).where(MonthlyBalance.account_id == account_id)).all():
        db.delete(bal)
    db.delete(account)
    db.commit()
    return {"status": "ok"}
