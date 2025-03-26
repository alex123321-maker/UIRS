from pathlib import Path
from datetime import datetime

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.recipe import (
    Recipe, RecipeStage, RecipeIngredient,
    RecipeTag, Ingredient, Tag,
)
from src.schemas.recipe import RecipeCreate, RecipeFullOut, RecipeIngredientCreate, RecipeStageCreate
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
    """

    # 1. Валидация ингредиентов и тегов
    await validate_ingredients(db, recipe_in.ingredients)
    await validate_tags(db, recipe_in.tags)

    # 2. Создадим транзакцию
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
            await save_preview_image(preview_image, media_dir, new_recipe)

        # 6. Создаём этапы и сохраняем фото
        if stage_images is None:
            stage_images = {}
        await create_and_save_stages(db, new_recipe.id, recipe_in.stages, stage_images, media_dir)

        # 7. Создаём ингредиенты
        await save_recipe_ingredients(db, new_recipe.id, recipe_in.ingredients)

        # 8. Создаём связи с тегами
        await save_recipe_tags(db, new_recipe.id, recipe_in.tags)

    # 9. Фиксируем транзакцию
    await db.refresh(new_recipe)

    # 10. Выполним отдельный запрос, чтобы подгрузить вложенные объекты
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

    return RecipeFullOut.model_validate(new_recipe)



async def create_and_save_stages(
    db: AsyncSession,
    recipe_id: int,
    stages_in: list[RecipeStageCreate],
    stage_images: dict[int, UploadFile],
    media_dir: Path
) -> None:
    for stage_in in stages_in:
        stage = RecipeStage(
            recipe_id=recipe_id,
            title=stage_in.title,
            order_index=stage_in.order_index,
            description=stage_in.description,
            minutes=stage_in.minutes,
        )
        db.add(stage)
        await db.flush()  # Чтобы получить stage.id

        # Проверяем, есть ли фото для этого шага
        if stage_in.order_index in stage_images:
            stage_file = stage_images[stage_in.order_index]
            stage_path = media_dir / f"{stage_in.order_index}.jpg"
            with stage_path.open("wb") as f:
                f.write(await stage_file.read())
            stage.photo_url = f"/media/{recipe_id}/{stage_in.order_index}.jpg"

async def save_recipe_ingredients(
    db: AsyncSession,
    recipe_id: int,
    ingredients_in: list[RecipeIngredientCreate]
) -> None:
    for ingr_in in ingredients_in:
        rec_ingr = RecipeIngredient(
            recipe_id=recipe_id,
            ingredient_id=ingr_in.ingredient_id,
            unit_id=ingr_in.unit_id,
            quantity=ingr_in.quantity
        )
        db.add(rec_ingr)


async def save_recipe_tags(
    db: AsyncSession,
    recipe_id: int,
    tag_ids: list[int]
) -> None:
    for tag_id in tag_ids:
        recipe_tag = RecipeTag(
            recipe_id=recipe_id,
            tag_id=tag_id
        )
        db.add(recipe_tag)


async def save_preview_image(
    preview_image: UploadFile,
    media_dir: Path,
    recipe: Recipe
) -> None:
    preview_path = media_dir / "preview.jpg"
    with preview_path.open("wb") as f:
        f.write(await preview_image.read())
    recipe.photo_url = f"/media/{recipe.id}/preview.jpg"


async def validate_ingredients(db: AsyncSession, ingredients: list[RecipeIngredientCreate]) -> None:
    if not ingredients:
        return

    ingredient_ids = [x.ingredient_id for x in ingredients]
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


async def validate_tags(db: AsyncSession, tag_ids: list[int]) -> None:
    if not tag_ids:
        return

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
