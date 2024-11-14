from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvTypes(Enum):
    prod: str = "prod"
    dev: str = "dev"


class BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_env: AppEnvTypes = AppEnvTypes.dev

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_port: int
    listen_addresses: str