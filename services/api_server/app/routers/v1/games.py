from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.routers.deps import FlexibleUserDep, MinioDep, ModalDep, SessionDep, UserDep
from app.services import publish_service
from app.services.publish_service import MAX_INPUT_BYTES, NotFoundError

router = APIRouter()
HTML_MEDIA_TYPE = "text/html; charset=utf-8"
UPLOAD_CHUNK = 1024 * 256


@router.post("/sessions/{thread_id}/publish")
def publish(
    thread_id: str, session: SessionDep, modal: ModalDep, minio: MinioDep, owner: UserDep
) -> dict:
    try:
        return publish_service.publish_version(
            thread_id=thread_id,
            owner=owner,
            session=session,
            modal=modal,
            minio=minio,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{thread_id}/versions")
def versions(thread_id: str, session: SessionDep, minio: MinioDep, owner: UserDep) -> dict:
    try:
        items = publish_service.list_versions(
            thread_id=thread_id, owner=owner, session=session, minio=minio
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"versions": items}


@router.post("/sessions/{thread_id}/input")
def upload_input(
    thread_id: str,
    file: UploadFile,
    session: SessionDep,
    minio: MinioDep,
    owner: UserDep,
) -> dict:
    filename = (file.filename or "").split("/")[-1].split("\\")[-1]
    try:
        data = _read_capped(file)
        return publish_service.store_input(
            thread_id=thread_id,
            owner=owner,
            filename=filename,
            data=data,
            content_type=file.content_type or "application/octet-stream",
            session=session,
            minio=minio,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def _read_capped(file: UploadFile) -> bytes:
    if file.size is not None and file.size > MAX_INPUT_BYTES:
        raise ValueError("素材超过 5MB")
    chunks, total = [], 0
    while True:
        chunk = file.file.read(UPLOAD_CHUNK)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > MAX_INPUT_BYTES:
            raise ValueError("素材超过 5MB")
        chunks.append(chunk)


@router.get("/games/{thread_id}/{version}/index.html")
def play(
    thread_id: str,
    version: str,
    session: SessionDep,
    minio: MinioDep,
    owner: FlexibleUserDep,
) -> Response:
    try:
        resolved = publish_service.resolve_version(
            thread_id=thread_id,
            owner=owner,
            version=version,
            session=session,
            minio=minio,
        )
        stream = publish_service.open_version_stream(
            minio=minio, thread_id=thread_id, version=resolved
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return StreamingResponse(stream, media_type=HTML_MEDIA_TYPE)


@router.get("/games/{thread_id}/{version}/download")
def download(
    thread_id: str,
    version: str,
    session: SessionDep,
    minio: MinioDep,
    owner: FlexibleUserDep,
) -> Response:
    try:
        html = publish_service.get_version_bytes(
            thread_id=thread_id,
            owner=owner,
            version=version,
            session=session,
            minio=minio,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
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
