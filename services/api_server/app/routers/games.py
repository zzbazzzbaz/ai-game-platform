from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.infra.db.session import SessionDep
from app.routers.auth import require_user, require_user_flexible
from app.services import publish_service
from app.services.publish_service import MAX_INPUT_BYTES

router = APIRouter()
HTML_MEDIA_TYPE = "text/html; charset=utf-8"
UPLOAD_CHUNK = 1024 * 256


@router.post("/sessions/{thread_id}/publish")
async def publish(
    thread_id: str,
    request: Request,
    session: SessionDep,
    owner: str = Depends(require_user),
) -> dict:
    try:
        return await publish_service.publish_version(
            thread_id=thread_id,
            owner=owner,
            session=session,
            modal=request.app.state.modal,
            minio=request.app.state.minio,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{thread_id}/versions")
async def versions(
    thread_id: str,
    request: Request,
    session: SessionDep,
    owner: str = Depends(require_user),
) -> dict:
    try:
        items = await publish_service.list_versions(
            thread_id=thread_id, owner=owner, session=session, minio=request.app.state.minio
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"versions": items}


@router.post("/sessions/{thread_id}/input")
async def upload_input(
    thread_id: str,
    file: UploadFile,
    request: Request,
    session: SessionDep,
    owner: str = Depends(require_user),
) -> dict:
    filename = (file.filename or "").split("/")[-1].split("\\")[-1]
    try:
        data = await _read_capped(file)
        return await publish_service.store_input(
            thread_id=thread_id,
            owner=owner,
            filename=filename,
            data=data,
            content_type=file.content_type or "application/octet-stream",
            session=session,
            minio=request.app.state.minio,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


async def _read_capped(file: UploadFile) -> bytes:
    if file.size is not None and file.size > MAX_INPUT_BYTES:
        raise ValueError("素材超过 5MB")
    chunks, total = [], 0
    while True:
        chunk = await file.read(UPLOAD_CHUNK)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > MAX_INPUT_BYTES:
            raise ValueError("素材超过 5MB")
        chunks.append(chunk)


@router.get("/games/{thread_id}/{version}/index.html")
async def play(
    thread_id: str,
    version: str,
    request: Request,
    session: SessionDep,
    owner: str = Depends(require_user_flexible),
) -> Response:
    try:
        resolved = await publish_service.resolve_version(
            thread_id=thread_id,
            owner=owner,
            version=version,
            session=session,
            minio=request.app.state.minio,
        )
        stream = await publish_service.open_version_stream(
            minio=request.app.state.minio, thread_id=thread_id, version=resolved
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "不存在" in str(e) or "还没有" in str(e) else 400, detail=str(e)
        ) from e
    return StreamingResponse(stream, media_type=HTML_MEDIA_TYPE)


@router.get("/games/{thread_id}/{version}/download")
async def download(
    thread_id: str,
    version: str,
    request: Request,
    session: SessionDep,
    owner: str = Depends(require_user_flexible),
) -> Response:
    try:
        html = await publish_service.get_version_bytes(
            thread_id=thread_id,
            owner=owner,
            version=version,
            session=session,
            minio=request.app.state.minio,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "不存在" in str(e) or "还没有" in str(e) else 400, detail=str(e)
        ) from e
    return Response(
        content=html,
        media_type=HTML_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename=game-{version}.html"},
    )
