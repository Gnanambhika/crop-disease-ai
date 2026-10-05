"""Atomic, shared PostgreSQL limits; SQLite supported for automated tests."""
import hashlib
import hmac
import time

from fastapi import Depends, HTTPException, Request
from sqlalchemy import case, delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.models.auth_limit import AuthRateLimit


def consume_attempt(db: Session, key: str, limit: int, window: int, now: int) -> int:
    dialect = db.get_bind().dialect.name
    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise RuntimeError('Authentication limits require PostgreSQL or SQLite')
    table = AuthRateLimit
    expired = table.expires_at <= now
    statement = insert(table).values(bucket_key=key, expires_at=now + window, attempts=1)
    statement = statement.on_conflict_do_update(
        index_elements=[table.bucket_key],
        set_={'attempts': case((expired, 1), else_=table.attempts + 1),
              'expires_at': case((expired, now + window), else_=table.expires_at)},
    ).returning(table.attempts, table.expires_at)
    attempts, expiry = db.execute(statement).one()
    db.execute(delete(table).where(table.expires_at < now - 86400))
    db.commit()  # Keep the consumed attempt even if authentication fails.
    return max(1, expiry - now) if attempts > limit else 0


def limit_authentication(request: Request, db: Session = Depends(get_db)) -> None:
    settings = get_settings()
    register = request.url.path.endswith('/register')
    limit = settings.auth_register_limit if register else settings.auth_login_limit
    window = settings.auth_register_window if register else settings.auth_login_window
    address = request.client.host if request.client else 'unknown'
    # No raw IP/email stored; forwarded headers are handled only by a trusted proxy.
    key = hmac.new(settings.jwt_secret.encode(),
                   f'{request.url.path}:{address}'.encode(), hashlib.sha256).hexdigest()
    retry = consume_attempt(db, key, limit, window, int(time.time()))
    if retry:
        raise HTTPException(429, 'Too many sign-in or registration attempts. Please try again later.',
                            headers={'Retry-After': str(retry)})
