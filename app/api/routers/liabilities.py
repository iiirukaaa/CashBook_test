from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Liability
from app.db.session import get_db
from app.schemas import LiabilityCreate, LiabilityRead, LiabilityUpdate

router = APIRouter(prefix="/api/liabilities", tags=["liabilities"])


@router.get("", response_model=list[LiabilityRead])
def list_liabilities(db: Session = Depends(get_db)) -> list[Liability]:
    return db.scalars(select(Liability).order_by(Liability.is_active.desc(), Liability.name.asc())).all()


@router.post("", response_model=LiabilityRead)
def create_liability(payload: LiabilityCreate, db: Session = Depends(get_db)) -> Liability:
    liability = Liability(**payload.model_dump(), user_id=1)
    db.add(liability)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="liability name must be unique") from exc
    db.refresh(liability)
    return liability


@router.put("/{liability_id}", response_model=LiabilityRead)
def update_liability(liability_id: int, payload: LiabilityUpdate, db: Session = Depends(get_db)) -> Liability:
    liability = db.get(Liability, liability_id)
    if not liability:
        raise HTTPException(status_code=404, detail="liability not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(liability, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="liability name must be unique") from exc

    db.refresh(liability)
    return liability


@router.delete("/{liability_id}")
def delete_liability(liability_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    liability = db.get(Liability, liability_id)
    if not liability:
        raise HTTPException(status_code=404, detail="liability not found")
    db.delete(liability)
    db.commit()
    return {"status": "ok"}
