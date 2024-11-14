from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel, SecurityScheme as SecuritySchemeModel


from src.api.v1 import api_router
from src.core import settings
from src.core.events import create_start_app_handler, create_stop_app_handler
from src.utils import (
    CustomizeLogger,
)

config_path = Path(__file__).with_name("logging_conf.json")


def create_app() -> FastAPI:
    _app = FastAPI(**settings.fastapi_kwargs)

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _app.logger = CustomizeLogger.make_logger(config_path)
    _app.include_router(api_router, prefix=settings.api_v1_prefix)

    @_app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=_app.openapi_url,
            title=_app.title + " - Swagger UI custom",
            oauth2_redirect_url=_app.swagger_ui_oauth2_redirect_url,
        )

    @_app.get(_app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    @_app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=_app.openapi_url,
            title=_app.title + " - ReDoc",
        )

    _app.add_event_handler("startup", create_start_app_handler(_app, settings))
    _app.add_event_handler("shutdown", create_stop_app_handler(_app))


    return _app


app = create_app()