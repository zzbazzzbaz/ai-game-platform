import asyncio
import queue
from contextlib import contextmanager
from typing import Any

import psycopg

POOL_MAXSIZE = 5


class Engine:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: queue.Queue[psycopg.Connection] = queue.Queue(maxsize=POOL_MAXSIZE)

    def _checkout(self) -> psycopg.Connection:
        try:
            conn = self._pool.get_nowait()
        except queue.Empty:
            return psycopg.connect(self._dsn, autocommit=True)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return conn
        except psycopg.Error:
            conn.close()
            return psycopg.connect(self._dsn, autocommit=True)

    def _checkin(self, conn: psycopg.Connection) -> None:
        if conn.closed:
            return
        try:
            self._pool.put_nowait(conn)
        except queue.Full:
            conn.close()

    @contextmanager
    def _connection(self):
        conn = self._checkout()
        try:
            yield conn
        finally:
            self._checkin(conn)

    def run(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall() if cur.description else []

    async def arun(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        return await asyncio.to_thread(self.run, sql, params)


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        from app.settings import get_settings

        _engine = Engine(get_settings().database_url)
    return _engine
