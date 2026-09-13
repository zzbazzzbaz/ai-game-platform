import time

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.infra.db.engine import get_engine
from app.infra.db.models import Base, ThreadOwner


def ensure_table() -> None:
    Base.metadata.create_all(get_engine())


def get_owner(session: Session, thread_id: str) -> str | None:
    row = session.get(ThreadOwner, thread_id)
    return row.owner if row else None


def claim_owner(session: Session, thread_id: str, owner: str) -> None:
    now = int(time.time())
    session.execute(
        insert(ThreadOwner)
        .values(thread_id=thread_id, owner=owner, created_at=now, updated_at=now)
        .on_conflict_do_nothing(index_elements=["thread_id"])
    )
    session.commit()
    row = session.get(ThreadOwner, thread_id)
    current = row.owner if row else None
    if current != owner:
        if current is None:
            raise ValueError(f"会话 {thread_id} 不存在")
        raise PermissionError("无权操作他人会话")
