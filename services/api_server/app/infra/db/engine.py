from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker


def create_db_engine(dsn: str) -> Engine:
    return create_engine(dsn, pool_pre_ping=True)


def create_session_factory(engine: Engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
