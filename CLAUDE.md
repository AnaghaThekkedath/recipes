# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack recipes app: browse recipes with nutritional info, schedule weekly meals, generate shopping lists. Currently in early development — Phases 1-2 (full backend) are complete, Phase 3+ (frontend) is pending.

## Commands

### Backend setup and run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
```

Server runs at http://localhost:8000. Swagger UI at http://localhost:8000/docs.

### No tests or linter configured yet
There are no test suites or linting tools set up. When adding tests, use `pytest` (add to requirements.txt). When adding linting, use `ruff`.

## Architecture

### Backend (Python/FastAPI + SQLModel + SQLite)

- **`backend/app/main.py`** — FastAPI app with lifespan hook that auto-creates DB tables on startup. CORS allows all origins (dev mode).
- **`backend/app/database.py`** — SQLite engine, `get_session` dependency. Override with `DATABASE_URL` env var for production (Turso).
- **`backend/app/models.py`** — SQLModel table classes: `Ingredient`, `Recipe`, `RecipeIngredient` (join table with composite PK), `WeekSchedule`, `MealSlot` enum. Relationships are set up for eager loading via `selectinload`.
- **`backend/app/schemas.py`** — Pydantic request/response models. Contains `compute_recipe_nutrition()` and `recipe_to_read()` helpers that compute nutrition totals from ingredient links (nutritional values are per 100g, scaled by `quantity / 100`).
- **`backend/app/routers/`** — One file per resource: `ingredients.py`, `recipes.py`, `schedule.py`, `shopping_list.py`.
- **`backend/seed.py`** — Seeds DB with 10 ingredients, 4 recipes, and a sample week schedule. Skips if data exists.

### Key patterns
- Nutrition is computed at read time, not stored in DB. The `recipe_to_read()` converter in schemas.py handles ORM-to-response conversion with nutrition computation.
- Recipe ingredient sync (`_sync_ingredients` in recipes router) deletes all existing links then re-inserts — full replacement, not partial update.
- Ingredient deletion is blocked (409) if the ingredient is used in any recipe.
- Alembic is in requirements but not initialized — tables are auto-created via `SQLModel.metadata.create_all()`.
- UUIDs are used as primary keys throughout.

### Frontend (not yet built)
Planned: React 18 + Vite + TypeScript + Tailwind + TanStack Query. See `plan.md` for full spec.

## Implementation Plan

See `plan.md` for the detailed phased task breakdown and `Recipe.md` for the full architecture document including data model, API spec, and deployment plan. Target deployment: AWS Lambda + API Gateway + Turso (backend), S3 + CloudFront (frontend).
