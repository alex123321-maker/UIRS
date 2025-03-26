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
from src.utils.custom_logging import CustomizeLogger
from src.models.recipe import Ingredient  # Ваша модель

config_path = Path(__file__).with_name("logging_conf.json")
STATIC_INGREDIENTS_PATH = Path("static/ingredients")
CONFIG_FILE_PATH = "src/ingredients_config.yaml"
async def init_ingredients(app: FastAPI) -> None:
    """
    Функция, которая читает ingredients_config.yaml и добавляет
    новые ингредиенты в БД. Если icon_url пустая или неправильная,
    пытаемся найти файл в папке static/ingredients. Если ничего
    не нашли, ставим null и обновляем YAML-файл.
    """

    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)  # список словарей
    except FileNotFoundError:
        app.logger.error(f"Файл {CONFIG_FILE_PATH} не найден.")
        return

    if not isinstance(config_data, list):
        app.logger.error("Формат ingredients_config.yaml некорректен: ожидается список.")
        return

    # 2) Перебираем ингредиенты, корректируем icon_url
    async with app.state.pool() as session:
        for item in config_data:
            # Если какие-то поля могут отсутствовать - обрабатываем
            name = item.get("name", "").strip()
            icon_url = item.get("icon_url", "")
            icon_url = icon_url.strip() if icon_url else ""

            # Если URL не пустой, проверяем файл:
            #   - Если не существует, ставим None (обновляем конфиг).
            if icon_url:
                file_path = Path(icon_url)
                if not file_path.exists():
                    # Файл не найден по заданному icon_url, значит ставим None.
                    app.logger.warning(f"Указанный путь к иконке не найден: {icon_url}")
                    icon_url = None
            else:
                possible_extensions = [".png", ".jpg", ".jpeg", ".svg"]
                found_file = None
                for ext in possible_extensions:
                    file_path = STATIC_INGREDIENTS_PATH / f"{name}{ext}"
                    if file_path.exists():
                        found_file = str(file_path)
                        break
                icon_url = found_file if found_file else None

            # Обновляем в item (для дальнейшей записи в YAML)
            item["icon_url"] = icon_url

            result = await session.execute(
                select(Ingredient).filter_by(name=name)
            )
            ingredient_in_db = result.scalars().first()

            if not ingredient_in_db:
                # Раз не нашли в БД, добавляем
                new_ingredient = Ingredient(
                    name=name,
                    icon_url=icon_url,
                )
                session.add(new_ingredient)
            else:
                if ingredient_in_db.icon_url != icon_url:
                    ingredient_in_db.icon_url = icon_url

        await session.commit()

    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        app.logger.info("ingredients_config.yaml успешно обновлён.")
    except Exception as e:
        app.logger.error(f"Не удалось сохранить изменения в {CONFIG_FILE_PATH}: {e}")

    app.logger.info("Ингредиенты успешно инициализированы.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Функция lifespan заменяет on_event("startup") и on_event("shutdown").
    """
    # 1) Подключаемся к БД и т.п.
    await create_start_app_handler(app, settings)()

    # 2) Инициализируем ингредиенты
    await init_ingredients(app)

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
