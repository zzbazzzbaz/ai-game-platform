from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infra.db.engine import get_engine
from app.infra.db.repositories import ensure_table
from app.infra.gateway.minio import MinioGateway
from app.infra.gateway.modal import ModalGateway
from app.routers.v1 import router as v1_router
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if "*" in settings.cors_origins_list:
        raise RuntimeError("CORS_ORIGINS 不允许用 *（已开启 allow_credentials）")
    ensure_table()
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
    get_engine().dispose()


app = FastAPI(title="ai-game-api", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(v1_router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
