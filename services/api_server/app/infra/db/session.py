from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.infra.db.engine import get_session_factory


def get_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
