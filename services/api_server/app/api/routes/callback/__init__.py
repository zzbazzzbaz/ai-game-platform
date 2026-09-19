from fastapi import APIRouter

from app.api.routes.callback import internal

router = APIRouter(prefix="/callback")
router.include_router(internal.router)
