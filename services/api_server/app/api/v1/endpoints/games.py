from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse

from app.api.dependencies import MinioDep
from app.services import publish_service

router = APIRouter(prefix="/games", tags=["games"])
HTML_MEDIA_TYPE = "text/html; charset=utf-8"


@router.get("/{thread_id}/{version}/index.html")
def play(thread_id: str, version: str, minio: MinioDep) -> Response:
    resolved = publish_service.resolve_version(
        thread_id=thread_id,
        version=version,
        minio=minio,
    )
    stream = publish_service.open_version_stream(
        minio=minio, thread_id=thread_id, version=resolved
    )
    return StreamingResponse(stream, media_type=HTML_MEDIA_TYPE)


@router.get("/{thread_id}/{version}/download")
def download(thread_id: str, version: str, minio: MinioDep) -> Response:
    html = publish_service.get_version_bytes(
        thread_id=thread_id,
        version=version,
        minio=minio,
    )
    return Response(
        content=html,
        media_type=HTML_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename=game-{version}.html"},
    )
