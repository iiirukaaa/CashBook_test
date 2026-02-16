from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, DEFAULT_CATEGORIES, User


def ensure_seed_data(db: Session) -> None:
    user = db.scalar(select(User).where(User.id == 1))
    if user is None:
        db.add(User(id=1, name="default"))
        db.flush()

    existing = {
        name
        for (name,) in db.execute(
            select(Category.name).where(Category.is_fixed.is_(True))
        ).all()
    }
    for name in DEFAULT_CATEGORIES:
        if name not in existing:
            db.add(Category(name=name, is_fixed=True, is_active=True, user_id=1))

    db.commit()
