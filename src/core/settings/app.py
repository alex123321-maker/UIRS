from pathlib import Path
from typing import Any

from pydantic import ConfigDict, SecretStr

from src.core.settings.base import BaseAppSettings


class AppSettings(BaseAppSettings):
    model_config = ConfigDict(
        validate_assignment=True,
    )


    BASE_DIR: str = str(Path(__file__).resolve().parent.parent.parent.parent)

    debug: bool = False
    docs_url: str | None =None
    openapi_prefix: str = ""
    openapi_url: str = "/openapi.json"
    redoc_url: str = "/redoc"
    title: str = "FastAPI example application"
    version: str = "0.7.3"

    # back-end app settings
    api_v1_prefix: str = "/api/v1"
    secret_key: SecretStr
    auth_header_key: str = "Authorization"
    allowed_hosts: list[str] = ["*"]

    @property
    def fastapi_kwargs(self) -> dict[str, Any]:
        return {
            "debug": self.debug,
            "docs_url": self.docs_url,
            "openapi_prefix": self.openapi_prefix,
            "openapi_url": self.openapi_url,
            "redoc_url": self.redoc_url,
            "title": self.title,
            "version": self.version,
        }