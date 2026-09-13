import time

from app.infra.db.session import Session

DDL = """CREATE TABLE IF NOT EXISTS thread_owners (
thread_id TEXT PRIMARY KEY,
owner TEXT NOT NULL,
created_at BIGINT NOT NULL,
updated_at BIGINT NOT NULL
)"""


async def ensure_table(session: Session) -> None:
    await session.arun(DDL)


async def get_owner(session: Session, thread_id: str) -> str | None:
    rows = await session.arun("SELECT owner FROM thread_owners WHERE thread_id=%s", (thread_id,))
    return rows[0][0] if rows else None


async def claim_owner(session: Session, thread_id: str, owner: str) -> None:
    now = int(time.time())
    await session.arun(
        "INSERT INTO thread_owners(thread_id, owner, created_at, updated_at)"
        " VALUES(%s, %s, %s, %s) ON CONFLICT(thread_id) DO NOTHING",
        (thread_id, owner, now, now),
    )
    current = await get_owner(session, thread_id)
    if current != owner:
        if current is None:
            raise ValueError(f"会话 {thread_id} 不存在")
        raise PermissionError("无权操作他人会话")
