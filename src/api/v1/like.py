# src/api/v1/like.py

from fastapi import APIRouter, Depends, HTTPException
from src.services.like import toggle_like
from src.api.dependencies.database import get_session
from src.models.recipe import Recipe
from src.api.dependencies.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/{recipe_id}")
async def like_recipe(
    recipe_id: int,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    # Проверяем, что рецепт существует
    recipe = await session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    is_liked = await toggle_like(current_user.id, recipe_id, session)
    return {"liked": is_liked}
