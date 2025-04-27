# src/api/api_v1/endpoints/mealplan.py

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_session
from src.api.dependencies.mealplan import get_user_mealplan
from src.schemas.mealplan import (
    DayScheduleRecipeCreate,
    DayScheduleRecipeRead,
    DayScheduleRead,
    DayScheduleRecipeUpdate,
    DayScheduleRecipesReorder,
    MealPlanCreate,
    MealPlanRead,
    MealPlanUpdate,
)
from src.services.mealplan import (
    create_recipe_to_day,
    update_day_recipe,
    delete_day_recipe,
    get_days_with_recipes,
    reorder_day_recipes,
    create_mealplan,
    get_mealplans_for_user,
    update_mealplan,
    delete_mealplan,
)

router = APIRouter()

@router.post("/", response_model=MealPlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: MealPlanCreate,
    db: AsyncSession = Depends(get_session),
    user = Depends(get_current_user)
):
    """
    Создает новый план питания для текущего пользователя.

    **Тело запроса**:
        - name (str): название плана (макс. 255 символов)

    **Успешный ответ (201)**:
        - возвращает объект MealPlanRead:
            - id (int): уникальный ID плана
            - name (str): название плана
            - days (List[DayScheduleRead]): пустой список дней
    """
    plan = await create_mealplan(db, user.id, payload)
    # возвращаем словарь, чтобы days сразу был пустым списком
    return {
        "id": plan.id,
        "name": plan.name,
        "days": []
    }


@router.get("/", response_model=List[MealPlanRead], status_code=status.HTTP_200_OK)
async def list_plans(
    db: AsyncSession = Depends(get_session),
    user = Depends(get_current_user)
):
    """
    Возвращает список всех планов питания текущего пользователя.

    **Успешный ответ (200)**:
        - список объектов MealPlanRead.
    """
    return await get_mealplans_for_user(db, user.id)

@router.get("/{plan_id}", response_model=MealPlanRead, status_code=status.HTTP_200_OK)
async def get_plan(
    plan = Depends(get_user_mealplan)
):
    """
    Возвращает детали плана питания по его ID, включая дни и назначенные рецепты.

    **Параметры пути**:
        - plan_id (int): ID плана питания

    **Успешный ответ (200)**:
        - объект MealPlanRead с полями:
            - id, name, days
    """
    return plan

@router.patch("/{plan_id}", response_model=MealPlanRead, status_code=status.HTTP_200_OK)
async def patch_plan(
    payload: MealPlanUpdate,
    plan = Depends(get_user_mealplan),
    db: AsyncSession = Depends(get_session)
):
    """
    Обновляет название существующего плана питания.

    **Параметры пути**:
        - plan_id (int): ID плана питания

    **Тело запроса**:
        - name (Optional[str]): новое название

    **Успешный ответ (200)**:
        - объект MealPlanRead с обновленным полем name
    """
    return await update_mealplan(db, plan, payload)

@router.delete("/{plan_id}", response_model=MealPlanRead, status_code=status.HTTP_200_OK)
async def remove_plan(
    plan = Depends(get_user_mealplan),
    db: AsyncSession = Depends(get_session)
):
    """
    Удаляет план питания вместе со всеми связанными днями и рецептами.

    **Параметры пути**:
        - plan_id (int): ID плана питания

    **Успешный ответ (200)**:
        - возвращает удаленный объект MealPlanRead (до удаления)
    """
    return await delete_mealplan(db, plan)

@router.get("/{plan_id}/days", response_model=List[DayScheduleRead], status_code=status.HTTP_200_OK)
async def list_days(
    start: date = Query(..., description="Дата начала периода YYYY-MM-DD"),
    end: date = Query(..., description="Дата конца периода YYYY-MM-DD"),
    plan = Depends(get_user_mealplan),
    db: AsyncSession = Depends(get_session)
):
    """
    Возвращает дни с назначенными рецептами для указанного плана питания в заданном интервале.

    **Параметры пути**:
        - plan_id (int): ID плана питания
    **Query параметры**:
        - start (date): начало периода
        - end (date): конец периода

    **Успешный ответ (200)**:
        - список DayScheduleRead с полями id, date, recipes
    **Ошибки**:
        - 404, если нет записей за период
    """
    days = await get_days_with_recipes(db, plan.id, start, end)
    if not days:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Записи не найдены")
    return days

@router.post("/{plan_id}/days/{target_date}/recipes", response_model=DayScheduleRecipeRead, status_code=status.HTTP_201_CREATED)
async def add_recipe(
    target_date: date,
    payload: DayScheduleRecipeCreate,
    plan = Depends(get_user_mealplan),
    db: AsyncSession = Depends(get_session)
):
    """
    Создает новую запись рецепта для указанного дня в плане питания.

    **Параметры пути**:
        - plan_id (int): ID плана питания
        - target_date (date): дата назначения рецепта

    **Тело запроса**:
        - recipe_id (int): ID рецепта

    **Успешный ответ (201)**:
        - объект DayScheduleRecipeRead с id, recipe_id, order
    """
    try:
        return await create_recipe_to_day(db, plan.id, target_date, payload)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e))

@router.patch("/{plan_id}/recipes/{dsr_id}", response_model=DayScheduleRecipeRead, status_code=status.HTTP_200_OK)
async def replace_recipe(
    dsr_id: int,
    payload: DayScheduleRecipeUpdate,
    plan = Depends(get_user_mealplan),
    db: AsyncSession = Depends(get_session)
):
    """
    Заменяет рецепт в существующей записи DayScheduleRecipe.

    **Параметры пути**:
        - plan_id (int): ID плана питания
        - dsr_id (int): ID записи DayScheduleRecipe

    **Тело запроса**:
        - recipe_id (int): новый ID рецепта

    **Успешный ответ (200)**:
        - обновленный объект DayScheduleRecipeRead
    **Ошибки**:
        - 400, если recipe_id не указан
        - 404, если запись не найдена
    """
    if payload.recipe_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Не указан новый recipe_id")
    updated = await update_day_recipe(db, plan.id, dsr_id, payload)
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    return updated

@router.patch("/{plan_id}/days/{target_date}/recipes/order", response_model=List[DayScheduleRecipeRead], status_code=status.HTTP_200_OK)
async def reorder_recipes(
    target_date: date,
    payload: DayScheduleRecipesReorder,
    plan = Depends(get_user_mealplan),
    db: AsyncSession = Depends(get_session)
):
    """
    Переупорядочивает все записи рецептов для указанного дня.

    **Параметры пути**:
        - plan_id (int): ID плана питания
        - target_date (date): дата, для которой происходит переупорядочивание

    **Тело запроса**:
        - orders (List[int]): полный список ID записей DayScheduleRecipe в новом порядке

    **Успешный ответ (200)**:
        - массив DateScheduleRecipeRead, отсортированных по новому order
    **Ошибки**:
        - 400, если список orders не совпадает с существующими ID
        - 404, если день не найден
    """
    try:
        updated = await reorder_day_recipes(db, plan.id, target_date, payload.orders)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="День не найден")
    return updated

@router.delete("/{plan_id}/recipes/{dsr_id}", response_model=DayScheduleRecipeRead, status_code=status.HTTP_200_OK)
async def remove_recipe(
    dsr_id: int,
    plan = Depends(get_user_mealplan),
    db: AsyncSession = Depends(get_session)
):
    """
    Удаляет запись DayScheduleRecipe по ее ID.

    **Параметры пути**:
        - plan_id (int): ID плана питания
        - dsr_id (int): ID записи DayScheduleRecipe

    **Успешный ответ (200)**:
        - удаленный объект DayScheduleRecipeRead
    **Ошибки**:
        - 404, если запись не найдена
    """
    dsr = await delete_day_recipe(db, plan.id, dsr_id)
    if not dsr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    return dsr




