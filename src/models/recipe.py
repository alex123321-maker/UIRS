from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Float,
    Enum as SAEnum, ForeignKey, Text, Table, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum

from src.models.rwmodel import RWModel as Base

class DifficultyEnum(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"

recipe_tags = Table(
    "recipe_tags",
    Base.metadata,  # связываем с метаданными
    Column("recipe_id", Integer, ForeignKey("recipes.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
)

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    published_at = Column(DateTime, nullable=True)
    is_published = Column(Boolean, default=False)
    servings = Column(Integer, default=1, nullable=False)
    difficulty = Column(SAEnum(DifficultyEnum), default=DifficultyEnum.EASY)
    calories = Column(Float, default=0.0)
    photo_url = Column(String, nullable=True)


    author = relationship("User", back_populates="recipes")
    stages = relationship("RecipeStage", back_populates="recipe")
    # Связь с объектом-ассоциацией RecipeIngredient
    ingredients = relationship("RecipeIngredient", back_populates="recipe")
    # Связь с объектом-ассоциацией RecipeTag
    tags = relationship("Tag", secondary=recipe_tags, back_populates="recipes")
    comments = relationship("Comment", back_populates="recipe")

class RecipeStage(Base):
    __tablename__ = "recipe_stages"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    minutes = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    photo_url = Column(String, nullable=True)

    recipe = relationship("Recipe", back_populates="stages")

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    icon_url = Column(String, nullable=True)

    # Обратная связь на список объектов RecipeIngredient,
    # из которых уже можно добраться до самих Recipe
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")

class UnitOfMeasurement(Base):
    __tablename__ = "units_of_measurement"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units_of_measurement.id"), nullable=False)
    quantity = Column(Float, default=0.0)

    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")
    unit = relationship("UnitOfMeasurement")

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    recipes = relationship("Recipe", secondary=recipe_tags, back_populates="tags")



class RecipeLike(Base):
    __tablename__ = "recipe_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "recipe_id", name="unique_user_recipe_like"),
    )