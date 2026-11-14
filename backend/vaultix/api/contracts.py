from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from vaultix.domain.rules import MAX_MINOR, Role, Status

Amount = Annotated[int, Field(strict=True, gt=0, le=MAX_MINOR)]
Funding = Annotated[int, Field(strict=True, ge=0, le=MAX_MINOR)]
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
Username = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.-]{2,39}$")]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(Input):
    username: Username
    password: Annotated[str, Field(min_length=1, max_length=128)]


class NewUser(Credentials):
    name: Name
    role: Role
    password: Annotated[str, Field(min_length=12, max_length=128)]


class User(BaseModel):
    id: UUID
    username: str
    name: str
    role: Role
    active: bool


class UserChange(Input):
    active: Annotated[bool, Field(strict=True)]


class NewAccount(Input):
    owner_id: UUID
    name: Name
    funding_minor: Funding = 0


class AccountChange(Input):
    status: Status


class Account(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    status: Status
    currency: Literal["RUB"]
    balance_minor: int


class Transfer(Input):
    source_id: UUID
    destination_id: UUID
    amount_minor: Amount
    currency: Literal["RUB"] = "RUB"


class TransferResult(BaseModel):
    id: UUID
    status: Literal["POSTED"]


class Entry(BaseModel):
    account_id: UUID
    amount: int
    side: Literal["DEBIT", "CREDIT"]


class Journal(BaseModel):
    id: UUID
    kind: Literal["TRANSFER", "FUNDING"]
    source_id: UUID
    destination_id: UUID
    amount: int
    created_at: datetime


class JournalDetail(Journal):
    entries: list[Entry]


class Limits(Input):
    per_transfer: Amount
    per_day: Amount

    @model_validator(mode="after")
    def ordered(self):
        if self.per_day < self.per_transfer:
            raise ValueError("Daily limit must be at least the per-transfer limit")
        return self


class Audit(BaseModel):
    id: UUID
    actor_id: UUID | None
    action: str
    result: str
    object_id: UUID | None
    request_id: UUID
    created_at: datetime


class ErrorBody(BaseModel):
    code: str
