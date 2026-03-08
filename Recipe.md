# Recipes App — Project Plan

## 1. Overview

A full-stack recipes app that lets users browse recipes, view nutritional info per ingredient, and schedule meals for the week. A generated shopping list aggregates all ingredients needed for the scheduled week.

---

## 2. Data Model

### 2.1 Ingredient

| Column       | Type | Notes                          |
| ------------ | ---- | ------------------------------ |
| id           | UUID | Primary key                    |
| name         | TEXT | Unique, e.g. "Chicken Breast"  |
| calories     | REAL | Per 100 g                      |
| protein_g    | REAL | Grams per 100 g                |
| fat_g        | REAL | Grams per 100 g                |
| carbs_g      | REAL | Grams per 100 g                |
| fibre_g      | REAL | Grams per 100 g                |
| default_unit | TEXT | "g", "ml", "piece", etc.       |

### 2.2 Recipe

| Column       | Type    | Notes                        |
| ------------ | ------- | ---------------------------- |
| id           | UUID    | Primary key                  |
| title        | TEXT    |                              |
| description  | TEXT    | Short blurb                  |
| servings     | INTEGER | Default serving count        |
| instructions | JSON    | Ordered list of step strings |
| created_at   | TEXT    | ISO-8601 timestamp           |

**Computed nutrition fields** (derived from `RecipeIngredient` quantities × `Ingredient` nutritional values, returned in API responses but not stored in the DB):

| Field             | Type | Notes                                                        |
| ----------------- | ---- | ------------------------------------------------------------ |
| total_calories    | REAL | Sum of (ingredient calories per 100 g × quantity / 100)     |
| total_protein_g   | REAL | Sum of (ingredient protein per 100 g × quantity / 100)      |
| total_fat_g       | REAL | Sum of (ingredient fat per 100 g × quantity / 100)          |
| total_carbs_g     | REAL | Sum of (ingredient carbs per 100 g × quantity / 100)        |
| total_fibre_g     | REAL | Sum of (ingredient fibre per 100 g × quantity / 100)        |

### 2.3 RecipeIngredient (join table)

| Column        | Type | Notes                            |
| ------------- | ---- | -------------------------------- |
| recipe_id     | UUID | FK → Recipe                      |
| ingredient_id | UUID | FK → Ingredient                  |
| quantity      | REAL | Amount in the given unit         |
| unit          | TEXT | "g", "ml", "tbsp", "piece", etc. |

Composite PK: `(recipe_id, ingredient_id)`

### 2.4 WeekSchedule

| Column    | Type    | Notes                                |
| --------- | ------- | ------------------------------------ |
| id        | UUID    | Primary key                          |
| recipe_id | UUID    | FK → Recipe                          |
| date      | TEXT    | ISO date, e.g. "2026-03-09"         |
| meal_slot | ENUM    | See `MealSlot` enum below            |
| servings  | INTEGER | Override serving count for this slot |

**MealSlot enum values:** `breakfast`, `morning_snack`, `lunch`, `evening_snack`, `dinner`

Unique constraint: `(date, meal_slot)` — one recipe per slot per day.

---

## 3. Backend

### 3.1 Tech Stack

| Concern    | Choice                                                                                    |
| ---------- | ----------------------------------------------------------------------------------------- |
| Runtime    | **Python 3.12 + FastAPI** — lightweight, async, easy to deploy serverless                 |
| ORM        | **SQLModel** (SQLAlchemy + Pydantic in one) — minimal boilerplate                         |
| Local DB   | **SQLite** via a single file — zero setup for development                                 |
| Cloud DB   | **Turso** (libSQL hosted SQLite) — generous free tier, serverless-friendly, ~$0 for hobby |
| Deployment | **AWS Lambda + API Gateway** via Mangum adapter, or **Fly.io** for a simple container     |
| Migrations | **Alembic** — standard SQLAlchemy migration tool                                          |

### 3.2 API Endpoints

#### Ingredients

| Method | Path               | Description          |
| ------ | ------------------ | -------------------- |
| GET    | `/ingredients`     | List all ingredients |
| GET    | `/ingredients/:id` | Get one ingredient   |
| POST   | `/ingredients`     | Create ingredient    |
| PUT    | `/ingredients/:id` | Update ingredient    |
| DELETE | `/ingredients/:id` | Delete ingredient    |

#### Recipes

| Method | Path           | Description                         |
| ------ | -------------- | ----------------------------------- |
| GET    | `/recipes`     | List all recipes (with ingredients) |
| GET    | `/recipes/:id` | Get single recipe with full details |
| POST   | `/recipes`     | Create recipe + link ingredients    |
| PUT    | `/recipes/:id` | Update recipe                       |
| DELETE | `/recipes/:id` | Delete recipe                       |

#### Week Schedule

| Method | Path                              | Description                                  |
| ------ | --------------------------------- | -------------------------------------------- |
| GET    | `/schedule?week_start=YYYY-MM-DD` | Get all scheduled meals for the 7-day window |
| POST   | `/schedule`                       | Add a recipe to a date + meal slot           |
| DELETE | `/schedule/:id`                   | Remove a scheduled meal                      |

#### Shopping List

| Method | Path                                   | Description                                                   |
| ------ | -------------------------------------- | ------------------------------------------------------------- |
| GET    | `/shopping-list?week_start=YYYY-MM-DD` | Aggregate ingredients across all scheduled meals for the week |

**Shopping list response shape:**

```json
{
  "week_start": "2026-03-09",
  "items": [
    {
      "ingredient": {
        "id": "...",
        "name": "Chicken Breast",
        "calories": 165,
        "protein_g": 31,
        "fat_g": 3.6,
        "carbs_g": 0,
        "fibre_g": 0
      },
      "total_quantity": 600,
      "unit": "g"
    }
  ],
  "totals": {
    "calories": 4520,
    "protein_g": 310,
    "fat_g": 95,
    "carbs_g": 480,
    "fibre_g": 42
  }
}
```

### 3.3 Project Structure

```
backend/
├── app/
│   ├── main.py            # FastAPI app, CORS, lifespan
│   ├── database.py        # Engine, session, create_all
│   ├── models.py          # SQLModel table classes
│   ├── routers/
│   │   ├── ingredients.py
│   │   ├── recipes.py
│   │   ├── schedule.py
│   │   └── shopping_list.py
│   └── schemas.py         # Request/response Pydantic models
├── alembic/               # Migrations
├── alembic.ini
├── requirements.txt
└── Dockerfile
```

---

## 4. Frontend

### 4.1 Tech Stack

| Concern     | Choice                                                |
| ----------- | ----------------------------------------------------- |
| Framework   | **React 18** with Vite                                |
| Routing     | **React Router v6**                                   |
| State/Fetch | **TanStack Query (React Query)** — caching, mutations |
| Styling     | **Tailwind CSS** — fast, utility-first                |
| Calendar    | Custom 7-day grid component (no heavy lib needed)     |

### 4.2 Pages & Components

```
frontend/src/
├── pages/
│   ├── RecipesPage.tsx          # Grid/list of all recipes
│   ├── RecipeDetailPage.tsx     # Single recipe: ingredients table + instructions
│   ├── RecipeFormPage.tsx       # Create / edit recipe
│   ├── SchedulePage.tsx         # Weekly calendar with drag-to-assign
│   └── ShoppingListPage.tsx     # Aggregated shopping list for selected week
├── components/
│   ├── RecipeCard.tsx           # Thumbnail card used in the grid
│   ├── IngredientRow.tsx        # Row in recipe detail ingredient table
│   ├── WeekGrid.tsx             # 7-column grid (Mon–Sun), 5 rows (meal slots)
│   ├── MealSlot.tsx             # Single slot in the week grid
│   ├── RecipePicker.tsx         # Modal/popover to pick a recipe for a slot
│   └── ShoppingItem.tsx         # Single line item in shopping list
├── api/
│   └── client.ts               # Axios/fetch wrapper, base URL config
├── App.tsx
└── main.tsx
```

### 4.3 Key UX Flows

1. **Browse recipes** — paginated grid with search/filter. Click a card to view details.
2. **Create/edit recipe** — form with dynamic ingredient rows (pick from existing ingredients or create inline). Instructions as an ordered list of text inputs with add/remove/reorder.
3. **Schedule meals** — weekly grid. Click an empty slot → recipe picker modal. Click a filled slot → view or remove.
4. **Shopping list** — auto-generated from the current week's schedule. Shows aggregated quantities, total macros, and a print/copy button.

---

## 5. Deployment

**All infrastructure on AWS** to keep things in one place.

### Backend: AWS Lambda + API Gateway + Turso

| Component       | Details                                                        | Est. Cost    |
| --------------- | -------------------------------------------------------------- | ------------ |
| AWS Lambda      | FastAPI wrapped with **Mangum** adapter. Cold starts ~1 s.     | ~$0/mo       |
| API Gateway     | HTTP API (v2) — routes to Lambda                               | ~$0–$1/mo    |
| Turso (libSQL)  | Hosted SQLite. Free tier: 8 GB storage, 1B row reads/mo.      | $0           |

### Frontend: S3 + CloudFront

| Component       | Details                                                        | Est. Cost    |
| --------------- | -------------------------------------------------------------- | ------------ |
| S3              | Static hosting for the Vite build output                       | ~$0/mo       |
| CloudFront      | CDN in front of S3 for HTTPS + caching + custom domain         | ~$0–$1/mo    |

**Total estimated cost: $0–$2/mo** for hobby-level traffic.

---

## 6. Implementation Order

| Phase | Scope                                               | Est. Effort |
| ----- | --------------------------------------------------- | ----------- |
| 1     | Backend: models, DB setup, ingredient + recipe CRUD | 3–4 hrs     |
| 2     | Backend: schedule + shopping list endpoints         | 2 hrs       |
| 3     | Frontend: recipe list + detail pages                | 3 hrs       |
| 4     | Frontend: recipe create/edit form                   | 2–3 hrs     |
| 5     | Frontend: weekly schedule grid + recipe picker      | 3 hrs       |
| 6     | Frontend: shopping list page                        | 1–2 hrs     |
| 7     | Polish: error handling, loading states, responsive  | 2 hrs       |
| 8     | Deployment: Lambda + S3/CloudFront + CI             | 1–2 hrs     |

**Total estimate: ~18–22 hours**

---

## 7. Future Enhancements (out of scope for v1)

- User authentication (multiple households)
- Recipe tags / categories / cuisine filters
- Image upload for recipes
- Portion scaling on the detail page
- "Pantry" tracker to subtract what you already have from the shopping list
- Nutritional summary per day on the schedule view
- Import recipes from URL (scrape structured data)
