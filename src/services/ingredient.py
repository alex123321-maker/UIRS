from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.recipe import Ingredient

async def get_ingredients(
    db: AsyncSession,
    q: Optional[str],
    page: int,
    limit: int
) -> Tuple[List[Ingredient], int]:
    """
    Возвращает список ингредиентов с учётом поиска и пагинации,
    а также общее количество найденных.
    """
    # Базовый запрос
    query = select(Ingredient)

    # Если указан q, то фильтруем по name
    if q:
        query = query.where(Ingredient.name.ilike(f"%{q}%"))

    # Считаем общее количество (до пагинации)

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    # Применяем пагинацию
    query = query.offset((page - 1) * limit).limit(limit)

    # Выполняем запрос
    results = await db.execute(query)
    ingredients = list(results.scalars().all())

    return ingredients, total


async def get_ingredient_by_id(
    db: AsyncSession,
    ingredient_id: int
) -> Optional[Ingredient]:
    """
    Ищет ингредиент в БД по его ID.
    Возвращает объект Ingredient, если найден, иначе None.
    """
    result = await db.execute(select(Ingredient).where(Ingredient.id == ingredient_id))
    return result.scalars().first()