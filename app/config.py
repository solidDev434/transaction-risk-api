from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    DATABASE_URL: str
    VERSION: str = "v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


config = Config()
