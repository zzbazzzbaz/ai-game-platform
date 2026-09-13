from fastapi import APIRouter

from app.api.routes.admin import internal

router = APIRouter()
router.include_router(internal.router)
