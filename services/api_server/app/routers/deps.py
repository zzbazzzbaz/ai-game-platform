from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.infra.db.session import get_session
from app.infra.gateway.minio import MinioGateway
from app.infra.gateway.modal import ModalGateway
from app.services.auth_service import verify_token


def get_modal(request: Request) -> ModalGateway:
    return request.app.state.modal


def get_minio(request: Request) -> MinioGateway:
    return request.app.state.minio


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def require_user(request: Request) -> str:
    user_id = verify_token(_bearer(request) or "")
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return user_id


def require_user_flexible(request: Request, token: str = Query(default="")) -> str:
    user_id = verify_token(_bearer(request) or token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return user_id


SessionDep = Annotated[Session, Depends(get_session)]
ModalDep = Annotated[ModalGateway, Depends(get_modal)]
MinioDep = Annotated[MinioGateway, Depends(get_minio)]
UserDep = Annotated[str, Depends(require_user)]
FlexibleUserDep = Annotated[str, Depends(require_user_flexible)]
