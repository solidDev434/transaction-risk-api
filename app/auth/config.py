from datetime import timedelta
from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    JWT_ALG: str = "HS256"
    JWT_SECRET: str
    JWT_EXP: int = 15

    REFRESH_TOKEN_KEY: str
    REFRESH_TOKEN_EXP: timedelta = timedelta(days=30)


auth_config = AuthConfig()
