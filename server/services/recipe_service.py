import json
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from models import RecipeIngredients, UserCollectRecipe, UserIngredients, UserRecipe
from models.ingredients import Ingredients
from models.ingredients_categories import IngredientsCategory
from models.recipes import Recipes
from services.diet import is_allowed


class RecipeIngredientsVO(BaseModel):
    """Recipe detail value object"""
    recipe_id: int
    recipe_name: str
    difficulty: str
    cook_time: str
    cook_steps: List[str]
    ingredients: List[str]
    is_collected: bool = False


def encode_steps(steps: Iterable[str]) -> str:
    """Steps are stored as a JSON array so commas inside a step are preserved."""
    return json.dumps([str(s).strip() for s in steps if str(s).strip()], ensure_ascii=False)


def decode_steps(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("["):
        try:
            return [str(s) for s in json.loads(text)]
        except ValueError:
            pass
    # legacy rows: steps joined with ','
    return [s.strip() for s in text.split(",") if s.strip()]


def _with_ingredients(query):
    return query.options(
        selectinload(Recipes.ingredient_associations).selectinload(RecipeIngredients.ingredient)
    )


def ingredient_names(recipe: Recipes) -> List[str]:
    return [a.ingredient.ingredient_name for a in recipe.ingredient_associations if a.ingredient]


def recipe_summary(recipe: Recipes) -> Dict[str, Any]:
    return {
        "recipe_id": recipe.id,
        "recipe_name": recipe.recipe_name,
        "difficulty": recipe.difficulty,
        "cook_time": recipe.cook_time,
        "ingredients": [
            {
                "ingredient_name": a.ingredient.ingredient_name,
                "quantity": a.quantity,
                "unit": a.ingredient.ingredient_unit or "",
            }
            for a in recipe.ingredient_associations
            if a.ingredient
        ],
    }


def _normalise(names: Iterable[str]) -> List[str]:
    seen, result = set(), []
    for name in names or []:
        key = str(name).strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(key)
    return result


class RecipeService:
    def get_all_ingredients_with_categories(self, db: Session):
        rows = (
            db.query(
                Ingredients.id,
                Ingredients.ingredient_name,
                IngredientsCategory.name.label("category_name"),
            )
            .join(IngredientsCategory, Ingredients.category_id == IngredientsCategory.id)
            .filter(Ingredients.category_id != 0)
            .order_by(IngredientsCategory.id, Ingredients.ingredient_name)
            .all()
        )
        return [
            {
                "id": row.id,
                "ingredient_name": row.ingredient_name,
                "category_name": (row.category_name or "").strip(),
            }
            for row in rows
        ]

    def get_ingredients_categories(self, db: Session):
        categories = db.query(IngredientsCategory).order_by(IngredientsCategory.id).all()
        return [{"id": c.id, "name": (c.name or "").strip()} for c in categories]

    def get_history_ingredients(self, user_id: int, db: Session):
        rows = (
            db.query(UserIngredients)
            .filter(UserIngredients.user_id == user_id)
            .order_by(UserIngredients.count.desc())
            .all()
        )
        return [{"ingredient_name": r.ingredient_name, "count": r.count} for r in rows]

    def _recipes_in_order(self, recipe_ids: List[int], db: Session) -> List[Dict[str, Any]]:
        if not recipe_ids:
            return []
        recipes = _with_ingredients(db.query(Recipes).filter(Recipes.id.in_(recipe_ids))).all()
        by_id = {r.id: r for r in recipes}
        return [recipe_summary(by_id[rid]) for rid in recipe_ids if rid in by_id]

    def get_history_recipes(self, user_id: int, db: Session):
        """Recipes the user opened, most viewed first."""
        ids = [
            row.recipe_id
            for row in db.query(UserRecipe)
            .filter(UserRecipe.user_id == user_id)
            .order_by(UserRecipe.count.desc(), UserRecipe.id.desc())
            .all()
        ]
        return self._recipes_in_order(list(dict.fromkeys(ids)), db)

    def get_collected_recipes(self, user_id: int, db: Session):
        """Recipes the user saved, newest first."""
        ids = [
            row.recipe_id
            for row in db.query(UserCollectRecipe)
            .filter(UserCollectRecipe.user_id == user_id, UserCollectRecipe.is_collect == 1)
            .order_by(UserCollectRecipe.id.desc())
            .all()
        ]
        return self._recipes_in_order(list(dict.fromkeys(ids)), db)

    def get_recipe_ingredients(self, recipe_id: int, user_id: int, db: Session):
        recipe = _with_ingredients(db.query(Recipes).filter(Recipes.id == recipe_id)).first()
        if not recipe:
            return None
        ingredients = []
        for association in recipe.ingredient_associations:
            ingredient = association.ingredient
            if not ingredient:
                continue
            if not association.quantity:
                text = ingredient.ingredient_name
            else:
                text = f"{association.quantity}"
                if ingredient.ingredient_unit:
                    separator = " " if ingredient.unit_need_space == 1 else ""
                    text += f"{separator}{ingredient.ingredient_unit}"
                text += f" {ingredient.ingredient_name}"
            ingredients.append(text)
        return RecipeIngredientsVO(
            recipe_id=recipe_id,
            recipe_name=str(recipe.recipe_name),
            difficulty=str(recipe.difficulty),
            cook_time=str(recipe.cook_time),
            cook_steps=decode_steps(recipe.cook_steps),
            ingredients=ingredients,
            is_collected=self.get_is_collected(user_id=user_id, recipe_id=recipe_id, db=db),
        )

    def get_is_collected(self, user_id: int, recipe_id: int, db: Session) -> bool:
        row = (
            db.query(UserCollectRecipe)
            .filter(UserCollectRecipe.user_id == user_id, UserCollectRecipe.recipe_id == recipe_id)
            .first()
        )
        return bool(row and row.is_collect == 1)

    def get_recipes_list(
        self, page: int, page_size: int, db: Session, preferences: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """All recipes that respect the user's dietary preferences, paginated."""
        page, page_size = max(page, 1), min(max(page_size, 1), 50)
        recipes = _with_ingredients(db.query(Recipes).order_by(Recipes.id)).all()
        if preferences:
            recipes = [r for r in recipes if is_allowed(ingredient_names(r), preferences)]
        start = (page - 1) * page_size
        return {
            "recipes": [recipe_summary(r) for r in recipes[start:start + page_size]],
            "total": len(recipes),
            "page": page,
            "page_size": page_size,
        }

    def get_recipes_by_ingredients(
        self,
        ingredients: List[str],
        page: int,
        page_size: int,
        db: Session,
        preferences: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Recipes containing at least one of the given ingredients, best match first.

        match_ratio is the share of the requested ingredients that the recipe uses.
        """
        page, page_size = max(page, 1), min(max(page_size, 1), 50)
        wanted = _normalise(ingredients)
        empty = {"recipes": [], "total": 0, "page": page, "page_size": page_size}
        if not wanted:
            return empty

        matching_ids = (
            db.query(RecipeIngredients.recipe_id)
            .join(Ingredients, RecipeIngredients.ingredient_id == Ingredients.id)
            .filter(Ingredients.ingredient_name.in_(wanted))
            .distinct()
        )
        recipes = _with_ingredients(db.query(Recipes).filter(Recipes.id.in_(matching_ids))).all()

        wanted_set = set(wanted)
        scored = []
        for recipe in recipes:
            names = ingredient_names(recipe)
            if preferences and not is_allowed(names, preferences):
                continue
            matched = wanted_set.intersection(n.lower() for n in names)
            if not matched:
                continue
            summary = recipe_summary(recipe)
            summary["match_ratio"] = round(len(matched) / len(wanted_set), 4)
            scored.append((len(matched), -len(names), -recipe.id, summary))

        scored.sort(key=lambda item: item[:3], reverse=True)
        start = (page - 1) * page_size
        return {
            "recipes": [item[3] for item in scored[start:start + page_size]],
            "total": len(scored),
            "page": page,
            "page_size": page_size,
        }

    def add_recipe_view(self, user_id: int, recipe_id: int, db: Session):
        row = (
            db.query(UserRecipe)
            .filter(UserRecipe.user_id == user_id, UserRecipe.recipe_id == recipe_id)
            .first()
        )
        if row:
            row.count += 1
        else:
            db.add(UserRecipe(user_id=user_id, recipe_id=recipe_id, count=1))
        db.commit()

    def add_ingredients_view(self, user_id: int, ingredients: List[str], db: Session):
        wanted = _normalise(ingredients)
        if not wanted:
            return
        known = {
            i.ingredient_name.lower(): i
            for i in db.query(Ingredients).filter(Ingredients.ingredient_name.in_(wanted)).all()
        }
        existing = {
            r.ingredient_id: r
            for r in db.query(UserIngredients).filter(UserIngredients.user_id == user_id).all()
        }
        for name in wanted:
            ingredient = known.get(name)
            if not ingredient:
                continue
            row = existing.get(ingredient.id)
            if row:
                row.count += 1
            else:
                db.add(UserIngredients(
                    user_id=user_id,
                    ingredient_id=ingredient.id,
                    ingredient_name=ingredient.ingredient_name,
                    count=1,
                ))
        db.commit()
