import asyncio
import time

from sqlalchemy import BigInteger, Text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.infra.db.engine import get_engine


class Base(DeclarativeBase):
    pass


class ThreadOwner(Base):
    __tablename__ = "thread_owners"

    thread_id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


async def ensure_table() -> None:
    await asyncio.to_thread(Base.metadata.create_all, get_engine())


async def get_owner(session: Session, thread_id: str) -> str | None:
    row = await asyncio.to_thread(session.get, ThreadOwner, thread_id)
    return row.owner if row else None


async def claim_owner(session: Session, thread_id: str, owner: str) -> None:
    def _claim() -> str | None:
        now = int(time.time())
        session.execute(
            insert(ThreadOwner)
            .values(thread_id=thread_id, owner=owner, created_at=now, updated_at=now)
            .on_conflict_do_nothing(index_elements=["thread_id"])
        )
        session.commit()
        row = session.get(ThreadOwner, thread_id)
        return row.owner if row else None

    current = await asyncio.to_thread(_claim)
    if current != owner:
        if current is None:
            raise ValueError(f"会话 {thread_id} 不存在")
        raise PermissionError("无权操作他人会话")
