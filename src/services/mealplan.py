# src/services/mealplan.py

from datetime import date
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from fastapi import HTTPException, status

from src.models.mealplan import MealPlan, DaySchedule, DayScheduleRecipe
from src.models.recipe import Recipe
from src.schemas.mealplan import (
    DayScheduleRecipeCreate,
    DayScheduleRecipeUpdate,
    MealPlanCreate,
    MealPlanUpdate,
)


async def validate_recipe_exists(
    db: AsyncSession,
    recipe_id: int
) -> None:
    """
    Проверяет, что рецепт с заданным ID существует.
    Если нет — бросает HTTPException(404).
    """
    q = select(Recipe.id).where(Recipe.id == recipe_id)
    if (await db.execute(q)).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id={recipe_id} not found"
        )


async def get_plan_by_id(
    db: AsyncSession,
    plan_id: int
) -> Optional[MealPlan]:
    """
    Получить MealPlan вместе со всеми днями и привязанными рецептами.
    """
    stmt = (
        select(MealPlan)
        .options(
            joinedload(MealPlan.days)
            .joinedload(DaySchedule.recipes)
            .joinedload(DayScheduleRecipe.recipe)
        )
        .where(MealPlan.id == plan_id)
    )
    res = await db.execute(stmt)
    return res.unique().scalar_one_or_none()


async def create_recipe_to_day(
    db: AsyncSession,
    plan_id: int,
    target_date: date,
    payload: DayScheduleRecipeCreate
) -> DayScheduleRecipe:
    """
    Создаёт новую привязку Recipe → DaySchedule:
    - Проверяет, что рецепт существует.
    - Создаёт или находит нужный DaySchedule.
    - Проверяет уникальность `order`.
    - Возвращает DayScheduleRecipe с предзагруженным recipe.
    """
    await validate_recipe_exists(db, payload.recipe_id)

    # 1) найти или создать День
    stmt_day = select(DaySchedule).where(
        and_(
            DaySchedule.meal_plan_id == plan_id,
            DaySchedule.date == target_date
        )
    )
    day = (await db.execute(stmt_day)).scalar_one_or_none()
    if not day:
        day = DaySchedule(meal_plan_id=plan_id, date=target_date)
        db.add(day)
        await db.commit()
        await db.refresh(day)

    # 2) проверить конфликт по order
    stmt_conf = select(DayScheduleRecipe).where(
        and_(
            DayScheduleRecipe.day_schedule_id == day.id,
            DayScheduleRecipe.order == payload.order
        )
    )
    if (await db.execute(stmt_conf)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: порядок занят"
        )

    # 3) создать запись
    dsr = DayScheduleRecipe(
        day_schedule_id=day.id,
        recipe_id=payload.recipe_id,
        order=payload.order
    )
    db.add(dsr)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно создать привязку"
        )

    # 4) перезагрузить с joinedload recipe
    stmt = select(DayScheduleRecipe).options(
        joinedload(DayScheduleRecipe.recipe)
    ).where(DayScheduleRecipe.id == dsr.id)
    dsr = (await db.execute(stmt)).scalar_one()
    return dsr


async def update_day_recipe(
    db: AsyncSession,
    plan_id: int,
    dsr_id: int,
    data: DayScheduleRecipeUpdate
) -> Optional[DayScheduleRecipe]:
    """
    Заменяет только `recipe_id` в существующей DayScheduleRecipe:
    - Проверяет, что новый рецепт существует.
    - Возвращает обновлённый объект с предзагруженным recipe.
    """
    if data.recipe_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указан новый recipe_id"
        )

    await validate_recipe_exists(db, data.recipe_id)

    stmt = (
        select(DayScheduleRecipe)
        .where(DayScheduleRecipe.id == dsr_id)
        .join(DayScheduleRecipe.day)
        .where(DaySchedule.meal_plan_id == plan_id)
    )
    dsr = (await db.execute(stmt)).scalar_one_or_none()
    if not dsr:
        return None

    dsr.recipe_id = data.recipe_id
    await db.commit()

    # перезагрузить с joinedload recipe
    stmt = select(DayScheduleRecipe).options(
        joinedload(DayScheduleRecipe.recipe)
    ).where(DayScheduleRecipe.id == dsr.id)
    dsr = (await db.execute(stmt)).scalar_one()
    return dsr


async def delete_day_recipe(
    db: AsyncSession,
    plan_id: int,
    dsr_id: int
) -> Optional[DayScheduleRecipe]:
    """
    Удаляет одну запись DayScheduleRecipe по её ID.
    """
    stmt = select(DayScheduleRecipe).join(DaySchedule).where(
        and_(
            DaySchedule.meal_plan_id == plan_id,
            DayScheduleRecipe.id == dsr_id
        )
    )
    dsr = (await db.execute(stmt)).scalar_one_or_none()
    if dsr:
        await db.delete(dsr)
        await db.commit()
    return dsr


async def get_days_with_recipes(
    db: AsyncSession,
    plan_id: int,
    start_date: date,
    end_date: date
) -> List[DaySchedule]:
    """
    Возвращает все дни с вложенными рецептами (и сами объекты Recipe) за период.
    """
    stmt = (
        select(DaySchedule)
        .options(
            joinedload(DaySchedule.recipes)
            .joinedload(DayScheduleRecipe.recipe)
        )
        .where(
            and_(
                DaySchedule.meal_plan_id == plan_id,
                DaySchedule.date.between(start_date, end_date)
            )
        )
        .order_by(DaySchedule.date)
    )
    res = await db.execute(stmt)
    return res.scalars().unique().all()


async def reorder_day_recipes(
    db: AsyncSession,
    plan_id: int,
    target_date: date,
    new_order_ids: List[int]
) -> Optional[List[DayScheduleRecipe]]:
    """
    Переставляет все DayScheduleRecipe в дне согласно полному списку их ID.
    Загружает рецепты сразу через joinedload.
    """
    # найти день
    stmt_day = select(DaySchedule).where(
        and_(
            DaySchedule.meal_plan_id == plan_id,
            DaySchedule.date == target_date
        )
    )
    day = (await db.execute(stmt_day)).scalar_one_or_none()
    if not day:
        return None

    # загрузить привязки сразу с recipe
    stmt_rec = select(DayScheduleRecipe).options(
        joinedload(DayScheduleRecipe.recipe)
    ).where(DayScheduleRecipe.day_schedule_id == day.id)
    existing = (await db.execute(stmt_rec)).scalars().all()

    ids_set = {r.id for r in existing}
    if set(new_order_ids) != ids_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="orders должен содержать ровно все id"
        )

    for idx, rid in enumerate(new_order_ids, start=1):
        next(r for r in existing if r.id == rid).order = idx

    await db.commit()
    for r in existing:
        await db.refresh(r)
    return sorted(existing, key=lambda r: r.order)


async def create_mealplan(
    db: AsyncSession,
    user_id: int,
    obj_in: MealPlanCreate
) -> MealPlan:
    """
    Создаёт новый MealPlan.
    """
    plan = MealPlan(user_id=user_id, name=obj_in.name)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def get_mealplans_for_user(
    db: AsyncSession,
    user_id: int
) -> List[MealPlan]:
    """
    Возвращает все MealPlan пользователя с жадной загрузкой дней и рецептов.
    """
    stmt = (
        select(MealPlan)
        .options(
            joinedload(MealPlan.days)
            .joinedload(DaySchedule.recipes)
            .joinedload(DayScheduleRecipe.recipe)
        )
        .where(MealPlan.user_id == user_id)
    )
    res = await db.execute(stmt)
    return res.scalars().unique().all()


async def update_mealplan(
    db: AsyncSession,
    plan: MealPlan,
    obj_in: MealPlanUpdate
) -> MealPlan:
    """
    Обновляет имя MealPlan.
    """
    if obj_in.name is not None:
        plan.name = obj_in.name
    await db.commit()
    await db.refresh(plan)
    return plan


async def delete_mealplan(
    db: AsyncSession,
    plan: MealPlan
) -> MealPlan:
    """
    Удаляет MealPlan и всё, что к нему привязано.
    """
    await db.delete(plan)
    await db.commit()
    return plan
