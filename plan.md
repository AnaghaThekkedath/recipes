# Implementation Plan — Recipes App

Detailed task breakdown derived from [Recipe.md](./Recipe.md). Each phase is split into atomic tasks with acceptance criteria.

---

## Phase 0 — Initialise Git Repo

Remote: `https://github.com/AnaghaThekkedath/recipes.git`

- [ ] `git init`
- [ ] Create `.gitignore` with entries for:
  - Python: `__pycache__/`, `*.pyc`, `.venv/`, `*.db`, `.env`
  - Node: `node_modules/`, `dist/`
  - IDE: `.vscode/`, `.idea/`
  - OS: `.DS_Store`, `Thumbs.db`
- [ ] Add remote: `git remote add origin https://github.com/AnaghaThekkedath/recipes.git`
- [ ] Initial commit with `Recipe.md`, `plan.md`, and `.gitignore`
- [ ] Push to `main`: `git push -u origin main`

**Done when:** repo is live on GitHub with the three initial files.

---

## Phase 1 — Backend: Project Setup, Models & Ingredient/Recipe CRUD

### 1.1 Project scaffold

- [ ] Create `backend/` directory with `app/` package, `routers/` sub-package
- [ ] Create `requirements.txt` with pinned versions:
  - `fastapi`, `uvicorn[standard]`, `sqlmodel`, `alembic`, `mangum`, `libsql-experimental` (Turso driver)
- [ ] Create `app/main.py` — FastAPI app instance, CORS middleware (allow `*` for dev, lock down later), lifespan hook to init DB
- [ ] Add a `GET /health` endpoint that returns `{"status": "ok"}` for smoke testing

**Done when:** `uvicorn app.main:app --reload` starts and `/health` returns 200.

### 1.2 Database setup

- [ ] Create `app/database.py`:
  - SQLite engine for local dev (`sqlite:///recipes.db`)
  - Environment variable `DATABASE_URL` to override with Turso connection string in production
  - `get_session` dependency (yields a `Session`, auto-closes)
  - `create_db_and_tables()` called on app startup
- [ ] Initialise Alembic: `alembic init alembic`, point `sqlalchemy.url` at the same engine
- [ ] Create initial migration after models are defined (task 1.3)

**Done when:** app startup creates `recipes.db` with empty tables. `alembic current` shows head.

### 1.3 SQLModel table definitions

- [ ] Create `app/models.py` with:
  - `Ingredient` table — columns: `id` (UUID, default `uuid4`), `name` (unique index), `calories`, `protein_g`, `fat_g`, `carbs_g`, `fibre_g`, `default_unit`
  - `Recipe` table — columns: `id`, `title`, `description`, `servings`, `instructions` (JSON column storing `list[str]`), `created_at` (default `utcnow`)
  - `RecipeIngredient` link table — columns: `recipe_id` (FK), `ingredient_id` (FK), `quantity`, `unit`. Composite PK on `(recipe_id, ingredient_id)`
  - `MealSlot` Python enum: `breakfast`, `morning_snack`, `lunch`, `evening_snack`, `dinner`
  - `WeekSchedule` table — columns: `id`, `recipe_id` (FK), `date`, `meal_slot` (enum), `servings`. Unique constraint on `(date, meal_slot)`
- [ ] Set up SQLModel `Relationship` fields for eager loading:
  - `Recipe.ingredients` → list of `RecipeIngredient` (with nested `Ingredient`)
  - `WeekSchedule.recipe` → `Recipe`

**Done when:** `alembic revision --autogenerate -m "initial"` creates a clean migration and `alembic upgrade head` applies it.

### 1.4 Pydantic request/response schemas

- [ ] Create `app/schemas.py`:
  - `IngredientCreate` / `IngredientUpdate` / `IngredientRead`
  - `RecipeIngredientEntry` (ingredient_id, quantity, unit) — used when creating/updating a recipe
  - `RecipeCreate` (title, description, servings, instructions: list[str], ingredients: list[RecipeIngredientEntry])
  - `RecipeUpdate` — same fields, all optional
  - `RecipeRead` — includes nested ingredients and computed nutrition fields (`total_calories`, `total_protein_g`, `total_fat_g`, `total_carbs_g`, `total_fibre_g`)
  - Nutrition computation: a helper function or `@computed_field` that iterates over recipe ingredients and sums `(ingredient.<nutrient> * quantity / 100)`

**Done when:** schemas import cleanly, nutrition computation has a unit test.

### 1.5 Ingredient CRUD router

- [ ] Create `app/routers/ingredients.py`:
  - `GET /ingredients` — return all ingredients, support optional `?search=` query param (name LIKE)
  - `GET /ingredients/{id}` — return single ingredient or 404
  - `POST /ingredients` — create, return 201. Reject duplicate names with 409
  - `PUT /ingredients/{id}` — partial update, return 200 or 404
  - `DELETE /ingredients/{id}` — delete, return 204 or 404. If ingredient is used in recipes, return 409 with message
- [ ] Register router in `main.py` with prefix `/ingredients`

**Done when:** all five endpoints work via Swagger UI (`/docs`). Test with curl or httpie.

### 1.6 Recipe CRUD router

- [ ] Create `app/routers/recipes.py`:
  - `GET /recipes` — return all recipes with nested ingredients and computed nutrition totals. Support `?search=` on title
  - `GET /recipes/{id}` — full detail with ingredients + nutrition
  - `POST /recipes` — accepts `RecipeCreate`. In a transaction: insert `Recipe`, then bulk-insert `RecipeIngredient` rows. Validate all ingredient IDs exist (422 if not). Return 201
  - `PUT /recipes/{id}` — accepts `RecipeUpdate`. Replace ingredient list if provided (delete old links, insert new). Return 200 or 404
  - `DELETE /recipes/{id}` — cascade-delete `RecipeIngredient` rows, then recipe. Return 204 or 404
- [ ] Register router in `main.py` with prefix `/recipes`

**Done when:** can create a recipe with 3+ ingredients via Swagger, GET returns correct nutrition totals.

---

## Phase 2 — Backend: Schedule & Shopping List

### 2.1 Schedule router

- [ ] Create `app/routers/schedule.py`:
  - `GET /schedule?week_start=YYYY-MM-DD` — return all `WeekSchedule` entries for the 7-day range `[week_start, week_start + 6 days]`, each with nested `Recipe` (including ingredients + nutrition). If `week_start` is missing, default to current Monday
  - `POST /schedule` — body: `{recipe_id, date, meal_slot, servings}`. Validate: recipe exists (404), date is valid ISO (422), meal_slot is valid enum value (422), slot not already taken (409). Return 201
  - `DELETE /schedule/{id}` — remove entry, return 204 or 404
- [ ] Register router in `main.py` with prefix `/schedule`

**Done when:** can schedule 3 meals across different days, GET returns them grouped correctly.

### 2.2 Shopping list endpoint

- [ ] Create `app/routers/shopping_list.py`:
  - `GET /shopping-list?week_start=YYYY-MM-DD`:
    1. Query all `WeekSchedule` entries for the 7-day window
    2. For each entry, get its recipe's `RecipeIngredient` list, scaled by `(schedule.servings / recipe.servings)`
    3. Aggregate by `ingredient_id + unit`: sum quantities across all scheduled meals
    4. Compute per-item nutrition: `ingredient.<nutrient> * total_quantity / 100`
    5. Compute week totals: sum all item-level nutrition
    6. Return response matching the shape in Recipe.md
- [ ] Register router in `main.py` with prefix `/shopping-list`

**Done when:** schedule 5+ meals for a week, shopping list correctly aggregates duplicate ingredients and totals match hand calculation.

### 2.3 Seed data script (optional but helpful)

- [ ] Create `backend/seed.py`:
  - Insert 8–10 common ingredients with real nutritional data (chicken, rice, eggs, broccoli, olive oil, etc.)
  - Insert 3–4 sample recipes referencing those ingredients
  - Insert a sample week schedule
- [ ] Add `"seed"` script to a Makefile or document the command

**Done when:** running `python seed.py` populates the DB and all endpoints return meaningful data.

---

## Phase 3 — Frontend: Recipe List & Detail Pages

### 3.1 Project scaffold

- [ ] Scaffold with `npm create vite@latest frontend -- --template react-ts`
- [ ] Install dependencies: `react-router-dom`, `@tanstack/react-query`, `tailwindcss`, `@tailwindcss/vite`, `axios`
- [ ] Configure Tailwind (`tailwind.config.js`, add directives to `index.css`)
- [ ] Set up `api/client.ts` — Axios instance with `baseURL` from env var (`VITE_API_URL`, default `http://localhost:8000`)
- [ ] Set up `QueryClientProvider` and `BrowserRouter` in `main.tsx`
- [ ] Create `App.tsx` with route definitions:
  - `/` → `RecipesPage`
  - `/recipes/:id` → `RecipeDetailPage`
  - `/recipes/new` → `RecipeFormPage`
  - `/recipes/:id/edit` → `RecipeFormPage`
  - `/schedule` → `SchedulePage`
  - `/shopping-list` → `ShoppingListPage`
- [ ] Create a shared layout with a top nav bar (links: Recipes, Schedule, Shopping List)

**Done when:** `npm run dev` starts, navigation between empty pages works.

### 3.2 TypeScript types

- [ ] Create `types/index.ts` mirroring backend schemas:
  - `Ingredient`, `RecipeIngredientEntry`, `Recipe` (with nutrition fields), `MealSlot` enum, `ScheduleEntry`, `ShoppingListResponse`

### 3.3 API hooks

- [ ] Create `api/ingredients.ts` — `useIngredients()`, `useCreateIngredient()`, etc. using TanStack Query
- [ ] Create `api/recipes.ts` — `useRecipes()`, `useRecipe(id)`, `useCreateRecipe()`, `useUpdateRecipe()`, `useDeleteRecipe()`
- [ ] Create `api/schedule.ts` — `useSchedule(weekStart)`, `useAddToSchedule()`, `useRemoveFromSchedule()`
- [ ] Create `api/shoppingList.ts` — `useShoppingList(weekStart)`

**Done when:** hooks import cleanly, type-safe, and console-log data when pages mount.

### 3.4 RecipesPage

- [ ] Grid layout of `RecipeCard` components (responsive: 1 col mobile, 2 col tablet, 3 col desktop)
- [ ] Each `RecipeCard` shows: title, description snippet, serving count, total calories badge
- [ ] Search input at the top — debounced, filters via query param `?search=`
- [ ] "Add Recipe" button linking to `/recipes/new`
- [ ] Loading skeleton while fetching, empty state if no recipes

**Done when:** page renders cards from API, search filters in real-time, click navigates to detail.

### 3.5 RecipeDetailPage

- [ ] Hero section: title, description, servings
- [ ] Ingredients table: columns — Name, Quantity, Unit, Calories, Protein, Fat, Carbs, Fibre (per-ingredient, scaled to the ingredient's quantity in this recipe)
- [ ] Nutrition summary bar below the table: total calories, protein, fat, carbs, fibre for the full recipe
- [ ] Instructions: ordered list, each step as a numbered block
- [ ] Action buttons: Edit (→ `/recipes/:id/edit`), Delete (confirm dialog, then redirect to list)

**Done when:** detail page fully renders a seeded recipe with correct nutrition math.

---

## Phase 4 — Frontend: Recipe Create/Edit Form

### 4.1 RecipeFormPage (shared for create & edit)

- [ ] If URL has `:id`, fetch recipe and pre-fill form; otherwise blank
- [ ] Fields:
  - Title (text input, required)
  - Description (textarea)
  - Servings (number input, min 1)
- [ ] Dynamic ingredient rows:
  - Each row: ingredient select/autocomplete (from `useIngredients`), quantity input, unit select
  - "Add ingredient" button appends a blank row
  - Remove button per row (min 1 ingredient required)
  - Option to create a new ingredient inline (modal or expandable sub-form with name + nutrition fields)
- [ ] Dynamic instruction steps:
  - Each step: textarea for the instruction text
  - "Add step" button appends a blank step
  - Remove button per step (min 1 step required)
  - Drag handle or up/down buttons to reorder
- [ ] Submit: POST or PUT depending on create/edit mode. On success, redirect to detail page
- [ ] Validation: required fields, positive numbers, at least 1 ingredient and 1 instruction step

**Done when:** can create a new recipe with 3 ingredients and 4 steps, edit it, and see changes on detail page.

---

## Phase 5 — Frontend: Weekly Schedule

### 5.1 WeekGrid component

- [ ] 7 columns (Mon → Sun), 5 rows (breakfast, morning_snack, lunch, evening_snack, dinner)
- [ ] Row headers on the left: slot labels (formatted nicely, e.g. "Morning Snack")
- [ ] Column headers: day name + date (e.g. "Mon 9 Mar")
- [ ] Week navigation: "← Prev Week" / "Next Week →" buttons, "Today" button to jump to current week
- [ ] Responsive: horizontal scroll on mobile, or collapse to a day-at-a-time view

### 5.2 MealSlot component

- [ ] Empty state: "+" icon, clickable to open `RecipePicker`
- [ ] Filled state: recipe title (truncated), calorie badge, click to view detail or remove
- [ ] Remove: small "×" button, confirm dialog, calls `DELETE /schedule/:id`

### 5.3 RecipePicker modal

- [ ] Opens when clicking an empty slot
- [ ] Searchable list of all recipes (reuse `useRecipes` with search)
- [ ] Each option shows: title, calories per serving
- [ ] Servings input (defaults to recipe's default servings)
- [ ] "Assign" button: calls `POST /schedule` with selected recipe, date, meal_slot, servings
- [ ] On success: close modal, invalidate schedule query so grid updates

**Done when:** can fill out an entire week of meals, navigate between weeks, remove individual entries.

---

## Phase 6 — Frontend: Shopping List

### 6.1 ShoppingListPage

- [ ] Week selector: same week nav as schedule page (prev/next/today), kept in sync via URL query param
- [ ] Ingredient table: columns — Name, Total Quantity, Unit, Calories, Protein, Fat, Carbs, Fibre
- [ ] Sort by: name (default) or any nutrition column
- [ ] Weekly nutrition totals row at the bottom of the table (bold/highlighted)
- [ ] Empty state: "No meals scheduled for this week" with link to Schedule page
- [ ] Print / copy button: formats the list as plain text and copies to clipboard (or opens print dialog)

**Done when:** shopping list accurately reflects the scheduled week, quantities aggregate correctly across meals.

---

## Phase 7 — Polish

### 7.1 Error handling

- [ ] Backend: consistent error response shape `{"detail": "message"}` for all 4xx/5xx
- [ ] Frontend: global error boundary component wrapping the app
- [ ] Per-page: toast notifications for mutation success/failure (use a lightweight toast lib or custom component)
- [ ] Network error state: retry button on failed queries

### 7.2 Loading states

- [ ] Skeleton loaders for RecipesPage grid (shimmer cards)
- [ ] Spinner or skeleton for RecipeDetailPage
- [ ] Schedule grid: skeleton cells while loading
- [ ] Shopping list: skeleton table rows
- [ ] Button loading states during mutations (disable + spinner)

### 7.3 Responsive design

- [ ] Test and fix layout at 375px (mobile), 768px (tablet), 1280px (desktop)
- [ ] Mobile nav: hamburger menu or bottom tab bar
- [ ] Schedule grid: horizontal scroll or single-day view on mobile
- [ ] Recipe form: stack ingredient row fields vertically on mobile

### 7.4 Misc quality

- [ ] Add `<title>` and meta tags per page (optional: react-helmet)
- [ ] 404 page for unknown routes
- [ ] Favicon
- [ ] Validate all API inputs server-side (FastAPI handles most via Pydantic, but double-check edge cases)

---

## Phase 8 — Deployment

### 8.1 Backend deployment (AWS Lambda)

- [ ] Create `Dockerfile` for the Lambda container image (or use a zip deployment with Mangum)
- [ ] Create `handler.py` at backend root:
  ```python
  from mangum import Mangum
  from app.main import app
  handler = Mangum(app)
  ```
- [ ] Set up AWS resources (via console, CLI, or SAM/CDK):
  - Lambda function (Python 3.12 runtime, 256 MB memory, 30 s timeout)
  - HTTP API Gateway (v2) with `$default` route → Lambda integration
  - Environment variable `DATABASE_URL` pointing to Turso
- [ ] Create Turso database: `turso db create recipes-app`
- [ ] Get Turso connection URL + auth token, store as Lambda env vars
- [ ] Run Alembic migrations against Turso (one-time, from local machine or a CI step)
- [ ] Test: hit the API Gateway URL `/health` and verify

### 8.2 Frontend deployment (S3 + CloudFront)

- [ ] Build frontend: `npm run build` → `dist/` folder
- [ ] Create S3 bucket (private, block public access)
- [ ] Upload `dist/` contents to S3
- [ ] Create CloudFront distribution:
  - Origin: S3 bucket (via OAC — Origin Access Control)
  - Default root object: `index.html`
  - Custom error response: 403/404 → `/index.html` with 200 (for SPA client-side routing)
  - Enable compression (gzip/brotli)
- [ ] Set `VITE_API_URL` to the API Gateway URL before building
- [ ] Test: hit CloudFront domain, verify app loads and API calls work

### 8.3 CI (optional but recommended)

- [ ] GitHub Actions workflow:
  - On push to `main`:
    1. Backend: install deps, run linter, run tests, deploy Lambda (via SAM or AWS CLI)
    2. Frontend: install deps, build, sync to S3, invalidate CloudFront cache
  - Store AWS credentials and Turso token as GitHub Secrets

---

## Quick Reference — File Checklist

```
recipes/
├── .gitignore
├── Recipe.md                          ← architecture doc
├── plan.md                            ← this file
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── ingredients.py
│   │       ├── recipes.py
│   │       ├── schedule.py
│   │       └── shopping_list.py
│   ├── handler.py                     ← Lambda entry point
│   ├── seed.py
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── Makefile
└── frontend/
    ├── public/
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── types/index.ts
    │   ├── api/
    │   │   ├── client.ts
    │   │   ├── ingredients.ts
    │   │   ├── recipes.ts
    │   │   ├── schedule.ts
    │   │   └── shoppingList.ts
    │   ├── pages/
    │   │   ├── RecipesPage.tsx
    │   │   ├── RecipeDetailPage.tsx
    │   │   ├── RecipeFormPage.tsx
    │   │   ├── SchedulePage.tsx
    │   │   └── ShoppingListPage.tsx
    │   └── components/
    │       ├── Layout.tsx
    │       ├── RecipeCard.tsx
    │       ├── IngredientRow.tsx
    │       ├── WeekGrid.tsx
    │       ├── MealSlot.tsx
    │       ├── RecipePicker.tsx
    │       └── ShoppingItem.tsx
    ├── index.html
    ├── tailwind.config.js
    ├── vite.config.ts
    ├── tsconfig.json
    └── package.json
```
