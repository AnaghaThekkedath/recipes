import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Ingredient, Recipe, RecipeIngredient
from app.schemas import RecipeCreate, RecipeRead, RecipeUpdate, recipe_to_read

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _load_recipe(session: Session, recipe_id: uuid.UUID) -> Recipe:
    stmt = (
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.ingredient_links).selectinload(RecipeIngredient.ingredient)  # type: ignore[arg-type]
        )
    )
    recipe = session.exec(stmt).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


def _sync_ingredients(
    session: Session,
    recipe: Recipe,
    entries: list,
) -> None:
    """Replace all ingredient links for a recipe."""
    session.exec(  # type: ignore[call-overload]
        select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
    )
    for old_link in list(recipe.ingredient_links):
        session.delete(old_link)
    session.flush()

    ingredient_ids = {e.ingredient_id for e in entries}
    existing = session.exec(
        select(Ingredient).where(Ingredient.id.in_(ingredient_ids))  # type: ignore[union-attr]
    ).all()
    if len(existing) != len(ingredient_ids):
        found = {i.id for i in existing}
        missing = ingredient_ids - found
        raise HTTPException(
            status_code=422,
            detail=f"Ingredient(s) not found: {[str(m) for m in missing]}",
        )

    for entry in entries:
        link = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=entry.ingredient_id,
            quantity=entry.quantity,
            unit=entry.unit,
        )
        session.add(link)


@router.get("", response_model=list[RecipeRead])
def list_recipes(
    search: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    stmt = select(Recipe).options(
        selectinload(Recipe.ingredient_links).selectinload(RecipeIngredient.ingredient)  # type: ignore[arg-type]
    )
    if search:
        stmt = stmt.where(Recipe.title.ilike(f"%{search}%"))  # type: ignore[union-attr]
    recipes = session.exec(stmt.order_by(Recipe.created_at.desc())).all()  # type: ignore[union-attr]
    return [recipe_to_read(r) for r in recipes]


@router.get("/{recipe_id}", response_model=RecipeRead)
def get_recipe(
    recipe_id: uuid.UUID,
    session: Session = Depends(get_session),
):
    recipe = _load_recipe(session, recipe_id)
    return recipe_to_read(recipe)


@router.post("", response_model=RecipeRead, status_code=status.HTTP_201_CREATED)
def create_recipe(
    body: RecipeCreate,
    session: Session = Depends(get_session),
):
    recipe = Recipe(
        title=body.title,
        description=body.description,
        servings=body.servings,
        instructions=body.instructions,
    )
    session.add(recipe)
    session.flush()

    if body.ingredients:
        _sync_ingredients(session, recipe, body.ingredients)

    session.commit()
    loaded = _load_recipe(session, recipe.id)
    return recipe_to_read(loaded)


@router.put("/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    recipe_id: uuid.UUID,
    body: RecipeUpdate,
    session: Session = Depends(get_session),
):
    recipe = _load_recipe(session, recipe_id)

    update_data = body.model_dump(exclude_unset=True, exclude={"ingredients"})
    for key, value in update_data.items():
        setattr(recipe, key, value)

    if body.ingredients is not None:
        _sync_ingredients(session, recipe, body.ingredients)

    session.add(recipe)
    session.commit()
    loaded = _load_recipe(session, recipe.id)
    return recipe_to_read(loaded)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: uuid.UUID,
    session: Session = Depends(get_session),
):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    links = session.exec(
        select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id)
    ).all()
    for link in links:
        session.delete(link)

    session.delete(recipe)
    session.commit()
