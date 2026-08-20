from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    database_url: str
    version: str = "v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


config = Config()
