from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.month_locks import is_month_locked
from app.services.csv_io import export_transactions_csv, import_transactions_csv

router = APIRouter(prefix="/api/csv", tags=["csv"])


@router.post("/import")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, int]:
    data = await file.read()
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
        for row in reader:
            tx_date = date.fromisoformat((row.get("date") or "").strip())
            if is_month_locked(db, tx_date.year, tx_date.month):
                raise HTTPException(status_code=423, detail=f"month is locked: {tx_date.year}-{tx_date.month:02d}")
        count = import_transactions_csv(db, data)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"imported": count}


@router.get("/export")
def export_csv(year: int | None = None, month: int | None = None, db: Session = Depends(get_db)) -> StreamingResponse:
    content = export_transactions_csv(db, year=year, month=month)
    filename = "transactions.csv"
    if year and month:
        filename = f"transactions_{year}_{month:02d}.csv"

    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
