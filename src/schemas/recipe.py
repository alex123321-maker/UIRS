from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
import datetime
from enum import Enum


class DifficultyEnum(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


# ---- Входящие схемы ----

class RecipeStageCreate(BaseModel):
    """Этап создания."""
    title: str
    order_index: int
    description: Optional[str] = None
    minutes: int


class RecipeIngredientCreate(BaseModel):
    """Ингредиент для рецепта (по ID, с unit и количеством)."""
    ingredient_id: int
    unit_id: int
    quantity: float


class RecipeCreate(BaseModel):
    """
    Данные, которые нужны при создании рецепта.
    (Будет передаваться в JSON в поле recipe_data)
    """
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    calories: Optional[float] = None
    is_published: bool = False
    difficulty: DifficultyEnum = DifficultyEnum.EASY

    stages: List[RecipeStageCreate] = []
    ingredients: List[RecipeIngredientCreate] = []
    tags: List[int] = []




class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str

class IngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    icon_url: Optional[str] = None

class RecipeIngredientOut(BaseModel):
    """
    Один «ингредиент в рецепте», со ссылкой на сам Ingredient и Unit
    """
    model_config = ConfigDict(from_attributes=True)
    id: int
    quantity: float
    ingredient: IngredientOut
    unit: UnitOut

class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str

class RecipeStageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_index: int
    minutes: int
    title: str
    description: Optional[str] = None
    photo_url: Optional[str] = None

class RecipeFullOut(BaseModel):
    """
    Полный ответ о рецепте с вложенными этапами, ингредиентами и тегами.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    created_at: datetime.datetime
    published_at: Optional[datetime.datetime] = None
    is_published: bool
    difficulty: DifficultyEnum
    calories: float
    photo_url: Optional[str] = None

    stages: List[RecipeStageOut]
    ingredients: List[RecipeIngredientOut]
    tags: List[TagOut]
