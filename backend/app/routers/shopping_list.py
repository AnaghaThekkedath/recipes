from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.database import get_session
from app.models import Recipe, RecipeIngredient, WeekSchedule
from app.schemas import (
    IngredientRead,
    ShoppingListItem,
    ShoppingListResponse,
    ShoppingListTotals,
)

router = APIRouter(prefix="/shopping-list", tags=["shopping-list"])


def _current_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


@router.get("", response_model=ShoppingListResponse)
def get_shopping_list(
    week_start: date | None = Query(default=None),
    session: Session = Depends(get_session),
):
    start = week_start or _current_monday()
    end = start + timedelta(days=6)

    stmt = (
        select(WeekSchedule)
        .where(WeekSchedule.date >= start.isoformat())
        .where(WeekSchedule.date <= end.isoformat())
        .options(
            selectinload(WeekSchedule.recipe)  # type: ignore[arg-type]
            .selectinload(Recipe.ingredient_links)  # type: ignore[arg-type]
            .selectinload(RecipeIngredient.ingredient)  # type: ignore[arg-type]
        )
    )
    entries = session.exec(stmt).all()

    # Aggregate quantities: key = (ingredient_id, unit)
    # Store: {key: {"ingredient": Ingredient, "quantity": float}}
    aggregated: dict[tuple, dict] = defaultdict(lambda: {"ingredient": None, "quantity": 0.0})

    for entry in entries:
        recipe = entry.recipe
        if recipe is None:
            continue
        scale = entry.servings / recipe.servings if recipe.servings else 1.0
        for link in recipe.ingredient_links:
            if link.ingredient is None:
                continue
            key = (link.ingredient.id, link.unit)
            agg = aggregated[key]
            agg["ingredient"] = link.ingredient
            agg["quantity"] += link.quantity * scale

    # Build items and compute totals
    items: list[ShoppingListItem] = []
    total_cal = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carbs = 0.0
    total_fibre = 0.0

    for (ing_id, unit), data in sorted(aggregated.items(), key=lambda x: x[1]["ingredient"].name):
        ing = data["ingredient"]
        qty = round(data["quantity"], 2)
        factor = qty / 100.0

        items.append(
            ShoppingListItem(
                ingredient=IngredientRead.model_validate(ing),
                total_quantity=qty,
                unit=unit,
            )
        )

        total_cal += ing.calories * factor
        total_protein += ing.protein_g * factor
        total_fat += ing.fat_g * factor
        total_carbs += ing.carbs_g * factor
        total_fibre += ing.fibre_g * factor

    return ShoppingListResponse(
        week_start=start,
        items=items,
        totals=ShoppingListTotals(
            calories=round(total_cal, 2),
            protein_g=round(total_protein, 2),
            fat_g=round(total_fat, 2),
            carbs_g=round(total_carbs, 2),
            fibre_g=round(total_fibre, 2),
        ),
    )
