from typing import Generic, List, TypeVar
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")

class PaginatedResponse(GenericModel, Generic[T]):
    items: List[T]
    results: int
    current_page: int
    total_pages: int
