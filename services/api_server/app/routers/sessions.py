from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.infra.db.session import SessionDep
from app.routers.auth import require_user
from app.services import session_service

router = APIRouter()


class EnsureBody(BaseModel):
    thread_id: str


@router.post("/sessions/ensure")
async def ensure(
    body: EnsureBody,
    request: Request,
    session: SessionDep,
    owner: str = Depends(require_user),
) -> dict:
    try:
        return await session_service.ensure_session(
            thread_id=body.thread_id.strip(),
            owner=owner,
            session=session,
            modal=request.app.state.modal,
            minio=request.app.state.minio,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/sessions/{thread_id}/checkpoint")
async def checkpoint(
    thread_id: str,
    request: Request,
    session: SessionDep,
    owner: str = Depends(require_user),
) -> dict:
    try:
        return await session_service.snapshot_session(
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


@router.post("/sessions/{thread_id}/close")
async def close(
    thread_id: str,
    request: Request,
    session: SessionDep,
    owner: str = Depends(require_user),
) -> dict:
    try:
        return await session_service.close_session(
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
