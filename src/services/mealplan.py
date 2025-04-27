from datetime import date
from sqlalchemy import select, and_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from src.models.mealplan import MealPlan, DaySchedule, DayScheduleRecipe
from src.schemas.mealplan import (
    DayScheduleRecipeCreate,
    DayScheduleRecipeUpdate,
    MealPlanCreate,
    MealPlanUpdate,
)

async def get_plan_by_id(
    db: AsyncSession,
    plan_id: int
) -> MealPlan | None:
    """
    Получить MealPlan по ID вместе с загруженными днями и рецептами.
    """
    stmt = select(MealPlan).options(
        joinedload(MealPlan.days).joinedload(DaySchedule.recipes)
    ).where(MealPlan.id == plan_id)
    result = await db.execute(stmt)
    return result.unique().scalar_one_or_none()
async def create_recipe_to_day(
    db: AsyncSession,
    plan_id: int,
    target_date: date,
    payload: DayScheduleRecipeCreate
) -> DayScheduleRecipe:
    """
    Создать новую привязку рецепта к дню плана.
    Если день не существует — создаёт его.
    Всегда ставит рецепт в конец: order = max(order)+1.
    """
    # 1) Найти или создать DaySchedule
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

    # 2) Вычислить следующий order
    stmt_max = select(func.max(DayScheduleRecipe.order)).where(
        DayScheduleRecipe.day_schedule_id == day.id
    )
    result = await db.execute(stmt_max)
    max_order = result.scalar_one() or 0
    new_order = max_order + 1

    # 3) Создать привязку с вычисленным порядком
    dsr = DayScheduleRecipe(
        day_schedule_id=day.id,
        recipe_id=payload.recipe_id,
        order=new_order
    )
    db.add(dsr)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # маловероятно, но на всякий случай
        raise ValueError("Conflict: невозможно создать запись")
    await db.refresh(dsr)
    return dsr

async def update_day_recipe(
    db: AsyncSession,
    plan_id: int,
    dsr_id: int,
    data: DayScheduleRecipeUpdate
) -> DayScheduleRecipe | None:
    """
    Заменить только `recipe_id` в существующей записи.
    """
    if data.recipe_id is None:
        return None

    stmt = select(DayScheduleRecipe).join(DaySchedule).where(
        and_(
            DayScheduleRecipe.id == dsr_id,
            DaySchedule.meal_plan_id == plan_id
        )
    )
    dsr = (await db.execute(stmt)).scalar_one_or_none()
    if not dsr:
        return None

    dsr.recipe_id = data.recipe_id
    await db.commit()
    await db.refresh(dsr)
    return dsr

async def delete_day_recipe(
    db: AsyncSession,
    plan_id: int,
    dsr_id: int
) -> DayScheduleRecipe | None:
    """
    Удалить привязку рецепта к дню.
    Возвращает удалённый объект или None.
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
) -> list[DaySchedule]:
    """
    Получить список дней с предзагрузкой рецептов в интервале.
    """
    stmt = select(DaySchedule).options(
        joinedload(DaySchedule.recipes)
    ).where(
        and_(
            DaySchedule.meal_plan_id == plan_id,
            DaySchedule.date.between(start_date, end_date)
        )
    ).order_by(DaySchedule.date)
    result = await db.execute(stmt)
    return result.scalars().unique().all()
# src/services/mealplan.py

from sqlalchemy import select, and_, update, case
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.mealplan import DaySchedule, DayScheduleRecipe

async def reorder_day_recipes(
    db: AsyncSession,
    plan_id: int,
    target_date: date,
    new_order_ids: list[int]
) -> list[DayScheduleRecipe] | None:
    """
    Переупорядочить все записи рецептов для указанного дня.
    Делается одним UPDATE ... CASE, чтобы не было UniqueViolationError.
    """
    # 1) Найти день
    stmt_day = select(DaySchedule).where(
        and_(
            DaySchedule.meal_plan_id == plan_id,
            DaySchedule.date == target_date
        )
    )
    day = (await db.execute(stmt_day)).scalar_one_or_none()
    if not day:
        return None

    # 2) Проверить, что переданный список совпадает с существующими ID
    stmt_recipes = select(DayScheduleRecipe.id).where(
        DayScheduleRecipe.day_schedule_id == day.id
    )
    existing_ids = {r for (r,) in (await db.execute(stmt_recipes)).all()}
    if set(new_order_ids) != existing_ids:
        raise ValueError("orders должен содержать ровно все id рецептов этого дня")

    # 3) Собираем mapping id -> новый order
    mapping = {rid: idx for idx, rid in enumerate(new_order_ids, start=1)}

    # 4) Пачкой обновляем всё в одном запросе
    stmt_update = (
        update(DayScheduleRecipe)
        .where(DayScheduleRecipe.day_schedule_id == day.id)
        .values(order=case(mapping, value=DayScheduleRecipe.id))
    )
    await db.execute(stmt_update)
    await db.commit()

    # 5) Считываем результат и возвращаем в нужном порядке
    stmt_result = (
        select(DayScheduleRecipe)
        .where(DayScheduleRecipe.day_schedule_id == day.id)
    )
    updated = (await db.execute(stmt_result)).scalars().all()
    return sorted(updated, key=lambda r: r.order)


async def create_mealplan(
    db: AsyncSession,
    user_id: int,
    obj_in: MealPlanCreate
) -> MealPlan:
    """
    Создать новый план питания.
    """
    plan = MealPlan(user_id=user_id, name=obj_in.name)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan

async def get_mealplans_for_user(
    db: AsyncSession,
    user_id: int
) -> list[MealPlan]:
    """
    Получить все планы пользователя с предзагрузкой дней и рецептов.
    """
    stmt = select(MealPlan).options(
        joinedload(MealPlan.days).joinedload(DaySchedule.recipes)
    ).where(MealPlan.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().unique().all()

async def update_mealplan(
    db: AsyncSession,
    plan: MealPlan,
    obj_in: MealPlanUpdate
) -> MealPlan:
    """
    Обновить название плана.
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
    Удалить план питания.
    """
    await db.delete(plan)
    await db.commit()
    return plan
