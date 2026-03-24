"""Seed the database with sample ingredients, recipes, and a week schedule."""

import sys
from datetime import date, timedelta

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.models import Ingredient, MealSlot, Recipe, RecipeIngredient, WeekSchedule

# ---------------------------------------------------------------------------
# Ingredients (nutritional values per 100 g)
# ---------------------------------------------------------------------------
INGREDIENTS = [
    {"name": "Chicken Breast", "calories": 165, "protein_g": 31, "fat_g": 3.6, "carbs_g": 0, "fibre_g": 0, "default_unit": "g"},
    {"name": "Basmati Rice", "calories": 350, "protein_g": 7.1, "fat_g": 0.6, "carbs_g": 78, "fibre_g": 0.4, "default_unit": "g"},
    {"name": "Eggs", "calories": 155, "protein_g": 13, "fat_g": 11, "carbs_g": 1.1, "fibre_g": 0, "default_unit": "piece"},
    {"name": "Broccoli", "calories": 34, "protein_g": 2.8, "fat_g": 0.4, "carbs_g": 7, "fibre_g": 2.6, "default_unit": "g"},
    {"name": "Olive Oil", "calories": 884, "protein_g": 0, "fat_g": 100, "carbs_g": 0, "fibre_g": 0, "default_unit": "ml"},
    {"name": "Salmon Fillet", "calories": 208, "protein_g": 20, "fat_g": 13, "carbs_g": 0, "fibre_g": 0, "default_unit": "g"},
    {"name": "Sweet Potato", "calories": 86, "protein_g": 1.6, "fat_g": 0.1, "carbs_g": 20, "fibre_g": 3, "default_unit": "g"},
    {"name": "Spinach", "calories": 23, "protein_g": 2.9, "fat_g": 0.4, "carbs_g": 3.6, "fibre_g": 2.2, "default_unit": "g"},
    {"name": "Oats", "calories": 389, "protein_g": 16.9, "fat_g": 6.9, "carbs_g": 66, "fibre_g": 10.6, "default_unit": "g"},
    {"name": "Banana", "calories": 89, "protein_g": 1.1, "fat_g": 0.3, "carbs_g": 23, "fibre_g": 2.6, "default_unit": "piece"},
]

# ---------------------------------------------------------------------------
# Recipes: (title, description, servings, instructions, ingredients list)
# Each ingredient entry: (ingredient_name, quantity, unit)
# ---------------------------------------------------------------------------
RECIPES = [
    {
        "title": "Grilled Chicken & Rice",
        "description": "Simple grilled chicken breast served with basmati rice and steamed broccoli.",
        "servings": 2,
        "instructions": [
            "Season chicken breasts with salt, pepper, and a drizzle of olive oil.",
            "Grill chicken on medium-high heat for 6-7 minutes per side until cooked through.",
            "Cook basmati rice according to package directions.",
            "Steam broccoli for 4-5 minutes until tender-crisp.",
            "Plate rice, slice chicken on top, and serve broccoli on the side.",
        ],
        "ingredients": [
            ("Chicken Breast", 300, "g"),
            ("Basmati Rice", 200, "g"),
            ("Broccoli", 150, "g"),
            ("Olive Oil", 10, "ml"),
        ],
    },
    {
        "title": "Salmon with Sweet Potato",
        "description": "Pan-seared salmon fillet with roasted sweet potato and sautéed spinach.",
        "servings": 2,
        "instructions": [
            "Preheat oven to 200°C. Cube sweet potatoes, toss with olive oil, and roast for 25 minutes.",
            "Season salmon with salt and pepper.",
            "Heat olive oil in a pan over medium-high heat. Sear salmon skin-side down for 4 minutes, flip, cook 3 more minutes.",
            "Sauté spinach in the same pan with a splash of olive oil until wilted.",
            "Serve salmon over sweet potato with spinach on the side.",
        ],
        "ingredients": [
            ("Salmon Fillet", 300, "g"),
            ("Sweet Potato", 400, "g"),
            ("Spinach", 100, "g"),
            ("Olive Oil", 15, "ml"),
        ],
    },
    {
        "title": "Overnight Oats",
        "description": "No-cook breakfast oats with banana — prep the night before.",
        "servings": 1,
        "instructions": [
            "Add oats to a jar or container.",
            "Slice banana and layer on top of oats.",
            "Pour in 200 ml of milk or water, stir to combine.",
            "Refrigerate overnight (at least 6 hours).",
            "Stir and enjoy cold, or microwave for 2 minutes.",
        ],
        "ingredients": [
            ("Oats", 80, "g"),
            ("Banana", 120, "piece"),
        ],
    },
    {
        "title": "Veggie Egg Scramble",
        "description": "Quick scrambled eggs with broccoli and spinach.",
        "servings": 1,
        "instructions": [
            "Heat olive oil in a non-stick pan over medium heat.",
            "Add chopped broccoli and cook for 3 minutes.",
            "Add spinach and cook until wilted, about 1 minute.",
            "Crack eggs into the pan, scramble with vegetables until set.",
            "Season with salt and pepper, serve immediately.",
        ],
        "ingredients": [
            ("Eggs", 150, "piece"),
            ("Broccoli", 80, "g"),
            ("Spinach", 50, "g"),
            ("Olive Oil", 5, "ml"),
        ],
    },
]

# ---------------------------------------------------------------------------
# Week schedule: (recipe_title, date_offset_from_monday, meal_slot)
# ---------------------------------------------------------------------------
def _get_schedule_entries(monday: date) -> list[tuple[str, date, MealSlot, int]]:
    """Return (recipe_title, date, meal_slot, servings) tuples for a sample week."""
    return [
        ("Overnight Oats", monday, MealSlot.breakfast, 1),
        ("Grilled Chicken & Rice", monday, MealSlot.lunch, 2),
        ("Salmon with Sweet Potato", monday, MealSlot.dinner, 2),
        ("Veggie Egg Scramble", monday + timedelta(days=1), MealSlot.breakfast, 1),
        ("Grilled Chicken & Rice", monday + timedelta(days=1), MealSlot.lunch, 2),
        ("Overnight Oats", monday + timedelta(days=2), MealSlot.breakfast, 1),
        ("Salmon with Sweet Potato", monday + timedelta(days=2), MealSlot.dinner, 2),
        ("Veggie Egg Scramble", monday + timedelta(days=3), MealSlot.breakfast, 1),
        ("Grilled Chicken & Rice", monday + timedelta(days=4), MealSlot.lunch, 2),
    ]


def seed():
    create_db_and_tables()

    with Session(engine) as session:
        # Check if already seeded
        existing = session.exec(select(Ingredient)).first()
        if existing:
            print("Database already has data — skipping seed.")
            return

        # Insert ingredients
        name_to_ingredient: dict[str, Ingredient] = {}
        for data in INGREDIENTS:
            ing = Ingredient(**data)
            session.add(ing)
            name_to_ingredient[data["name"]] = ing
        session.flush()
        print(f"Inserted {len(INGREDIENTS)} ingredients.")

        # Insert recipes
        name_to_recipe: dict[str, Recipe] = {}
        for data in RECIPES:
            recipe = Recipe(
                title=data["title"],
                description=data["description"],
                servings=data["servings"],
                instructions=data["instructions"],
            )
            session.add(recipe)
            session.flush()

            for ing_name, qty, unit in data["ingredients"]:
                link = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=name_to_ingredient[ing_name].id,
                    quantity=qty,
                    unit=unit,
                )
                session.add(link)

            name_to_recipe[data["title"]] = recipe
        session.flush()
        print(f"Inserted {len(RECIPES)} recipes.")

        # Insert schedule
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        schedule_entries = _get_schedule_entries(monday)

        for title, d, slot, servings in schedule_entries:
            entry = WeekSchedule(
                recipe_id=name_to_recipe[title].id,
                date=d.isoformat(),
                meal_slot=slot,
                servings=servings,
            )
            session.add(entry)
        session.flush()
        print(f"Inserted {len(schedule_entries)} schedule entries for week of {monday}.")

        session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    seed()
