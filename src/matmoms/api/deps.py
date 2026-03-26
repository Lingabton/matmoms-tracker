"""FastAPI dependency injection."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from matmoms.db.engine import get_session


def get_db() -> Generator[Session, None, None]:
    yield from get_session()
