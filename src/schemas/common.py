from typing import Generic, List, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Универсальный формат для постраничного ответа.

    Attributes:
    - items (List[T]): массив элементов текущей страницы (типа T).
    - results (int): общее количество записей во всём наборе.
    - current_page (int): номер текущей страницы (начиная с 1).
    - total_pages (int): общее число страниц.
    """
    items: List[T]
    results: int
    current_page: int
    total_pages: int