import os
from pathlib import Path
from datetime import datetime

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.recipe import (
    Recipe, RecipeStage, RecipeIngredient,
    RecipeTag, Ingredient, Tag, UnitOfMeasurement
)
from src.schemas.recipe import RecipeCreate, RecipeFullOut, DifficultyEnum
from src.core import settings

async def create_recipe_service(
    db: AsyncSession,
    recipe_in: RecipeCreate,
    user_id: int,
    preview_image: UploadFile | None,
    stage_images: dict[int, UploadFile] | None
) -> RecipeFullOut:
    """
    Создаёт рецепт вместе с этапами, ингредиентами и тегами,
    загружает фотографии, валидирует ингредиенты и теги.
    Возвращает рецепт во вложенном виде.
    :param recipe_in: данные для рецепта
    :param user_id: автор
    :param preview_image: файл превью (может быть None)
    :param stage_images: словарь {order_index: файл}, может быть пустым
    """

    # 1. Валидация ингредиентов
    ingredient_ids = [x.ingredient_id for x in recipe_in.ingredients]
    if ingredient_ids:
        res_ingr = await db.execute(
            select(Ingredient.id).where(Ingredient.id.in_(ingredient_ids))
        )
        found_ingr_ids = {row[0] for row in res_ingr}
        missing = set(ingredient_ids) - found_ingr_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Некоторые ingredient_id не найдены: {missing}"
            )

    # 2. Валидация тегов
    tag_ids = recipe_in.tags
    if tag_ids:
        res_tags = await db.execute(
            select(Tag.id).where(Tag.id.in_(tag_ids))
        )
        found_tag_ids = {row[0] for row in res_tags}
        missing_tags = set(tag_ids) - found_tag_ids
        if missing_tags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Некоторые tag_id не найдены: {missing_tags}"
            )

    # Создадим транзакцию
    async with db.begin():
        # 3. Создаём запись о рецепте
        new_recipe = Recipe(
            author_id=user_id,
            title=recipe_in.title,
            description=recipe_in.description,
            calories=recipe_in.calories or 0.0,
            is_published=recipe_in.is_published,
            difficulty=recipe_in.difficulty,  # ENUM в модели
            created_at=datetime.utcnow(),
        )
        if recipe_in.is_published:
            new_recipe.published_at = datetime.utcnow()

        db.add(new_recipe)
        await db.flush()  # чтобы получить new_recipe.id

        # 4. Создаём папку media/{id}
        media_dir = Path(settings.BASE_DIR) / "media" / f"{new_recipe.id}"
        media_dir.mkdir(parents=True, exist_ok=True)

        # 5. Сохраняем превью, если передано
        if preview_image is not None:
            preview_path = media_dir / "preview.jpg"
            with preview_path.open("wb") as f:
                f.write(await preview_image.read())
            new_recipe.photo_url = f"/media/{new_recipe.id}/preview.jpg"

        # 6. Создаём этапы, сохраняем фото при наличии
        for stage_in in recipe_in.stages:
            stage = RecipeStage(
                recipe_id=new_recipe.id,
                title=stage_in.title,
                order_index=stage_in.order_index,
                description=stage_in.description,
                minutes=stage_in.minutes,
            )
            db.add(stage)
            await db.flush()  # чтобы получить stage.id

            # Проверяем, есть ли фото под данный order_index
            if stage_in.order_index in stage_images:
                stage_file = stage_images[stage_in.order_index]
                stage_path = media_dir / f"{stage_in.order_index}.jpg"
                with stage_path.open("wb") as f:
                    f.write(await stage_file.read())
                stage.photo_url = f"/media/{new_recipe.id}/{stage_in.order_index}.jpg"

        # 7. Создаём ингредиенты
        for ingr_in in recipe_in.ingredients:
            rec_ingr = RecipeIngredient(
                recipe_id=new_recipe.id,
                ingredient_id=ingr_in.ingredient_id,
                unit_id=ingr_in.unit_id,
                quantity=ingr_in.quantity
            )
            db.add(rec_ingr)

        # 8. Создаём связи с тегами
        for tag_id in recipe_in.tags:
            recipe_tag = RecipeTag(
                recipe_id=new_recipe.id,
                tag_id=tag_id
            )
            db.add(recipe_tag)

    # Фиксируем транзакцию и загружаем «полный» рецепт с зависимостями
    # (stages, ingredients->ingredient, unit, tags->tag)
    await db.refresh(new_recipe)

    # Выполним отдельный запрос, чтобы подгрузить вложенные объекты
    await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.stages),
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.unit),
            selectinload(Recipe.tags).selectinload(RecipeTag.tag),
        )
        .where(Recipe.id == new_recipe.id)
    )
    # Чтобы объекты stages, ingredients, tags подтянулись в new_recipe,
    # в asyncsession.orm_state достаточно сделать refresh с нужными нагрузками
    # или заново извлечь через one(), затем вернуть.

    return RecipeFullOut.model_validate(new_recipe)
