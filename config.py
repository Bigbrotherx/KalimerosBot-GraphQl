import contextlib
import dataclasses
from functools import lru_cache

import grpc
from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    domain: str
    api_audience: str
    issuer: str
    algorithms: str
    client_id: str
    client_secret: str
    scopes: str
    dictionary_service_uri: str
    dictionary_service_port: str

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


@contextlib.contextmanager
def get_dictionary_service_channel():
    settings = get_settings()
    yield grpc.insecure_channel(
            f"{settings.dictionary_service_uri}:"
            f"{settings.dictionary_service_port}")
