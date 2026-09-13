from fastapi import APIRouter

from app.routers.v1 import auth, games, sessions

router = APIRouter(prefix="/v1")
router.include_router(auth.router)
router.include_router(sessions.router)
router.include_router(games.router)
