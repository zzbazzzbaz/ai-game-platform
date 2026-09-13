from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.infra.db.engine import get_session_factory


def get_session():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]
