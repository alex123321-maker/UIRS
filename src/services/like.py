# src/services/like_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from src.models.recipe import RecipeLike

async def toggle_like(user_id: int, recipe_id: int, session: AsyncSession) -> bool:
    """
    Если лайк уже существует — удалить его, если нет — добавить.
    Возвращает True если лайк был поставлен, False если убран.
    """
    query = select(RecipeLike).where(
        RecipeLike.user_id == user_id,
        RecipeLike.recipe_id == recipe_id
    )
    result = await session.execute(query)
    like = result.scalar_one_or_none()

    if like:
        await session.execute(
            delete(RecipeLike).where(RecipeLike.id == like.id)
        )
        await session.commit()
        return False
    else:
        new_like = RecipeLike(user_id=user_id, recipe_id=recipe_id)
        session.add(new_like)
        await session.commit()
        return True
