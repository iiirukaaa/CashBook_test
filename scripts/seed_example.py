from __future__ import annotations

from datetime import date

from app.db.init_db import ensure_seed_data
from app.db.models import Account, Transaction
from app.db.session import Base, SessionLocal, engine


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_seed_data(db)
        cash = db.query(Account).filter_by(name="現金").first()
        if not cash:
            cash = Account(name="現金", kind="cash", user_id=1)
            db.add(cash)
            db.flush()

        tx = Transaction(
            date=date.today(),
            year=date.today().year,
            month=date.today().month,
            type="expense",
            amount=1000,
            account_id=cash.id,
            description="サンプル支出",
            user_id=1,
        )
        db.add(tx)
        db.commit()


if __name__ == "__main__":
    main()
