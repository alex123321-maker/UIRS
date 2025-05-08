

from datetime import date
from pydantic import BaseModel, Field
from typing import List, Optional, Annotated


class DayScheduleRecipeBase(BaseModel):
    recipe_id: int
    order: int


class DayScheduleRecipeCreate(DayScheduleRecipeBase):
    pass

class DayScheduleRecipeRead(DayScheduleRecipeBase):
    id: int
    recipe_title: Annotated[str, Field(..., description="Название связанного рецепта")]
    preview: Annotated[Optional[str], Field(None, description="URL превью изображения рецепта")]

    class Config:
        from_attributes = True

class DayScheduleBase(BaseModel):
    date: date


class DayScheduleRead(DayScheduleBase):
    id: int
    recipes: List[DayScheduleRecipeRead]

    class Config:
        from_attributes = True
class MealPlanRead(BaseModel):
    id: int
    name: str
    days: List[DayScheduleRead]

    class Config:
        from_attributes = True


class DayScheduleRecipeUpdate(BaseModel):
    recipe_id: Optional[int] = None
    order: Optional[int] = None

    class Config:
        from_attributes = True


class DayScheduleRecipesReorder(BaseModel):
    orders: List[int]

    class Config:
        from_attributes = True



class MealPlanCreate(BaseModel):
    name: str

class MealPlanUpdate(BaseModel):
    name: Optional[str] = None

    class Config:
        from_attributes = True