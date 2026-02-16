from __future__ import annotations

from app.schemas.common import TransactionCreate, TransactionUpdate


class ValidationError(ValueError):
    pass


def validate_transaction_input(payload: TransactionCreate | TransactionUpdate) -> None:
    tx_type = getattr(payload, "type", None)
    account_id = getattr(payload, "account_id", None)
    to_account_id = getattr(payload, "to_account_id", None)

    if tx_type in {"income", "expense", "transfer"} and not account_id:
        raise ValidationError("account_id is required for income/expense/transfer")

    if tx_type == "transfer":
        if not to_account_id:
            raise ValidationError("to_account_id is required for transfer")
        if account_id == to_account_id:
            raise ValidationError("account_id and to_account_id must be different")

    if tx_type in {"income", "expense"} and to_account_id:
        raise ValidationError("to_account_id must be null for income/expense")
