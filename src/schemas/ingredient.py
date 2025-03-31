from pydantic import BaseModel
from typing import List, Optional

class IngredientBase(BaseModel):
    id: int
    name: str
    icon_url: Optional[str] = None

    class Config:
        from_attributes = True

class IngredientList(BaseModel):
    ingredients: List[IngredientBase]

class PaginatedIngredientList(IngredientList):
    """Список ингредиентов с данными о пагинации."""
    results: int
    current_page: int
    total_pages: int

class UnitBase(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class UnitsList(BaseModel):
    units: List[UnitBase]