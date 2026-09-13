from fastapi import APIRouter, HTTPException

from app.api.dependencies import MinioDep, ModalDep, SessionDep, UserDep
from app.api.schemas.sessions import EnsureBody
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/ensure")
def ensure(
    body: EnsureBody, session: SessionDep, modal: ModalDep, minio: MinioDep, owner: UserDep
) -> dict:
    try:
        return session_service.ensure_session(
            thread_id=body.thread_id.strip(),
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


@router.post("/{thread_id}/checkpoint")
def checkpoint(
    thread_id: str, session: SessionDep, modal: ModalDep, minio: MinioDep, owner: UserDep
) -> dict:
    try:
        return session_service.snapshot_session(
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


@router.post("/{thread_id}/close")
def close(
    thread_id: str, session: SessionDep, modal: ModalDep, minio: MinioDep, owner: UserDep
) -> dict:
    try:
        return session_service.close_session(
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
