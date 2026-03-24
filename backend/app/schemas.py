import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models import MealSlot


# ---------------------------------------------------------------------------
# Ingredient
# ---------------------------------------------------------------------------

class IngredientCreate(BaseModel):
    name: str
    calories: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    fibre_g: float = 0.0
    default_unit: str = "g"


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fibre_g: Optional[float] = None
    default_unit: Optional[str] = None


class IngredientRead(BaseModel):
    id: uuid.UUID
    name: str
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float
    fibre_g: float
    default_unit: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# RecipeIngredient
# ---------------------------------------------------------------------------

class RecipeIngredientEntry(BaseModel):
    """Used in create/update recipe payloads."""
    ingredient_id: uuid.UUID
    quantity: float
    unit: str = "g"


class RecipeIngredientRead(BaseModel):
    ingredient: IngredientRead
    quantity: float
    unit: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Recipe
# ---------------------------------------------------------------------------

class RecipeCreate(BaseModel):
    title: str
    description: str = ""
    servings: int = Field(default=1, ge=1)
    instructions: list[str] = []
    ingredients: list[RecipeIngredientEntry] = []


class RecipeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    servings: Optional[int] = Field(default=None, ge=1)
    instructions: Optional[list[str]] = None
    ingredients: Optional[list[RecipeIngredientEntry]] = None


class RecipeRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    servings: int
    instructions: list[str]
    created_at: datetime
    ingredients: list[RecipeIngredientRead] = []

    total_calories: float = 0.0
    total_protein_g: float = 0.0
    total_fat_g: float = 0.0
    total_carbs_g: float = 0.0
    total_fibre_g: float = 0.0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

class ScheduleCreate(BaseModel):
    recipe_id: uuid.UUID
    date: date
    meal_slot: MealSlot
    servings: int = Field(default=1, ge=1)


class ScheduleRead(BaseModel):
    id: uuid.UUID
    recipe_id: uuid.UUID
    date: date
    meal_slot: MealSlot
    servings: int
    recipe: RecipeRead

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Shopping List
# ---------------------------------------------------------------------------

class ShoppingListItem(BaseModel):
    ingredient: IngredientRead
    total_quantity: float
    unit: str


class ShoppingListTotals(BaseModel):
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float
    fibre_g: float


class ShoppingListResponse(BaseModel):
    week_start: date
    items: list[ShoppingListItem]
    totals: ShoppingListTotals


# ---------------------------------------------------------------------------
# Nutrition helper
# ---------------------------------------------------------------------------

def compute_recipe_nutrition(ingredient_links) -> dict[str, float]:
    """Sum nutrition across all recipe-ingredient links.

    Each ingredient's nutritional values are per 100 g. We scale by
    (quantity / 100) to get the actual contribution.
    """
    totals = {
        "total_calories": 0.0,
        "total_protein_g": 0.0,
        "total_fat_g": 0.0,
        "total_carbs_g": 0.0,
        "total_fibre_g": 0.0,
    }
    for link in ingredient_links:
        ing = link.ingredient
        if ing is None:
            continue
        factor = link.quantity / 100.0
        totals["total_calories"] += ing.calories * factor
        totals["total_protein_g"] += ing.protein_g * factor
        totals["total_fat_g"] += ing.fat_g * factor
        totals["total_carbs_g"] += ing.carbs_g * factor
        totals["total_fibre_g"] += ing.fibre_g * factor

    return {k: round(v, 2) for k, v in totals.items()}


def recipe_to_read(recipe) -> RecipeRead:
    """Convert a Recipe ORM model (with eager-loaded ingredient_links) to RecipeRead."""
    ingredients = [
        RecipeIngredientRead(
            ingredient=IngredientRead.model_validate(link.ingredient),
            quantity=link.quantity,
            unit=link.unit,
        )
        for link in recipe.ingredient_links
        if link.ingredient is not None
    ]
    nutrition = compute_recipe_nutrition(recipe.ingredient_links)
    return RecipeRead(
        id=recipe.id,
        title=recipe.title,
        description=recipe.description,
        servings=recipe.servings,
        instructions=recipe.instructions or [],
        created_at=recipe.created_at,
        ingredients=ingredients,
        **nutrition,
    )
