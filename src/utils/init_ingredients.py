import logging
from pathlib import Path

import yaml
from fastapi import FastAPI
from sqlalchemy import select

from src.models.recipe import Ingredient

CONFIG_FILE_PATH = "src/ingredients_config.yaml"
STATIC_INGREDIENTS_PATH = Path("static/ingredients")
logger = logging.getLogger(__name__)



async def init_ingredients(app: FastAPI) -> None:
    """
    Функция, которая читает ingredients_config.yaml и:
      1) Добавляет/обновляет ингредиенты из конфига.
      2) Удаляет из базы все ингредиенты, не указанные в конфиге.
      3) Если icon_url пустая или неправильная, пытается найти файл в папке static/ingredients.
         Если не нашли, ставим null и обновляем YAML.
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

    # Соберём названия из конфига в множество, чтобы удобнее проверять
    config_names = set()

    # Открываем сессию
    async with app.state.pool() as session:
        # ============================
        # 1) Добавляем/обновляем
        # ============================
        for item in config_data:
            name = item.get("name", "").strip()
            icon_url = item.get("icon_url", "")
            icon_url = icon_url.strip() if icon_url else ""

            config_names.add(name)

            # Проверяем существование файла, если путь задан
            if icon_url:
                file_path = Path(icon_url)
                if not file_path.exists():
                    app.logger.warning(f"Указанный путь к иконке не найден: {icon_url}")
                    icon_url = None
            else:
                # Ищем файл в папке static/ingredients
                possible_extensions = [".png", ".jpg", ".jpeg", ".svg"]
                found_file = None
                for ext in possible_extensions:
                    file_path = STATIC_INGREDIENTS_PATH / f"{name}{ext}"
                    if file_path.exists():
                        found_file = str(file_path)
                        break
                icon_url = found_file if found_file else None

            # Обновляем в item (для записи в YAML)
            item["icon_url"] = icon_url

            # Ищем в БД
            result = await session.execute(
                select(Ingredient).filter_by(name=name)
            )
            ingredient_in_db = result.scalars().first()

            if not ingredient_in_db:
                # Добавляем нового
                new_ingredient = Ingredient(
                    name=name,
                    icon_url=icon_url,
                )
                session.add(new_ingredient)
            else:
                # Обновляем, если изменилось
                if ingredient_in_db.icon_url != icon_url:
                    ingredient_in_db.icon_url = icon_url

        # ============================
        # 2) Удаляем лишние
        # ============================
        # Выбираем все ингредиенты из БД
        result_all = await session.execute(select(Ingredient))
        all_ingredients = result_all.scalars().all()
        for ingr in all_ingredients:
            # Если название ингредиента не входит в config_names, удаляем
            if ingr.name not in config_names:
                logger.warning(f"Удаляем ингредиент: {ingr.name}")
                await session.delete(ingr)

        await session.commit()

    # ============================
    # 3) Сохранение изменённого YAML
    # ============================
    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                config_data,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
        logger.info("ingredients_config.yaml успешно обновлён.")
    except Exception as e:
        logger.error(f"Не удалось сохранить изменения в {CONFIG_FILE_PATH}: {e}")

    logger.info("Ингредиенты успешно инициализированы.")
