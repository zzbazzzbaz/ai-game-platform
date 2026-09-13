from app.infra.db.engine import Engine, get_engine


class Session:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def run(self, sql: str, params: tuple = ()):
        return self._engine.run(sql, params)

    async def arun(self, sql: str, params: tuple = ()):
        return await self._engine.arun(sql, params)


def get_session() -> Session:
    return Session(get_engine())
