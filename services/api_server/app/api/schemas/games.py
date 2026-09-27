from pydantic import BaseModel


class PublishGameBody(BaseModel):
    thread_id: str
    user_id: str
    name: str = ""


class PublishGameResponse(BaseModel):
    thread_id: str
    size: int
    url: str
