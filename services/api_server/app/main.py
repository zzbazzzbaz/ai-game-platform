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
        endpoint_url=settings.s3_endpoint_url,
        bucket=settings.s3_bucket,
        path_style=settings.s3_path_style,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
    )
    minio.ensure_bucket()
    app.state.minio = minio
    app.state.modal = ModalGateway(
        app_name=settings.modal_app,
        idle_timeout=settings.modal_idle_timeout_seconds,
        timeout=settings.modal_timeout_seconds,
    )
    yield


app = FastAPI(title="ai-game-api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
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
