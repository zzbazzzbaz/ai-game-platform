from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse

from app.api.dependencies import MinioDep
from app.core.constants import HTML_MEDIA_TYPE
from app.services import game_service, publish_service

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/{thread_id}/index.html")
def play_published(thread_id: str, minio: MinioDep) -> Response:
    """按 thread_id 播放最新发布的单人游戏（与 MinIO 公网链接等价，同源备选）。"""
    stream = game_service.open_game_stream(minio=minio, thread_id=thread_id)
    return StreamingResponse(stream, media_type=HTML_MEDIA_TYPE)


# —— 以下为旧版多版本试玩路由（保留，待后续清理）——


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
