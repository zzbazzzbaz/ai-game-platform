from fastapi import APIRouter

from app.api.routes.web import auth, games, sessions

router = APIRouter(prefix="/web")
router.include_router(auth.router)
router.include_router(sessions.router)
router.include_router(games.router)
