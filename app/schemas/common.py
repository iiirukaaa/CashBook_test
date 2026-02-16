from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TransactionType = Literal["income", "expense", "transfer", "adjust"]


class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="other", max_length=50)
    is_active: bool = True
    note: str | None = None


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: str | None = None
    kind: str | None = None
    is_active: bool | None = None
    note: str | None = None


class AccountRead(AccountBase):
    id: int

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_fixed: bool = False
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    is_fixed: bool | None = None
    is_active: bool | None = None


class CategoryRead(CategoryBase):
    id: int

    class Config:
        from_attributes = True


class MonthlyBalanceUpsert(BaseModel):
    account_id: int
    opening_balance: int
    note: str | None = None


class MonthlyBalanceRead(MonthlyBalanceUpsert):
    id: int
    year: int
    month: int

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    date: dt.date
    type: TransactionType
    amount: int = Field(gt=0)
    account_id: int | None = None
    to_account_id: int | None = None
    category_id: int | None = None
    category_free: str | None = Field(default=None, max_length=120)
    description: str | None = None
    note: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        allowed = {"income", "expense", "transfer", "adjust"}
        if value not in allowed:
            raise ValueError("invalid type")
        return value


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    date: dt.date | None = None
    type: TransactionType | None = None
    amount: int | None = Field(default=None, gt=0)
    account_id: int | None = None
    to_account_id: int | None = None
    category_id: int | None = None
    category_free: str | None = Field(default=None, max_length=120)
    description: str | None = None
    note: str | None = None


class TransactionRead(TransactionBase):
    id: int
    year: int
    month: int

    class Config:
        from_attributes = True


class LiabilityBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    balance: int
    monthly_payment: int | None = None
    payment_day: int | None = Field(default=None, ge=1, le=31)
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    fee_amount: int | None = None
    note: str | None = None
    is_active: bool = True


class LiabilityCreate(LiabilityBase):
    pass


class LiabilityUpdate(BaseModel):
    name: str | None = None
    balance: int | None = None
    monthly_payment: int | None = None
    payment_day: int | None = Field(default=None, ge=1, le=31)
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    fee_amount: int | None = None
    note: str | None = None
    is_active: bool | None = None


class LiabilityRead(LiabilityBase):
    id: int

    class Config:
        from_attributes = True


class SummaryRead(BaseModel):
    income_total: int
    expense_total: int
    net: int


class MonthlySummaryRead(SummaryRead):
    opening_balance: int
    adjust_total: int


class MonthlyLockRead(BaseModel):
    year: int
    month: int
    is_locked: bool

    class Config:
        from_attributes = True


class MonthlyLockUpsert(BaseModel):
    is_locked: bool
