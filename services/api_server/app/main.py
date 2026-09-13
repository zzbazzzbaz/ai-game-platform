from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infra.db.models import ensure_table
from app.infra.gateway.minio import MinioGateway
from app.infra.gateway.modal import ModalGateway
from app.routers import auth, games, sessions
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await ensure_table()
    minio = MinioGateway(
        endpoint_url=settings.S3_ENDPOINT_URL,
        bucket=settings.S3_BUCKET,
        path_style=settings.S3_PATH_STYLE,
        access_key=settings.S3_ACCESS_KEY,
        secret_key=settings.S3_SECRET_KEY,
    )
    minio.ensure_bucket()
    app.state.minio = minio
    app.state.modal = ModalGateway(
        app_name=settings.MODAL_APP,
        idle_timeout=settings.MODAL_IDLE_TIMEOUT_SECONDS,
        timeout=settings.MODAL_TIMEOUT_SECONDS,
    )
    yield


app = FastAPI(title="ai-game-api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.router.lifespan_context = lifespan
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(games.router)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}
