import os

from vaultix.application.identity import passwords
from vaultix.application.ledger import open_account
from vaultix.infrastructure.db import connect_engine, one, query

DEMO_USERS = (
    (
        "demo",
        "Анна Волкова",
        "CUSTOMER",
        (("Основной счёт", 24865000), ("Накопительный", 7245000)),
    ),
    ("recipient", "Илья Соколов", "CUSTOMER", (("Расчётный счёт", 350000),)),
    ("operator", "Мария Павлова", "OPERATOR", ()),
    ("admin", "Алексей Ким", "ADMIN", ()),
)


def seed():
    if os.getenv("APP_ENV") != "demo":
        raise SystemExit("Seeding requires APP_ENV=demo")
    password = os.environ["DEMO_PASSWORD"]
    if len(password) < 12:
        raise SystemExit("DEMO_PASSWORD must have at least 12 characters")
    with connect_engine().begin() as conn:
        for username, name, role, accounts in DEMO_USERS:
            user = one(
                conn,
                """INSERT INTO users(username,name,role,password_hash)
                           VALUES (:username,:name,:role,:hash) ON CONFLICT DO NOTHING RETURNING id""",
                username=username,
                name=name,
                role=role,
                hash=passwords.hash(password),
            )
            if user:
                for account_name, funding in accounts:
                    open_account(conn, user["id"], account_name, funding, None)
        query(conn, "DELETE FROM sessions WHERE expires_at <= clock_timestamp()")


if __name__ == "__main__":
    seed()
