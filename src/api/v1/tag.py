from fastapi import APIRouter, Depends, Query, status
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_session
from src.api.dependencies.auth import get_current_user
from src.services.tag import get_tags, get_or_create_tag
from src.schemas.tag import PaginatedTagList, TagBase, TagCreate
from src.api.dependencies.pagination import get_pagination_params, PaginationParams

router = APIRouter()

@router.get(
    "/",
    response_model=PaginatedTagList,
    status_code=status.HTTP_200_OK,
    summary="Получить список тэгов",
    description="Возвращает список тэгов с возможностью поиска по q и пагинацией."
)
async def tag_list(
    db: AsyncSession = Depends(get_session),
    q: Optional[str] = Query(None, description="Строка поиска по тегам"),
    pagination: PaginationParams = Depends(get_pagination_params),
)->PaginatedTagList:
    """
    1) Доступен без авторизации.
    2) Поиск по тэгам: если q не пустой, ищем теги,
       у которых title содержит q.
    3) Пагинация по параметрам page, limit.
    """
    page = pagination.page
    limit = pagination.limit

    tags, total = await get_tags(db, q, page, limit)
    total_pages = (total // limit) + int(total % limit != 0)

    return PaginatedTagList(
        tags=[
            TagBase(id=t.id, title=t.name) for t in tags
        ],
        results=total,
        current_page=page,
        total_pages=total_pages
    )


@router.post(
    "/",
    response_model=TagBase,
    status_code=status.HTTP_200_OK,
    summary="Создать новый тег",
    description="Создаёт новый тег, либо возвращает уже существующий."
)
async def create_tag(
    tag_in: TagCreate,
    db: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
)->TagBase:
    """
    1) Эндпоинт доступен только для авторизованных пользователей.
    2) Если тег (title) уже существует – возвращаем существующий.
    3) Иначе создаём новый тег.
    """
    # Сервис проверит существование, при отсутствии – создаст
    tag_obj, is_created = await get_or_create_tag(db, tag_in.title)
    # Возвращаем в формате нашей схемы
    return TagBase(id=tag_obj.id, title=tag_obj.name)