from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "CUSTOMER"
    OPERATOR = "OPERATOR"
    ADMIN = "ADMIN"


class Status(StrEnum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class BusinessError(Exception):
    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status = status
        self.code = code


MAX_MINOR = 10**12


def validate_debit(
    amount: int, balance: int, spent: int, operation_limit: int, daily_limit: int
) -> None:
    if amount > operation_limit:
        raise BusinessError(409, "OPERATION_LIMIT")
    if spent + amount > daily_limit:
        raise BusinessError(409, "DAILY_LIMIT")
    if amount > balance:
        raise BusinessError(409, "INSUFFICIENT_FUNDS")
