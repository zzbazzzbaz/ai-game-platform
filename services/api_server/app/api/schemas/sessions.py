from pydantic import BaseModel


class EnsureBody(BaseModel):
    thread_id: str
