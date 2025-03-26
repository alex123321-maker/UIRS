from typing import Optional

from fastapi import APIRouter, Depends, status, Query, Path, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.ingredient import PaginatedIngredientList, IngredientBase
from src.api.dependencies.database import get_session
from src.api.dependencies.pagination import PaginationParams, get_pagination_params
from src.services.ingredient import get_ingredients, get_ingredient_by_id

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedIngredientList,
    status_code=status.HTTP_200_OK,
    summary="Получить список ингредиентов",
    description="Возвращает список ингредиентов с возможностью поиска по q и пагинацией."
)
async def ingredient_list(
    db: AsyncSession = Depends(get_session),
    q: Optional[str] = Query(None, description="Строка поиска по ингредиентам"),
    pagination: PaginationParams = Depends(get_pagination_params),
) -> PaginatedIngredientList:
    """
    1) Доступен без авторизации.
    2) Если параметр q не пустой, ищем ингредиенты, у которых name содержит q.
    3) Пагинация по параметрам page, limit.
    """
    page = pagination.page
    limit = pagination.limit

    ingredients, total = await get_ingredients(db, q, page, limit)
    total_pages = (total // limit) + int(total % limit != 0)

    return PaginatedIngredientList(
        ingredients=[
            IngredientBase(id=i.id, name=i.name, icon_url=i.icon_url)
            for i in ingredients
        ],
        results=total,
        current_page=page,
        total_pages=total_pages
    )

@router.get(
    "/{ingredient_id}",
    response_model=IngredientBase,
    status_code=status.HTTP_200_OK,
    summary="Получить ингредиент по ID",
    description="Возвращает данные одного ингредиента по его идентификатору."
)
async def get_ingredient(
    ingredient_id: int = Path(..., description="Идентификатор ингредиента"),
    db: AsyncSession = Depends(get_session),
) -> IngredientBase:
    """
    1) Доступен без авторизации.
    2) Возвращает ингредиент, если он есть, иначе 404.
    """
    ingredient = await get_ingredient_by_id(db, ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    # Благодаря `from_attributes = True` в pydantic-модели можно вернуть прямо объект
    # Однако, чтобы быть явными, используем конструктор Pydantic:
    return IngredientBase.model_validate(ingredient)