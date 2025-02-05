from functools import lru_cache

from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    domain: str
    api_audience: str
    issuer: str
    algorithms: str
    client_id: str
    client_secret: str
    scopes: str

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
