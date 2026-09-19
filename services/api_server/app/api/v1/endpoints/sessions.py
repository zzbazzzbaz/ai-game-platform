from fastapi import APIRouter, HTTPException, UploadFile

from app.api.dependencies import MinioDep, ModalDep, SessionDep, UserIdDep
from app.api.schemas.sessions import (
    CheckpointResponse,
    EnsureBody,
    EnsureResponse,
    InputResponse,
    PublishResponse,
    VersionsResponse,
)
from app.services import publish_service, session_service
from app.services.publish_service import MAX_INPUT_BYTES

router = APIRouter(prefix="/sessions", tags=["sessions"])
UPLOAD_CHUNK = 1024 * 256


@router.post("/ensure", response_model=EnsureResponse)
def ensure(
    body: EnsureBody, session: SessionDep, modal: ModalDep, minio: MinioDep, user_id: UserIdDep
) -> dict:
    try:
        return session_service.ensure_session(
            thread_id=body.thread_id.strip(),
            user_id=user_id,
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


@router.post("/{thread_id}/checkpoint", response_model=CheckpointResponse)
def checkpoint(
    thread_id: str, session: SessionDep, modal: ModalDep, minio: MinioDep, user_id: UserIdDep
) -> dict:
    try:
        return session_service.snapshot_session(
            thread_id=thread_id,
            user_id=user_id,
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


@router.post("/{thread_id}/close", response_model=CheckpointResponse)
def close(
    thread_id: str, session: SessionDep, modal: ModalDep, minio: MinioDep, user_id: UserIdDep
) -> dict:
    try:
        return session_service.close_session(
            thread_id=thread_id,
            user_id=user_id,
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


@router.post("/{thread_id}/publish", response_model=PublishResponse)
def publish(
    thread_id: str, session: SessionDep, modal: ModalDep, minio: MinioDep, user_id: UserIdDep
) -> dict:
    try:
        return publish_service.publish_version(
            thread_id=thread_id,
            user_id=user_id,
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


@router.get("/{thread_id}/versions", response_model=VersionsResponse)
def versions(thread_id: str, session: SessionDep, minio: MinioDep, user_id: UserIdDep) -> dict:
    try:
        items = publish_service.list_versions(
            thread_id=thread_id, user_id=user_id, session=session, minio=minio
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"versions": items}


@router.post("/{thread_id}/input", response_model=InputResponse)
def upload_input(
    thread_id: str,
    file: UploadFile,
    session: SessionDep,
    minio: MinioDep,
    user_id: UserIdDep,
) -> dict:
    filename = (file.filename or "").split("/")[-1].split("\\")[-1]
    try:
        data = _read_capped(file)
        return publish_service.store_input(
            thread_id=thread_id,
            user_id=user_id,
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
