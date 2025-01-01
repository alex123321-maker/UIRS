import logging

from pydantic import PostgresDsn, SecretStr

from src.core.settings.app import AppSettings


class DevAppSettings(AppSettings):
    # fastapi_kwargs
    debug: bool = True
    title: str = "Fastapi app"

    # back-end app settings
    secret_key: SecretStr = SecretStr("secret-dev")

    db_url: PostgresDsn | None = None
    logging_level: int = logging.DEBUG

