from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Any

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select, desc, func, asc, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.recipe import (
    Recipe,
    RecipeStage,
    RecipeIngredient,
    Ingredient,
    Tag,
    UnitOfMeasurement,
    DifficultyEnum,
    RecipeLike,
)
from src.schemas.recipe import (
    RecipeCreate,
    RecipeFullOut,
    RecipeIngredientCreate,
    RecipeStageCreate, RecipeUpdate,
)
from src.core import settings


# ————————————————————————————————————————————————————————————
# Helpers
# ————————————————————————————————————————————————————————————

async def _is_liked(
    db: AsyncSession,
    user_id: int,
    recipe_id: int
) -> bool:
    cnt = await db.scalar(
        select(func.count())
        .select_from(RecipeLike)
        .where(
            RecipeLike.user_id == user_id,
            RecipeLike.recipe_id == recipe_id,
        )
    )
    return cnt > 0


def _base_recipe_query() -> Any:
    return (
        select(
            Recipe,
            func.count(RecipeLike.id).label("likes_count")
        )
        .outerjoin(RecipeLike, Recipe.id == RecipeLike.recipe_id)
        .options(
            joinedload(Recipe.author),
            joinedload(Recipe.stages),
            joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient),
            joinedload(Recipe.ingredients).joinedload(RecipeIngredient.unit),
            joinedload(Recipe.tags),
        )
    )


async def _paginate_and_prepare(
    db: AsyncSession,
    stmt: Any,
    page: int,
    limit: int,
    user_id: Optional[int] = None,
) -> Tuple[List[RecipeFullOut], int]:
    total = await db.scalar(
        select(func.count()).select_from(stmt.subquery())
    )
    stmt = stmt.offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    rows = result.unique().all()

    out_list: List[RecipeFullOut] = []
    for recipe_obj, likes_count in rows:
        out = RecipeFullOut.model_validate(recipe_obj)
        out.likes_count = likes_count
        out.is_liked_by_me = (
            await _is_liked(db, user_id, out.id)
            if user_id is not None
            else None
        )
        out_list.append(out)

    return out_list, total


async def validate_units(
        db: AsyncSession,
        ingredients: list[RecipeIngredientCreate],
) -> None:
    """
    Проверяет, что все unit_id из списка ингредиентов существуют в таблице UnitOfMeasurement.
    Если какой-то unit_id не найден — бросает HTTPException 400.
    """
    if not ingredients:
        return

    unit_ids = [i.unit_id for i in ingredients]
    res = await db.execute(
        select(UnitOfMeasurement.id).where(UnitOfMeasurement.id.in_(unit_ids))
    )
    found = {r[0] for r in res}
    missing = set(unit_ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Некоторые unit_id не найдены: {missing}",
        )

async def validate_ingredients(
    db: AsyncSession,
    ingredients: list[RecipeIngredientCreate],
) -> None:
    if not ingredients:
        return

    ids = [i.ingredient_id for i in ingredients]
    res = await db.execute(
        select(Ingredient.id).where(Ingredient.id.in_(ids))
    )
    found = {r[0] for r in res}
    missing = set(ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Некоторые ingredient_id не найдены: {missing}",
        )


async def validate_tags(
    db: AsyncSession,
    tag_ids: list[int],
) -> None:
    if not tag_ids:
        return

    res = await db.execute(
        select(Tag.id).where(Tag.id.in_(tag_ids))
    )
    found = {r[0] for r in res}
    missing = set(tag_ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Некоторые tag_id не найдены: {missing}",
        )


async def save_preview_image(
    preview_image: UploadFile,
    media_dir: Path,
    recipe: Recipe,
) -> None:
    preview_path = media_dir / "preview.jpg"
    with preview_path.open("wb") as f:
        f.write(await preview_image.read())
    recipe.photo_url = f"/media/{recipe.id}/preview.jpg"


async def create_and_save_stages(
    db: AsyncSession,
    recipe_id: int,
    stages_in: list[RecipeStageCreate],
    stage_images: dict[int, UploadFile],
    media_dir: Path,
) -> None:
    for stage in stages_in:
        obj = RecipeStage(
            recipe_id=recipe_id,
            title=stage.title,
            order_index=stage.order_index,
            description=stage.description,
            minutes=stage.minutes,
        )
        db.add(obj)
        await db.flush()

        if stage.order_index in stage_images:
            img = stage_images[stage.order_index]
            path = media_dir / f"{stage.order_index}.jpg"
            with path.open("wb") as f:
                f.write(await img.read())
            obj.photo_url = f"/media/{recipe_id}/{stage.order_index}.jpg"


async def save_recipe_ingredients(
    db: AsyncSession,
    recipe_id: int,
    ingredients_in: list[RecipeIngredientCreate],
) -> None:
    for ingr in ingredients_in:
        db.add(
            RecipeIngredient(
                recipe_id=recipe_id,
                ingredient_id=ingr.ingredient_id,
                unit_id=ingr.unit_id,
                quantity=ingr.quantity,
            )
        )


async def save_recipe_tags(
    db: AsyncSession,
    recipe: Recipe,
    tag_ids: list[int],
) -> None:
    if not tag_ids:
        return

    res = await db.execute(
        select(Tag).where(Tag.id.in_(tag_ids))
    )
    tags = res.scalars().all()
    await db.run_sync(lambda sess: setattr(recipe, "tags", tags))


async def create_recipe_service(
    db: AsyncSession,
    recipe_in: RecipeCreate,
    user_id: int,
    preview_image: UploadFile | None,
    stage_images: dict[int, UploadFile] | None,
) -> RecipeFullOut:
    await validate_ingredients(db, recipe_in.ingredients)
    await validate_tags(db, recipe_in.tags)
    await validate_units(db, recipe_in.ingredients)

    new = Recipe(
        author_id=user_id,
        title=recipe_in.title,
        servings=recipe_in.servings,
        description=recipe_in.description,
        calories=recipe_in.calories or 0.0,
        is_published=recipe_in.is_published,
        difficulty=recipe_in.difficulty,
        created_at=datetime.utcnow(),
    )
    if recipe_in.is_published:
        new.published_at = datetime.utcnow()

    db.add(new)
    await db.flush()

    media_dir = Path(settings.BASE_DIR) / "media" / str(new.id)
    media_dir.mkdir(parents=True, exist_ok=True)

    if preview_image:
        await save_preview_image(preview_image, media_dir, new)

    await create_and_save_stages(
        db, new.id, recipe_in.stages, stage_images or {}, media_dir
    )
    await save_recipe_ingredients(db, new.id, recipe_in.ingredients)
    await save_recipe_tags(db, new, recipe_in.tags)

    return await get_recipe_by_id(db, new.id,user_id)


# ————————————————————————————————————————————————————————————
# Read / List Recipes
# ————————————————————————————————————————————————————————————

async def get_recipe_by_id(
    db: AsyncSession,
    id: int,
    user_id: Optional[int] = None,
) -> RecipeFullOut:
    stmt = _base_recipe_query().where(Recipe.id == id).group_by(Recipe.id)
    result = await db.execute(stmt)
    row = result.unique().first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id={id} not found",
        )

    recipe_obj, likes_count = row
    out = RecipeFullOut.model_validate(recipe_obj)
    out.likes_count = likes_count
    out.is_liked_by_me = await _is_liked(db, user_id, id) if user_id else None
    return out


async def get_recipes_list_service(
    db: AsyncSession,
    page: int,
    limit: int,
    title: Optional[str] = None,
    author_id: Optional[int] = None,
    difficulty: Optional[DifficultyEnum] = None,
    liked_by_me: bool = False,
    tag_ids: Optional[List[int]] = None,
    ingredient_ids: Optional[List[int]] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Tuple[List[RecipeFullOut], int]:
    stmt = _base_recipe_query().where(Recipe.is_published.is_(True))

    if title:
        stmt = stmt.where(Recipe.title.ilike(f"%{title}%"))
    if author_id:
        stmt = stmt.where(Recipe.author_id == author_id)
    if difficulty:
        stmt = stmt.where(Recipe.difficulty == difficulty)

    if tag_ids:
        for tid in tag_ids:
            stmt = stmt.where(Recipe.tags.any(Tag.id == tid))
    if ingredient_ids:
        for iid in ingredient_ids:
            stmt = stmt.where(Recipe.ingredients.any(RecipeIngredient.ingredient_id == iid))
    if liked_by_me:
        if not user_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется авторизация для фильтра по лайкам")
        stmt = stmt.where(RecipeLike.user_id == user_id)

    stmt = stmt.group_by(Recipe.id)

    if sort_by == "date":
        stmt = stmt.order_by(desc(Recipe.published_at) if sort_order == "desc" else asc(Recipe.published_at))
    elif sort_by == "calories":
        stmt = stmt.order_by(desc(Recipe.calories) if sort_order == "desc" else asc(Recipe.calories))
    else:
        stmt = stmt.order_by(desc(Recipe.created_at))

    return await _paginate_and_prepare(db, stmt, page, limit, user_id)


async def get_my_recipes_service(
    db: AsyncSession,
    user_id: int,
    page: int,
    limit: int,
    is_published: Optional[bool] = None,
    sort_order: Optional[str] = None,
) -> Tuple[List[RecipeFullOut], int]:
    stmt = _base_recipe_query().where(Recipe.author_id == user_id)

    if is_published is not None:
        stmt = stmt.where(Recipe.is_published == is_published)

    stmt = stmt.group_by(Recipe.id)
    stmt = stmt.order_by(desc(Recipe.published_at) if sort_order == "desc" else asc(Recipe.published_at))

    return await _paginate_and_prepare(db, stmt, page, limit, user_id)


async def update_recipe_service(
    db: AsyncSession,
    recipe_id: int,
    user_id: int,
    data: RecipeUpdate,
    preview_image: UploadFile | None = None,
    stage_images: dict[int, UploadFile] | None = None,
) -> RecipeFullOut:
    # 1) достаём рецепт и проверяем авторство
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Рецепт с id={recipe_id} не найден")
    if recipe.author_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа")

    # 2) Обновляем простые поля, если они переданы
    for field in ("title", "description", "calories", "is_published", "difficulty", "servings"):
        val = getattr(data, field)
        if val is not None:
            setattr(recipe, field, val)
            # если впервые публикуем
            if field == "is_published" and val and recipe.published_at is None:
                recipe.published_at = datetime.now()

    # 3) Теги
    if data.tags is not None:
        await validate_tags(db, data.tags)
        res = await db.execute(select(Tag).where(Tag.id.in_(data.tags)))
        recipe.tags = res.scalars().all()

    # 4) Ингредиенты
    if data.ingredients is not None:
        await validate_ingredients(db, data.ingredients)
        # удалить старые
        await db.execute(delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id))
        # добавить новые
        await save_recipe_ingredients(db, recipe_id, data.ingredients)

    # 5) Стадии
    if data.stages is not None:
        # удалить старые
        await db.execute(delete(RecipeStage).where(RecipeStage.recipe_id == recipe_id))
        await create_and_save_stages(db, recipe_id, data.stages, stage_images or {}, Path(settings.BASE_DIR) / "media" / str(recipe_id))

    # 6) Обложка
    if preview_image:
        media_dir = Path(settings.BASE_DIR) / "media" / str(recipe_id)
        await save_preview_image(preview_image, media_dir, recipe)

    # 7) Сохраняем
    return await get_recipe_by_id(db, recipe_id, user_id)
