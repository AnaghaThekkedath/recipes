import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON
from sqlmodel import Column, Enum, Field, Relationship, SQLModel, UniqueConstraint


# ---------------------------------------------------------------------------
# Ingredient
# ---------------------------------------------------------------------------

class Ingredient(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    calories: float = Field(default=0.0)
    protein_g: float = Field(default=0.0)
    fat_g: float = Field(default=0.0)
    carbs_g: float = Field(default=0.0)
    fibre_g: float = Field(default=0.0)
    default_unit: str = Field(default="g")

    recipe_links: list["RecipeIngredient"] = Relationship(back_populates="ingredient")


# ---------------------------------------------------------------------------
# Recipe
# ---------------------------------------------------------------------------

class Recipe(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(index=True)
    description: str = Field(default="")
    servings: int = Field(default=1)
    instructions: list[str] = Field(default=[], sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    ingredient_links: list["RecipeIngredient"] = Relationship(back_populates="recipe")
    schedule_entries: list["WeekSchedule"] = Relationship(back_populates="recipe")


# ---------------------------------------------------------------------------
# RecipeIngredient (join table)
# ---------------------------------------------------------------------------

class RecipeIngredient(SQLModel, table=True):
    __tablename__ = "recipe_ingredient"

    recipe_id: uuid.UUID = Field(foreign_key="recipe.id", primary_key=True)
    ingredient_id: uuid.UUID = Field(foreign_key="ingredient.id", primary_key=True)
    quantity: float = Field(default=0.0)
    unit: str = Field(default="g")

    recipe: Optional[Recipe] = Relationship(back_populates="ingredient_links")
    ingredient: Optional[Ingredient] = Relationship(back_populates="recipe_links")


# ---------------------------------------------------------------------------
# MealSlot enum
# ---------------------------------------------------------------------------

class MealSlot(str, enum.Enum):
    breakfast = "breakfast"
    morning_snack = "morning_snack"
    lunch = "lunch"
    evening_snack = "evening_snack"
    dinner = "dinner"


# ---------------------------------------------------------------------------
# WeekSchedule
# ---------------------------------------------------------------------------

class WeekSchedule(SQLModel, table=True):
    __tablename__ = "week_schedule"
    __table_args__ = (UniqueConstraint("date", "meal_slot"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    recipe_id: uuid.UUID = Field(foreign_key="recipe.id")
    date: str = Field(index=True)
    meal_slot: MealSlot = Field(sa_column=Column(Enum(MealSlot)))
    servings: int = Field(default=1)

    recipe: Optional[Recipe] = Relationship(back_populates="schedule_entries")
