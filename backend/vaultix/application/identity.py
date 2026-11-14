import hashlib
import secrets
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import Engine

from vaultix.application.ledger import audit
from vaultix.domain.rules import BusinessError, Role
from vaultix.infrastructure.db import one, query

passwords = PasswordHasher()
UNKNOWN_HASH = passwords.hash(secrets.token_urlsafe(32))
PUBLIC_USER = "id, username, name, role, active"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(engine: Engine, username: str, password: str, request_id: UUID) -> str:
    with engine.begin() as conn:
        user = one(
            conn,
            "SELECT * FROM users WHERE username=:username FOR SHARE",
            username=username,
        )
        try:
            valid = passwords.verify(
                user["password_hash"] if user else UNKNOWN_HASH, password
            )
        except VerifyMismatchError:
            valid = False
        if user and user["active"] and valid:
            token = secrets.token_urlsafe(32)
            query(
                conn,
                """INSERT INTO sessions VALUES
                         (:token, :user, clock_timestamp() + interval '8 hours')""",
                user=user["id"],
                token=token_hash(token),
            )
            audit(conn, request_id, "LOGIN", "SUCCESS", user["id"])
            return token
        audit(
            conn,
            request_id,
            "LOGIN",
            "INVALID_CREDENTIALS",
            user["id"] if user else None,
        )
    raise BusinessError(401, "INVALID_CREDENTIALS")


def current_user(engine: Engine, token: str | None) -> dict:
    if token:
        with engine.connect() as conn:
            user = one(
                conn,
                """SELECT u.id, u.username, u.name, u.role, u.active
                       FROM sessions s JOIN users u ON u.id=s.user_id
                       WHERE s.token_hash=:token AND s.expires_at > clock_timestamp() AND u.active""",
                token=token_hash(token),
            )
        if user:
            return user
    raise BusinessError(401, "AUTH_REQUIRED")


def create_user(
    engine: Engine,
    actor: UUID,
    request_id: UUID,
    username: str,
    name: str,
    password: str,
    role: Role,
) -> dict:
    digest = passwords.hash(password)
    with engine.begin() as conn:
        user = one(
            conn,
            f"""INSERT INTO users(username, name, password_hash, role)
                         VALUES (:username, :name, :digest, :role)
                         ON CONFLICT (username) DO NOTHING RETURNING {PUBLIC_USER}""",
            username=username,
            name=name,
            digest=digest,
            role=role,
        )
        if user is None:
            raise BusinessError(409, "USERNAME_EXISTS")
        audit(conn, request_id, "USER_CREATE", "SUCCESS", actor, user["id"])
        return user


def set_customer_active(
    engine: Engine, actor: UUID, request_id: UUID, target: UUID, active: bool
) -> dict:
    with engine.begin() as conn:
        user = one(
            conn,
            f"""UPDATE users SET active=:active WHERE id=:id AND role='CUSTOMER'
                            RETURNING {PUBLIC_USER}""",
            id=target,
            active=active,
        )
        if user is None:
            raise BusinessError(404, "CUSTOMER_NOT_FOUND")
        if not active:
            query(conn, "DELETE FROM sessions WHERE user_id=:user", user=target)
        audit(
            conn,
            request_id,
            "USER_STATUS",
            "ACTIVE" if active else "DISABLED",
            actor,
            target,
        )
        return user
