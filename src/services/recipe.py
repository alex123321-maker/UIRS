from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select, desc, func, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.recipe import (
    Recipe, RecipeStage, RecipeIngredient,
    Ingredient, Tag, UnitOfMeasurement, DifficultyEnum,
)
from src.schemas.recipe import RecipeCreate, RecipeFullOut, RecipeIngredientCreate, RecipeStageCreate
from src.core import settings


async def validate_units(db: AsyncSession, ingredients_in: list[RecipeIngredientCreate]) -> None:
    """
    Проверяем, что все переданные unit_id есть в таблице единиц измерения.
    Если какого-то unit_id не существует — выкидываем 400 ошибку.
    """
    if not ingredients_in:
        return

    # Собираем все unit_id (уберём повторения, если нужно)
    unit_ids = {x.unit_id for x in ingredients_in if x.unit_id is not None}
    if not unit_ids:
        return

    res_units = await db.execute(
        select(UnitOfMeasurement.id).where(UnitOfMeasurement.id.in_(unit_ids))
    )
    found_unit_ids = {row[0] for row in res_units}
    missing_units = unit_ids - found_unit_ids
    if missing_units:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Некоторые unit_id не найдены: {missing_units}"
        )

async def create_recipe_service(
    db: AsyncSession,
    recipe_in: RecipeCreate,
    user_id: int,
    preview_image: UploadFile | None,
    stage_images: dict[int, UploadFile] | None
) -> RecipeFullOut:
    """
    Создаёт рецепт вместе с этапами, ингредиентами и тегами,
    загружает фотографии, валидирует данные.
    Возвращает рецепт во вложенном виде.
    """

    # 1. Валидация ингредиентов и тегов
    await validate_ingredients(db, recipe_in.ingredients)
    await validate_tags(db, recipe_in.tags)
    await validate_units(db, recipe_in.ingredients)
    # 2. Создаём модель рецепта
    new_recipe = Recipe(
        author_id=user_id,
        title=recipe_in.title,
        description=recipe_in.description,
        calories=recipe_in.calories or 0.0,
        is_published=recipe_in.is_published,
        difficulty=recipe_in.difficulty,
        created_at=datetime.utcnow(),
    )
    if recipe_in.is_published:
        new_recipe.published_at = datetime.utcnow()

    db.add(new_recipe)
    # нужен flush, чтобы получить new_recipe.id
    await db.flush()

    # 3. Создаём папку media/{id}, сохраняем превью, если есть
    media_dir = Path(settings.BASE_DIR) / "media" / f"{new_recipe.id}"
    media_dir.mkdir(parents=True, exist_ok=True)

    if preview_image is not None:
        await save_preview_image(preview_image, media_dir, new_recipe)

    # 4. Создаём стадии (этапы) и привязываем к ним фото
    if stage_images is None:
        stage_images = {}
    await create_and_save_stages(
        db,
        new_recipe.id,
        recipe_in.stages,
        stage_images,
        media_dir
    )

    # 5. Создаём записи с ингредиентами
    await save_recipe_ingredients(db, new_recipe.id, recipe_in.ingredients)

    # 6. Создаём связи с тегами
    await save_recipe_tags(db, new_recipe, recipe_in.tags)


    # 7. Обновляем объект рецепта, чтобы подгрузить все изменения
    await db.refresh(new_recipe)

    stmt = (
        select(Recipe)
        .options(
            selectinload(Recipe.stages),
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.unit),
            # Теперь tags у нас уже список Tag, поэтому достаточно
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == new_recipe.id)
    )
    result = await db.execute(stmt)
    recipe_loaded = result.scalar_one()

    return RecipeFullOut.model_validate(recipe_loaded)

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
    recipe: Recipe,
    tag_ids: list[int]
) -> None:
    if not tag_ids:
        return
    result = await db.execute(
        select(Tag).where(Tag.id.in_(tag_ids))
    )
    tags = result.scalars().all()
    # Выполняем присваивание в синхронном контексте
    await db.run_sync(lambda sync_session: setattr(recipe, 'tags', tags))

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


async def get_recipe_by_id(db: AsyncSession, id: int) -> RecipeFullOut:
    recipe = await db.execute(
        select(Recipe)
        .where(Recipe.id == id)
        .options(
            selectinload(Recipe.stages),
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.unit),
            selectinload(Recipe.tags),
        )
    )
    recipe_obj = recipe.scalars().one_or_none()
    if recipe_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Рецепт с id={id} не найден."
        )
    return RecipeFullOut.model_validate(recipe_obj)

async def get_recipes_list_service(
    db: AsyncSession,
    page: int,
    limit: int,
    title: Optional[str] = None,
    author_id: Optional[int] = None,
    difficulty: Optional[DifficultyEnum] = None,
    tag_ids: Optional[List[int]] = None,
    ingredient_ids: Optional[List[int]] = None,
    sort_by: Optional[str] = None,  # 'date' или 'calories'
    sort_order: Optional[str] = None  # 'asc' или 'desc'
) -> Tuple[List[Recipe], int]:

    stmt = select(Recipe).where(Recipe.is_published == True).options(
        selectinload(Recipe.tags),
        selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
        selectinload(Recipe.ingredients).selectinload(RecipeIngredient.unit),
        selectinload(Recipe.stages)
    )

    if title:
        stmt = stmt.where(Recipe.title.ilike(f"%{title}%"))
    if author_id:
        stmt = stmt.where(Recipe.author_id == author_id)
    if difficulty:
        stmt = stmt.where(Recipe.difficulty == difficulty)

    if tag_ids:
        for tag_id in tag_ids:
            stmt = stmt.where(Recipe.tags.any(Tag.id == tag_id))

    if ingredient_ids:
        for ing_id in ingredient_ids:
            stmt = stmt.where(Recipe.ingredients.any(RecipeIngredient.ingredient_id == ing_id))

    if sort_by == "date":
        stmt = stmt.order_by(desc(Recipe.published_at) if sort_order == "desc" else asc(Recipe.published_at))
    elif sort_by == "calories":
        stmt = stmt.order_by(desc(Recipe.calories) if sort_order == "desc" else asc(Recipe.calories))

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((page - 1) * limit).limit(limit)

    result = await db.execute(stmt)
    recipes = result.scalars().all()

    return recipes, total

async def get_my_recipes_service(
    db: AsyncSession,
    user_id: int,
    page: int,
    limit: int,
    is_published: Optional[bool] = None,
    sort_order: Optional[str] = None,
) -> Tuple[List[Recipe], int]:
    """
    Возвращает рецепты пользователя с фильтрацией по публикации и сортировкой по дате публикации.
    """
    stmt = select(Recipe).options(
        selectinload(Recipe.tags),
        selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient),
        selectinload(Recipe.ingredients).selectinload(RecipeIngredient.unit),
        selectinload(Recipe.stages)
    ).where(Recipe.author_id == user_id)

    if is_published is not None:
        stmt = stmt.where(Recipe.is_published == is_published)

    # Сортировка по дате публикации
    stmt = stmt.order_by(
        desc(Recipe.published_at) if sort_order == "desc" else asc(Recipe.published_at)
    )

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((page - 1) * limit).limit(limit)

    result = await db.execute(stmt)
    recipes = result.scalars().all()

    return recipes, total
