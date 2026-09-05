from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    ASYNC_DATABASE_URL: str
    SYNC_DATABASE_URL: str
    VERSION: str = "v1"
    REDIS_URL: str = "redis://localhost:6379/0"
    MAX_ATTEMPTS: int

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


config = Config()
