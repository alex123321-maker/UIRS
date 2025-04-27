

from datetime import date
from pydantic import BaseModel
from typing import List, Optional


class DayScheduleRecipeBase(BaseModel):
    recipe_id: int

class DayScheduleRecipeCreate(DayScheduleRecipeBase):
    pass

class DayScheduleRecipeRead(DayScheduleRecipeBase):
    id: int

    order: int

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