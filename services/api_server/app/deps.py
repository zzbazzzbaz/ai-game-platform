from typing import Annotated

from fastapi import Depends, Request

from app.infra.gateway.minio import MinioGateway
from app.infra.gateway.modal import ModalGateway


def get_modal(request: Request) -> ModalGateway:
    return request.app.state.modal


def get_minio(request: Request) -> MinioGateway:
    return request.app.state.minio


ModalDep = Annotated[ModalGateway, Depends(get_modal)]
MinioDep = Annotated[MinioGateway, Depends(get_minio)]
