import logging

from pydantic import PostgresDsn, SecretStr

from src.core.settings.app import AppSettings


class DevAppSettings(AppSettings):
    # fastapi_kwargs
    debug: bool = True
    title: str = "Dev FastAPI application"

    # back-end app settings
    secret_key: SecretStr = SecretStr("secret-dev")
    db_url: PostgresDsn | None = None
    logging_level: int = logging.DEBUG

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db_url = PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.listen_addresses,
            port=int(self.postgres_port),
            path=f"{self.postgres_db}"
        )