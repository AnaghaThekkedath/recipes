# Recipes

A full-stack recipes app for browsing recipes, tracking nutritional info, scheduling weekly meals, and generating shopping lists.

## Prerequisites

- Python 3.12+
- Node.js 18+ *(frontend — coming soon)*

## Backend

### Setup

```bash
# From the repo root
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Run the server

```bash
cd backend
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Open `http://localhost:8000/docs` for the interactive Swagger UI.

### Environment variables

| Variable       | Default                  | Description                                  |
|----------------|--------------------------|----------------------------------------------|
| `DATABASE_URL` | `sqlite:///recipes.db`   | Database connection string (Turso URL in prod)|

### API overview

| Resource       | Endpoints                                          |
|----------------|----------------------------------------------------|
| Health         | `GET /health`                                      |
| Ingredients    | `GET/POST /ingredients`, `GET/PUT/DELETE /ingredients/{id}` |
| Recipes        | `GET/POST /recipes`, `GET/PUT/DELETE /recipes/{id}` |
| Schedule       | `GET/POST /schedule`, `DELETE /schedule/{id}` *(Phase 2)* |
| Shopping List  | `GET /shopping-list` *(Phase 2)*                   |
