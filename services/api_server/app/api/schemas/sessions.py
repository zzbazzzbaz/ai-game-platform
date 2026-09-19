from pydantic import BaseModel


class EnsureBody(BaseModel):
    thread_id: str


class EnsureResponse(BaseModel):
    thread_id: str
    sandbox_id: str
    restored_files: int
    manifest_match: bool


class CheckpointResponse(BaseModel):
    thread_id: str
    checkpoint: str
    files: int


class PublishResponse(BaseModel):
    thread_id: str
    version: str
    size: int


class VersionItem(BaseModel):
    n: int
    version: str
    size: int


class VersionsResponse(BaseModel):
    versions: list[VersionItem]


class InputResponse(BaseModel):
    filename: str
    size: int
