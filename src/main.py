import os
from pathlib import Path
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from starlette.staticfiles import StaticFiles
from sqlalchemy import select

from src.api.v1 import api_router
from src.core import settings
from src.core.events import create_start_app_handler, create_stop_app_handler
from src.database.events import logger
from src.utils.custom_logging import CustomizeLogger
from src.models.recipe import Ingredient  # Ваша модель
from src.utils.init_ingredients import init_ingredients
from src.utils.init_units import init_units

config_path = Path(__file__).with_name("logging_conf.json")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Функция lifespan заменяет on_event("startup") и on_event("shutdown").
    """
    # 1) Подключаемся к БД и т.п.
    await create_start_app_handler(app, settings)()

    # 2) Инициализируем ингредиенты
    await init_ingredients(app)
    await init_units(app)

    # Переходим в "приложение запущено"
    yield

    # 3) Логика при остановке приложения
    await create_stop_app_handler(app)()


def create_app() -> FastAPI:
    _app = FastAPI(**settings.fastapi_kwargs, lifespan=lifespan)

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _app.mount("/media", StaticFiles(directory="media"), name="media")
    _app.mount("/static", StaticFiles(directory="static"), name="static")

    _app.logger = CustomizeLogger.make_logger(config_path)
    _app.include_router(api_router, prefix=settings.api_v1_prefix)

    @_app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html() -> HTMLResponse:
        original_html = get_swagger_ui_html(
            openapi_url=_app.openapi_url,
            title=_app.title + " - Swagger UI custom",
            oauth2_redirect_url=_app.swagger_ui_oauth2_redirect_url,
        )
        original_html_str = original_html.body.decode("utf-8")
        custom_css_link = '<link rel="stylesheet" type="text/css" href="/static/swagger_custom.css"/>'
        new_html = original_html_str.replace("<head>", f"<head>{custom_css_link}\n")
        return HTMLResponse(new_html)

    @_app.get(_app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect() -> HTMLResponse:
        return get_swagger_ui_oauth2_redirect_html()

    @_app.get("/redoc", include_in_schema=False)
    async def redoc_html() -> HTMLResponse:
        return get_redoc_html(
            openapi_url=_app.openapi_url,
            title=_app.title + " - ReDoc",
        )

    return _app


app = create_app()
