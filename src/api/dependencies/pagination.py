from fastapi import Query
from pydantic import BaseModel

class PaginationParams(BaseModel):
    page: int
    limit: int

def get_pagination_params(
    page: int = Query(1, ge=1, description="Номер страницы (начиная с 1)"),
    limit: int = Query(10, ge=1, description="Количество элементов на странице")
) -> PaginationParams:
    """
    Возвращает объект с полями page и limit для пагинации.
    """
    return PaginationParams(page=page, limit=limit)
