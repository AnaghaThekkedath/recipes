import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.database import get_session
from app.models import Recipe, RecipeIngredient, WeekSchedule
from app.schemas import RecipeRead, ScheduleCreate, ScheduleRead, recipe_to_read

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _current_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _load_schedule_entry(session: Session, entry_id: uuid.UUID) -> WeekSchedule:
    stmt = (
        select(WeekSchedule)
        .where(WeekSchedule.id == entry_id)
        .options(
            selectinload(WeekSchedule.recipe)  # type: ignore[arg-type]
            .selectinload(Recipe.ingredient_links)  # type: ignore[arg-type]
            .selectinload(RecipeIngredient.ingredient)  # type: ignore[arg-type]
        )
    )
    entry = session.exec(stmt).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Schedule entry not found")
    return entry


def _entry_to_read(entry: WeekSchedule) -> ScheduleRead:
    return ScheduleRead(
        id=entry.id,
        recipe_id=entry.recipe_id,
        date=date.fromisoformat(entry.date),
        meal_slot=entry.meal_slot,
        servings=entry.servings,
        recipe=recipe_to_read(entry.recipe),
    )


@router.get("", response_model=list[ScheduleRead])
def list_schedule(
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
        .order_by(WeekSchedule.date, WeekSchedule.meal_slot)  # type: ignore[arg-type]
    )
    entries = session.exec(stmt).all()
    return [_entry_to_read(e) for e in entries]


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule_entry(
    body: ScheduleCreate,
    session: Session = Depends(get_session),
):
    # Validate recipe exists
    recipe = session.get(Recipe, body.recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Check slot not already taken
    existing = session.exec(
        select(WeekSchedule).where(
            WeekSchedule.date == body.date.isoformat(),
            WeekSchedule.meal_slot == body.meal_slot,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Slot {body.meal_slot.value} on {body.date} is already taken",
        )

    entry = WeekSchedule(
        recipe_id=body.recipe_id,
        date=body.date.isoformat(),
        meal_slot=body.meal_slot,
        servings=body.servings,
    )
    session.add(entry)
    session.commit()

    loaded = _load_schedule_entry(session, entry.id)
    return _entry_to_read(loaded)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_entry(
    entry_id: uuid.UUID,
    session: Session = Depends(get_session),
):
    entry = session.get(WeekSchedule, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Schedule entry not found")
    session.delete(entry)
    session.commit()
