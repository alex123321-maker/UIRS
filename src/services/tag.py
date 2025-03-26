from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.recipe import Tag as TagModel
from typing import List, Optional, Tuple


async def get_tags(
    db: AsyncSession,
    q: Optional[str],
    page: int,
    limit: int
) -> Tuple[List[TagModel], int]:
    """
    Возвращает список тэгов с учётом поиска и пагинации, а также
    общее число найденных (с учётом фильтра q).
    """

    # Базовый запрос (с фильтрацией, если есть q)
    base_query = select(TagModel)
    if q:
        base_query = base_query.where(TagModel.name.ilike(f"%{q}%"))

    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()  # Общее кол-во строк по тому же фильтру

    # Применяем пагинацию к основному запросу
    base_query = base_query.offset((page - 1) * limit).limit(limit)

    # Выполняем запрос
    results = await db.execute(base_query)
    tags = results.scalars().all()

    return tags, total

async def get_tag_by_name(db: AsyncSession, name: str) -> Optional[TagModel]:
    """Возвращает тег по имени (None, если не найден)."""
    query = select(TagModel).where(TagModel.name == name)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def create_tag(db: AsyncSession, name: str) -> TagModel:
    """Создаёт новый тег с указанным именем."""
    new_tag = TagModel(name=name)
    db.add(new_tag)
    await db.commit()
    await db.refresh(new_tag)
    return new_tag

async def get_or_create_tag(db: AsyncSession, name: str) -> Tuple[TagModel, bool]:
    """
    Проверяет существование тега. Если уже есть – возвращаем его,
    иначе создаём новый. Второй элемент кортежа указывает, создан ли новый (True/False).
    """
    existing = await get_tag_by_name(db, name)
    if existing:
        return existing, False
    created = await create_tag(db, name)
    return created, True
