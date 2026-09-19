from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import API_V1_PREFIX, Settings, get_settings
from app.core.database import create_all, create_db_engine, create_session_factory
from app.gateways.minio import MinioGateway
from app.gateways.modal import ModalGateway


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings if settings is not None else get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        engine = create_db_engine(resolved_settings.sqlalchemy_database_url)
        create_all(engine)
        application.state.engine = engine
        application.state.session_factory = create_session_factory(engine)
        minio = MinioGateway(
            endpoint_url=resolved_settings.s3_endpoint_url,
            bucket=resolved_settings.s3_bucket,
            path_style=resolved_settings.s3_path_style,
            access_key=resolved_settings.s3_access_key,
            secret_key=resolved_settings.s3_secret_key,
        )
        minio.ensure_bucket()
        application.state.minio = minio
        application.state.modal = ModalGateway(
            app_name=resolved_settings.modal_app,
            idle_timeout=resolved_settings.modal_idle_timeout_seconds,
            timeout=resolved_settings.modal_timeout_seconds,
        )
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="ai-game-api", version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.state.settings = resolved_settings
    application.include_router(api_router, prefix=API_V1_PREFIX)
    return application


app = create_app()
