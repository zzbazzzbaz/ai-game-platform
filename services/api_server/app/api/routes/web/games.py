from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from app.api.dependencies import MinioDep
from app.services import publish_service
from app.services.publish_service import NotFoundError

router = APIRouter(prefix="/games", tags=["games"])
HTML_MEDIA_TYPE = "text/html; charset=utf-8"


@router.get("/{thread_id}/{version}/index.html")
def play(thread_id: str, version: str, minio: MinioDep) -> Response:
    try:
        resolved = publish_service.resolve_version(
            thread_id=thread_id,
            version=version,
            minio=minio,
        )
        stream = publish_service.open_version_stream(
            minio=minio, thread_id=thread_id, version=resolved
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return StreamingResponse(stream, media_type=HTML_MEDIA_TYPE)


@router.get("/{thread_id}/{version}/download")
def download(thread_id: str, version: str, minio: MinioDep) -> Response:
    try:
        html = publish_service.get_version_bytes(
            thread_id=thread_id,
            version=version,
            minio=minio,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return Response(
        content=html,
        media_type=HTML_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename=game-{version}.html"},
    )
