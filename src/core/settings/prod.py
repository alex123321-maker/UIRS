import logging
import os

from pydantic import PostgresDsn, SecretStr

from src.core.settings.app import AppSettings


class ProdAppSettings(AppSettings):
    # fastapi_kwargs
    debug: bool = False
    title: str = "Production FastAPI application"

    # back-end app settings
    secret_key: SecretStr = SecretStr("secret-prod")
    db_url: PostgresDsn | None = None
    logging_level: int = logging.INFO
