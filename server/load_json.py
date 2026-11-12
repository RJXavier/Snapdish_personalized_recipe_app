"""Create the database tables and load the recipe dataset.

    python load_json.py            # seed an empty database
    python load_json.py --reset    # wipe recipe data and seed again

Works with whichever database DATABASE_URL points to (SQLite by default).
User accounts are never touched, except that a demo account is created when
there are no users at all.
"""
import argparse
import json
import re
from pathlib import Path

from core.mysql import SessionLocal
from models import (Ingredients, IngredientsCategory, RecipeIngredients, Recipes, User,
                    UserCollectRecipe, UserIngredients, UserRecipe)
from services.recipe_service import encode_steps
from utils.password import hash_password

DATA_FILE = Path(__file__).resolve().parent / "fridge_recipes.recipes.json"

CATEGORIES = {1: "Meat", 2: "Seafood", 3: "Vegetables", 4: "Protein", 5: "Grains", 6: "Fats"}

# name -> (id, category id). These are the ingredients the YOLO model detects
# and the ones users can pick on the "Select ingredients" screen.
BASE_INGREDIENTS = {
    "beef": (1, 1),
    "butter": (2, 6),
    "capsicum": (3, 3),
    "carrot": (4, 3),
    "chicken breast": (5, 1),
    "egg": (6, 4),
    "onion": (7, 3),
    "potatoes": (8, 3),
    "shrimp": (9, 2),
    "tofu": (10, 4),
    "tomatoes": (11, 3),
    "rice": (12, 5),
}

DEMO_USER = {"username": "demo", "password": "demo1234"}


def _singular(word: str) -> str:
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokens(name: str):
    return [_singular(t) for t in re.split(r"[^a-z]+", name.lower()) if t]


_BASE_TOKENS = {name: _tokens(name) for name in BASE_INGREDIENTS}
_BASE_ALIASES = {"bell pepper": "capsicum", "prawn": "shrimp"}


def match_base_ingredient(name: str):
    """Map e.g. 'ground beef' or 'cherry tomatoes' to a base ingredient.

    Only matches when the name *ends with* the base ingredient, so
    'eggplant', 'rice vinegar' or 'beef broth' are left alone.
    """
    tokens = _tokens(name)
    for alias, base in _BASE_ALIASES.items():
        alias_tokens = _tokens(alias)
        if tokens[-len(alias_tokens):] == alias_tokens:
            return base
    for base, base_tokens in _BASE_TOKENS.items():
        if tokens[-len(base_tokens):] == base_tokens:
            return base
    return None


def reset_recipe_data(db):
    for model in (UserCollectRecipe, UserRecipe, UserIngredients, RecipeIngredients,
                  Recipes, Ingredients, IngredientsCategory):
        db.query(model).delete()
    db.commit()


def seed(db) -> int:
    recipes = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    for category_id, name in CATEGORIES.items():
        db.add(IngredientsCategory(id=category_id, name=name))
    ingredient_ids = {}
    for name, (ingredient_id, category_id) in BASE_INGREDIENTS.items():
        db.add(Ingredients(id=ingredient_id, ingredient_name=name, unit_need_space=2,
                           category_id=category_id))
        ingredient_ids[name] = ingredient_id
    db.flush()

    seen_titles = set()
    for recipe in recipes:
        title = str(recipe["title"]).strip()[:100]
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        steps = recipe.get("steps") or []
        if isinstance(steps, str):
            steps = [steps]
        recipe_obj = Recipes(
            recipe_name=title,
            difficulty="easy",
            cook_time=f"{recipe.get('prep_time_min') or 0} min",
            cook_steps=encode_steps(steps),
        )
        db.add(recipe_obj)
        db.flush()

        used = set()
        for raw_name in recipe.get("normalized_ingredients") or []:
            name = str(raw_name).strip().lower()[:100]
            if not name:
                continue
            name = match_base_ingredient(name) or name
            if name not in ingredient_ids:
                ingredient = Ingredients(ingredient_name=name, unit_need_space=2, category_id=0)
                db.add(ingredient)
                db.flush()
                ingredient_ids[name] = ingredient.id
            if ingredient_ids[name] in used:
                continue
            used.add(ingredient_ids[name])
            db.add(RecipeIngredients(recipe_id=recipe_obj.id,
                                     ingredient_id=ingredient_ids[name], quantity=0))
    db.commit()
    return len(seen_titles)


def ensure_demo_user(db) -> bool:
    if db.query(User).count() > 0:
        return False
    db.add(User(
        username=DEMO_USER["username"],
        nickname="Demo User",
        email="demo@example.com",
        gender="Prefer not to say",
        password=hash_password(DEMO_USER["password"]),
        birthday="1998-05-17",
        food_preferences="No Shrimp",
    ))
    db.commit()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true",
                        help="delete existing recipes, ingredients and user history first")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.reset:
            reset_recipe_data(db)
        if db.query(Recipes).count() > 0:
            print("Recipes already loaded. Use --reset to load them again.")
        else:
            print(f"Loaded {seed(db)} recipes.")
        if ensure_demo_user(db):
            print(f"Created demo account: {DEMO_USER['username']} / {DEMO_USER['password']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
