from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from src.models.rwmodel import RWModel as Base

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)

    owner = relationship("User", back_populates="meal_plans")
    days = relationship("DaySchedule", back_populates="plan", cascade="all, delete-orphan")

class DaySchedule(Base):
    __tablename__ = "day_schedules"
    __table_args__ = (
        UniqueConstraint("meal_plan_id", "date", name="uq_plan_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False)

    plan = relationship("MealPlan", back_populates="days")
    recipes = relationship("DayScheduleRecipe", back_populates="day", cascade="all, delete-orphan")

class DayScheduleRecipe(Base):
    __tablename__ = "day_schedule_recipes"


    id = Column(Integer, primary_key=True, index=True)
    day_schedule_id = Column(Integer, ForeignKey("day_schedules.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    order = Column(Integer, nullable=False)

    day = relationship("DaySchedule", back_populates="recipes")
    recipe = relationship("Recipe")
