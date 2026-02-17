from __future__ import annotations

import calendar
import json
from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Account, Category, Liability, MonthlyBalance, Transaction, User
from app.db.session import get_db
from app.services.auth import verify_password
from app.services.month_locks import is_month_locked, set_month_lock
from app.services.summary import get_month_summary, get_year_summary
from app.services.transactions import ValidationError, validate_transaction_input
from app.web.auth_cookie import AUTH_COOKIE_NAME

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/web/templates")

TX_TYPE_LABELS = {
    "income": "収入",
    "expense": "支出",
    "transfer": "移動",
    "adjust": "調整",
}


def _today() -> date:
    return date.today()


def _resolve_year(year: int | None) -> int:
    today = _today()
    if year is None:
        return today.year
    if year > today.year:
        return today.year
    return year


def _max_month_for_year(year: int) -> int:
    today = _today()
    if year < today.year:
        return 12
    if year == today.year:
        return today.month
    return 0


def _year_options() -> list[int]:
    current = _today().year
    return list(range(current, current - 9, -1))


def _base_context(selected_year: int) -> dict:
    return {
        "selected_year": selected_year,
        "year_options": _year_options(),
    }


def _is_safe_next(next_path: str | None) -> bool:
    return bool(next_path and next_path.startswith("/") and not next_path.startswith("//") and not next_path.startswith("/login"))


def _active_accounts_for_opening(db: Session) -> list[Account]:
    return db.scalars(
        select(Account)
        .where(Account.is_active.is_(True), Account.kind != "card")
        .order_by(Account.name.asc())
    ).all()


def _ensure_month_accessible(year: int, month: int) -> None:
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month must be 1-12")
    if month > _max_month_for_year(year):
        raise HTTPException(status_code=404, detail="future month is not available")


def _ensure_month_unlocked(db: Session, year: int, month: int) -> None:
    if is_month_locked(db, year, month):
        raise HTTPException(status_code=423, detail="month is locked")


def _delete_account(db: Session, account_id: int) -> None:
    account = db.get(Account, account_id)
    if not account:
        return
    for tx in db.scalars(select(Transaction).where(Transaction.account_id == account_id)).all():
        tx.account_id = None
    for tx in db.scalars(select(Transaction).where(Transaction.to_account_id == account_id)).all():
        tx.to_account_id = None
    for bal in db.scalars(select(MonthlyBalance).where(MonthlyBalance.account_id == account_id)).all():
        db.delete(bal)
    db.delete(account)


def _delete_category(db: Session, category_id: int) -> None:
    category = db.get(Category, category_id)
    if not category:
        return
    for tx in db.scalars(select(Transaction).where(Transaction.category_id == category_id)).all():
        tx.category_id = None
    db.delete(category)


def _month_context(db: Session, year: int, month: int) -> dict:
    summary = get_month_summary(db, year, month)
    txs = db.scalars(
        select(Transaction)
        .where(Transaction.year == year, Transaction.month == month)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    ).all()
    accounts = db.scalars(select(Account).where(Account.is_active.is_(True)).order_by(Account.name.asc())).all()
    categories = db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name.asc())).all()

    is_locked = is_month_locked(db, year, month)
    max_day = calendar.monthrange(year, month)[1]
    if year == _today().year and month == _today().month:
        max_day = min(max_day, _today().day)

    return {
        "summary": summary,
        "transactions": txs,
        "accounts": accounts,
        "categories": categories,
        "is_locked": is_locked,
        "max_day": max_day,
        "tx_type_labels": TX_TYPE_LABELS,
    }


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    next_path = request.query_params.get("next", "/")
    return templates.TemplateResponse(
        request,
        "login.html",
        {"next_path": next_path if _is_safe_next(next_path) else "/", "error": None},
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next_path: str = Form(default="/"),
    db: Session = Depends(get_db),
) -> Response:
    user = db.scalar(select(User).where(User.name == username))
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"next_path": next_path if _is_safe_next(next_path) else "/", "error": "ユーザー名またはパスワードが正しくありません。"},
            status_code=401,
        )

    response = RedirectResponse(url=next_path if _is_safe_next(next_path) else "/", status_code=303)
    response.set_cookie(
        AUTH_COOKIE_NAME,
        str(user.id),
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return response


@router.post("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return response


@router.get("/", response_class=HTMLResponse)
def index(request: Request, year: int | None = None, db: Session = Depends(get_db)) -> HTMLResponse:
    selected_year = _resolve_year(year)
    summary = get_year_summary(db, selected_year)
    accounts = db.scalars(select(Account).where(Account.is_active.is_(True)).order_by(Account.name.asc())).all()
    liabilities = db.scalars(select(Liability).where(Liability.is_active.is_(True)).order_by(Liability.name.asc())).all()

    max_month = _max_month_for_year(selected_year)
    months = list(range(1, max_month + 1))

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "year": selected_year,
            "summary": summary,
            "accounts": accounts,
            "liabilities": liabilities,
            "months": months,
            **_base_context(selected_year),
        },
    )


@router.get("/month/{year}/{month}", response_class=HTMLResponse)
def month_page(request: Request, year: int, month: int, db: Session = Depends(get_db)) -> HTMLResponse:
    _ensure_month_accessible(year, month)

    context = _month_context(db, year, month)
    editing_id = request.query_params.get("edit")
    editing_tx = db.get(Transaction, int(editing_id)) if editing_id else None
    return templates.TemplateResponse(
        request,
        "month.html",
        {
            "year": year,
            "month": month,
            "editing_tx": editing_tx,
            **context,
            **_base_context(year),
        },
    )


@router.post("/month/{year}/{month}/lock")
def month_lock_switch(
    year: int,
    month: int,
    is_locked: int = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    _ensure_month_accessible(year, month)
    set_month_lock(db, year, month, bool(is_locked))
    return RedirectResponse(url=f"/month/{year}/{month}", status_code=303)


@router.post("/month/{year}/{month}/transactions")
def create_or_update_transaction(
    year: int,
    month: int,
    tx_id: int | None = Form(default=None),
    day: int = Form(...),
    tx_type: str = Form(alias="type"),
    amount: int = Form(...),
    account_id: int | None = Form(default=None),
    to_account_id: int | None = Form(default=None),
    category_id: int | None = Form(default=None),
    category_free: str | None = Form(default=None),
    description: str | None = Form(default=None),
    note: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    _ensure_month_accessible(year, month)
    _ensure_month_unlocked(db, year, month)

    try:
        tx_date = date(year, month, day)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid day") from exc

    if tx_date > _today():
        raise HTTPException(status_code=422, detail="future date is not allowed")

    payload = Transaction(
        date=tx_date,
        type=tx_type,
        amount=amount,
        account_id=account_id,
        to_account_id=to_account_id,
        category_id=category_id,
        category_free=category_free or None,
        description=description or None,
        note=note or None,
        year=tx_date.year,
        month=tx_date.month,
        user_id=1,
    )

    try:
        validate_transaction_input(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if tx_id:
        current = db.get(Transaction, tx_id)
        if not current:
            raise HTTPException(status_code=404, detail="transaction not found")
        for field in [
            "date",
            "type",
            "amount",
            "account_id",
            "to_account_id",
            "category_id",
            "category_free",
            "description",
            "note",
            "year",
            "month",
        ]:
            setattr(current, field, getattr(payload, field))
    else:
        db.add(payload)

    db.commit()
    return RedirectResponse(url=f"/month/{year}/{month}", status_code=303)


@router.post("/month/{year}/{month}/transactions/{tx_id}/delete")
def delete_transaction_web(year: int, month: int, tx_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    _ensure_month_accessible(year, month)
    _ensure_month_unlocked(db, year, month)
    tx = db.get(Transaction, tx_id)
    if tx:
        db.delete(tx)
        db.commit()
    return RedirectResponse(url=f"/month/{year}/{month}", status_code=303)


@router.get("/opening-balances/{year}/{month}", response_class=HTMLResponse)
def opening_balances_page(request: Request, year: int, month: int, db: Session = Depends(get_db)) -> HTMLResponse:
    _ensure_month_accessible(year, month)
    accounts = _active_accounts_for_opening(db)
    balances = db.scalars(
        select(MonthlyBalance).where(MonthlyBalance.year == year, MonthlyBalance.month == month)
    ).all()
    by_account_id = {b.account_id: b for b in balances}

    rows: list[dict] = []
    for account in accounts:
        item = by_account_id.get(account.id)
        rows.append(
            {
                "account": account,
                "opening_balance": item.opening_balance if item else 0,
                "note": item.note if item else "",
            }
        )

    return templates.TemplateResponse(
        request,
        "opening_balances.html",
        {
            "year": year,
            "month": month,
            "rows": rows,
            "is_locked": is_month_locked(db, year, month),
            **_base_context(year),
        },
    )


@router.post("/opening-balances/{year}/{month}")
async def save_opening_balances(
    year: int, month: int, request: Request, db: Session = Depends(get_db)
) -> RedirectResponse:
    _ensure_month_accessible(year, month)
    _ensure_month_unlocked(db, year, month)
    accounts = _active_accounts_for_opening(db)
    form = await request.form()

    for account in accounts:
        key_balance = f"opening_balance_{account.id}"
        key_note = f"note_{account.id}"
        raw_balance = form.get(key_balance, "0")
        raw_note = form.get(key_note, "")
        try:
            opening_balance = int(raw_balance)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"invalid opening balance for account {account.name}") from exc

        existing = db.scalar(
            select(MonthlyBalance).where(
                MonthlyBalance.year == year,
                MonthlyBalance.month == month,
                MonthlyBalance.account_id == account.id,
            )
        )
        if existing:
            existing.opening_balance = opening_balance
            existing.note = raw_note or None
        else:
            db.add(
                MonthlyBalance(
                    year=year,
                    month=month,
                    account_id=account.id,
                    opening_balance=opening_balance,
                    note=raw_note or None,
                    user_id=1,
                )
            )

    db.commit()
    return RedirectResponse(url=f"/month/{year}/{month}", status_code=303)


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, year: int | None = None, db: Session = Depends(get_db)) -> HTMLResponse:
    selected_year = _resolve_year(year)
    accounts = db.scalars(select(Account).order_by(Account.name.asc())).all()
    categories = db.scalars(select(Category).order_by(Category.name.asc())).all()
    liabilities = db.scalars(select(Liability).order_by(Liability.name.asc())).all()
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "accounts": accounts,
            "categories": categories,
            "liabilities": liabilities,
            **_base_context(selected_year),
        },
    )


@router.post("/settings/accounts")
def create_account_web(
    name: str = Form(...),
    kind: str = Form(default="other"),
    note: str | None = Form(default=None),
    year: int | None = Form(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    selected_year = _resolve_year(year)
    db.add(Account(name=name, kind=kind, note=note, is_active=True, user_id=1))
    db.commit()
    return RedirectResponse(url=f"/settings?year={selected_year}", status_code=303)


@router.post("/settings/accounts/import-json")
def import_accounts_json_web(
    payload: str = Form(...),
    year: int | None = Form(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    selected_year = _resolve_year(year)
    try:
        data = json.loads(payload)
        items = data if isinstance(data, list) else data.get("accounts", [])
        if not isinstance(items, list):
            raise ValueError("accounts must be list")
        existing_names = {name for (name,) in db.execute(select(Account.name)).all()}
        for item in items:
            name = str(item.get("name", "")).strip()
            if not name or name in existing_names:
                continue
            kind = str(item.get("kind", "other") or "other")
            note = item.get("note")
            db.add(Account(name=name, kind=kind, note=note, is_active=True, user_id=1))
            existing_names.add(name)
        db.commit()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid json: {exc}") from exc
    return RedirectResponse(url=f"/settings?year={selected_year}", status_code=303)


@router.post("/settings/accounts/delete")
async def delete_accounts_web(
    request: Request, year: int | None = Form(default=None), db: Session = Depends(get_db)
) -> RedirectResponse:
    selected_year = _resolve_year(year)
    form = await request.form()
    for raw_id in form.getlist("account_ids"):
        try:
            _delete_account(db, int(raw_id))
        except ValueError:
            continue
    db.commit()
    return RedirectResponse(url=f"/settings?year={selected_year}", status_code=303)


@router.post("/settings/categories")
def create_category_web(
    name: str = Form(...),
    year: int | None = Form(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    selected_year = _resolve_year(year)
    db.add(Category(name=name, is_fixed=False, is_active=True, user_id=1))
    db.commit()
    return RedirectResponse(url=f"/settings?year={selected_year}", status_code=303)


@router.post("/settings/categories/delete")
async def delete_categories_web(
    request: Request, year: int | None = Form(default=None), db: Session = Depends(get_db)
) -> RedirectResponse:
    selected_year = _resolve_year(year)
    form = await request.form()
    for raw_id in form.getlist("category_ids"):
        try:
            _delete_category(db, int(raw_id))
        except ValueError:
            continue
    db.commit()
    return RedirectResponse(url=f"/settings?year={selected_year}", status_code=303)


@router.post("/settings/liabilities")
def create_liability_web(
    name: str = Form(...),
    balance: int = Form(...),
    monthly_payment: int | None = Form(default=None),
    payment_day: int | None = Form(default=None),
    note: str | None = Form(default=None),
    year: int | None = Form(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    selected_year = _resolve_year(year)
    db.add(
        Liability(
            name=name,
            balance=balance,
            monthly_payment=monthly_payment,
            payment_day=payment_day,
            note=note,
            is_active=True,
            user_id=1,
        )
    )
    db.commit()
    return RedirectResponse(url=f"/settings?year={selected_year}", status_code=303)


@router.post("/settings/liabilities/delete")
async def delete_liabilities_web(
    request: Request, year: int | None = Form(default=None), db: Session = Depends(get_db)
) -> RedirectResponse:
    selected_year = _resolve_year(year)
    form = await request.form()
    for raw_id in form.getlist("liability_ids"):
        try:
            item = db.get(Liability, int(raw_id))
        except ValueError:
            item = None
        if item:
            db.delete(item)
    db.commit()
    return RedirectResponse(url=f"/settings?year={selected_year}", status_code=303)
