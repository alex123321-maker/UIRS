import logging
from pathlib import Path

import yaml
from fastapi import FastAPI
from sqlalchemy import select

from src.models.recipe import UnitOfMeasurement

CONFIG_FILE_PATH = "src/unit_config.yaml"
logger = logging.getLogger(__name__)

async def init_units(app: FastAPI) -> None:
    """
    Функция, которая читает unit_config.yaml (CONFIG_FILE_PATH) и:
      1) Добавляет/обновляет единицы измерения из конфига.
      2) Удаляет из базы все единицы, не указанные в конфиге.
      3) При необходимости перезаписывает unit_config.yaml (если что-то меняли).
    """
    # Шаг 1. Прочитать YAML
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)  # ожидаем список словарей
    except FileNotFoundError:
        app.logger.error(f"Файл {CONFIG_FILE_PATH} не найден.")
        return

    if not isinstance(config_data, list):
        app.logger.error(f"Формат {CONFIG_FILE_PATH} некорректен: ожидается список.")
        return

    # Собираем все 'name' из конфига
    unit_names_in_config = set()
    for item in config_data:
        # Предполагаем, что в каждом item есть ключ "name"
        name = item.get("name", "").strip()
        if name:
            unit_names_in_config.add(name)

    # Шаг 2. Работа с БД
    # Предполагаем, что app.state.pool() — это асинхронный "sessionmaker"
    # или аналогичная зависимость, возвращающая сессию.
    async with app.state.pool() as session:

        # 2a) Добавляем/обновляем
        for item in config_data:
            name = item.get("name", "").strip()
            if not name:
                continue  # если вдруг попался пустой элемент

            # Ищем в БД
            result = await session.execute(
                select(UnitOfMeasurement).where(UnitOfMeasurement.name == name)
            )
            unit_in_db = result.scalars().first()

            if not unit_in_db:
                # Добавляем новую единицу измерения
                new_unit = UnitOfMeasurement(name=name)
                session.add(new_unit)
            # Если нужно обновлять какие-то дополнительные поля, делаем это здесь,
            # но пока что предполагаем, что только name.

        # 2b) Удаляем единицы, которых нет в конфиге
        result_all = await session.execute(select(UnitOfMeasurement))
        all_units_in_db = result_all.scalars().all()
        for unit in all_units_in_db:
            if unit.name not in unit_names_in_config:
                logger.warning(f"Удаляем единицу измерения из БД: {unit.name}")
                await session.delete(unit)

        await session.commit()

    # Шаг 3. (Опционально) Сохранение изменённого YAML
    # Если вам ничего не нужно менять в файле, можно этот блок пропустить.
    # Но если логика подразумевает, что вы что-то изменяете в config_data, — сохраните обратно:
    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                config_data,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
        logger.info(f"{CONFIG_FILE_PATH} успешно обновлён.")
    except Exception as e:
        logger.error(f"Не удалось сохранить изменения в {CONFIG_FILE_PATH}: {e}")

    logger.info("Единицы измерения успешно инициализированы.")
