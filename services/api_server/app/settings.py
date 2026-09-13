from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    S3_ENDPOINT_URL: str
    S3_BUCKET: str
    S3_PATH_STYLE: bool
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    MODAL_TOKEN_ID: str
    MODAL_TOKEN_SECRET: str
    MODAL_APP: str
    MODAL_IDLE_TIMEOUT_SECONDS: int
    MODAL_TIMEOUT_SECONDS: int
    AUTH_SECRET: str
    AUTH_INTERNAL_TOKEN: str
    AUTH_TOKEN_TTL_SECONDS: int

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
