from enum import Enum

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvTypes(Enum):
    prod: str = "prod"
    dev: str = "dev"


class BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict()

    app_env: AppEnvTypes = AppEnvTypes.dev

    db_url: PostgresDsn | None = None

