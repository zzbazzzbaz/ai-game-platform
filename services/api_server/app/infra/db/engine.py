import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings import get_settings

POOL_SIZE = 5
POOL_RECYCLE = 1800
POOL_TIMEOUT = 30


_engine = None
_SessionFactory = None
_engine_lock = threading.Lock()


def get_engine():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = create_engine(
                    get_settings().sqlalchemy_database_url,
                    pool_size=POOL_SIZE,
                    pool_recycle=POOL_RECYCLE,
                    pool_timeout=POOL_TIMEOUT,
                    pool_pre_ping=True,
                )
    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionFactory
