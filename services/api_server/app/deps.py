from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.infra.db.session import get_session
from app.infra.gateway.minio import MinioGateway
from app.infra.gateway.modal import ModalGateway


def get_modal(request: Request) -> ModalGateway:
    return request.app.state.modal


def get_minio(request: Request) -> MinioGateway:
    return request.app.state.minio


SessionDep = Annotated[Session, Depends(get_session)]
ModalDep = Annotated[ModalGateway, Depends(get_modal)]
MinioDep = Annotated[MinioGateway, Depends(get_minio)]
