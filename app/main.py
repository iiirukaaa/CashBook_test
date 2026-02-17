from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers import (
    accounts,
    categories,
    csv_io,
    liabilities,
    month_locks,
    monthly_balances,
    summary,
    transactions,
)
from app.db.init_db import ensure_seed_data
from app.db.session import Base, SessionLocal, engine
from app.web.auth_cookie import get_auth_user_id
from app.web.routes import router as web_router

app = FastAPI(title="家計簿Webアプリ")

app.include_router(summary.router)
app.include_router(transactions.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(monthly_balances.router)
app.include_router(liabilities.router)
app.include_router(csv_io.router)
app.include_router(month_locks.router)
app.include_router(web_router)

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")


@app.middleware("http")
async def auth_guard(request, call_next):
    path = request.url.path
    public_paths = {"/login", "/health", "/openapi.json", "/docs", "/redoc", "/favicon.ico"}
    if path in public_paths or path.startswith("/static"):
        return await call_next(request)

    if get_auth_user_id(request):
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"detail": "authentication required"}, status_code=401)

    return RedirectResponse(url=f"/login?next={path}", status_code=302)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_seed_data(db)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
