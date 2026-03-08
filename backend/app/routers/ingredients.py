import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Ingredient, RecipeIngredient
from app.schemas import IngredientCreate, IngredientRead, IngredientUpdate

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("", response_model=list[IngredientRead])
def list_ingredients(
    search: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    stmt = select(Ingredient)
    if search:
        stmt = stmt.where(Ingredient.name.ilike(f"%{search}%"))  # type: ignore[union-attr]
    return session.exec(stmt.order_by(Ingredient.name)).all()


@router.get("/{ingredient_id}", response_model=IngredientRead)
def get_ingredient(
    ingredient_id: uuid.UUID,
    session: Session = Depends(get_session),
):
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return ingredient


@router.post("", response_model=IngredientRead, status_code=status.HTTP_201_CREATED)
def create_ingredient(
    body: IngredientCreate,
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(Ingredient).where(Ingredient.name == body.name)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ingredient with this name already exists")

    ingredient = Ingredient.model_validate(body)
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


@router.put("/{ingredient_id}", response_model=IngredientRead)
def update_ingredient(
    ingredient_id: uuid.UUID,
    body: IngredientUpdate,
    session: Session = Depends(get_session),
):
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ingredient, key, value)

    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(
    ingredient_id: uuid.UUID,
    session: Session = Depends(get_session),
):
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    used = session.exec(
        select(RecipeIngredient).where(RecipeIngredient.ingredient_id == ingredient_id)
    ).first()
    if used:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete ingredient that is used in recipes",
        )

    session.delete(ingredient)
    session.commit()
