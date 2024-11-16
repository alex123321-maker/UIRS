from functools import lru_cache

from src.core.settings.app import AppSettings
from src.core.settings.base import AppEnvTypes, BaseAppSettings
from src.core.settings.dev import DevAppSettings
from src.core.settings.prod import ProdAppSettings

environments: dict[AppEnvTypes, type[AppSettings]] = {
    AppEnvTypes.dev: DevAppSettings,
    AppEnvTypes.prod: ProdAppSettings,
}


@lru_cache
def get_app_settings() -> AppSettings:
    app_env = BaseAppSettings().app_env
    print(app_env)
    config = environments[app_env]
    return config()