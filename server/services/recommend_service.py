from collections import Counter
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models import Recipes, UserCollectRecipe, UserIngredients, UserRecipe
from services.diet import is_allowed
from services.recipe_service import _normalise, _with_ingredients, ingredient_names, recipe_summary

# Weights of the three content-based signals (sum to 1.0)
INPUT_WEIGHT = 0.6        # ingredients the user selected / photographed
PREFERENCE_WEIGHT = 0.3   # ingredients common in the user's saved recipes
HISTORY_WEIGHT = 0.1      # recipes viewed and ingredients searched before

MAX_PREFERENCE_INGREDIENTS = 10
DEFAULT_TOP_N = 20


class RecipeRecommender:
    """Content-based recipe recommender.

    Every candidate recipe is described by its set of ingredients and scored
    against a user profile built from the current request and past behaviour.
    Recipes that break the user's dietary preferences are never recommended.
    """

    def _preference_ingredients(self, user_id: int, db: Session) -> List[str]:
        """Most frequent ingredients across the user's saved recipes."""
        saved_ids = [
            row.recipe_id
            for row in db.query(UserCollectRecipe)
            .filter(UserCollectRecipe.user_id == user_id, UserCollectRecipe.is_collect == 1)
            .all()
        ]
        if not saved_ids:
            return []
        counter: Counter = Counter()
        for recipe in _with_ingredients(db.query(Recipes).filter(Recipes.id.in_(saved_ids))).all():
            counter.update(n.lower() for n in ingredient_names(recipe))
        return [name for name, _ in counter.most_common(MAX_PREFERENCE_INGREDIENTS)]

    @staticmethod
    def _overlap(recipe_set: set, wanted: set) -> float:
        return len(recipe_set & wanted) / len(wanted) if wanted else 0.0

    def get_recommendations(
        self,
        user_id: int,
        input_ingredients: List[str],
        db: Session,
        preferences: Optional[List[str]] = None,
        top_n: int = DEFAULT_TOP_N,
    ) -> List[Dict[str, Any]]:
        input_set = set(_normalise(input_ingredients))
        preference_set = set(self._preference_ingredients(user_id, db))

        view_counts = {
            row.recipe_id: row.count
            for row in db.query(UserRecipe).filter(UserRecipe.user_id == user_id).all()
        }
        searched = {
            row.ingredient_name.lower(): row.count
            for row in db.query(UserIngredients).filter(UserIngredients.user_id == user_id).all()
        }
        max_views = max(view_counts.values(), default=0)
        searched_total = sum(searched.values())

        recipes = _with_ingredients(db.query(Recipes).order_by(Recipes.id)).all()
        has_profile = bool(input_set or preference_set or view_counts or searched)
        # Best score this user could reach, so match_ratio is always on a 0..1 scale
        max_score = (
            (INPUT_WEIGHT if input_set else 0.0)
            + (PREFERENCE_WEIGHT if preference_set else 0.0)
            + (HISTORY_WEIGHT if (view_counts or searched) else 0.0)
        )

        results = []
        for recipe in recipes:
            names = ingredient_names(recipe)
            if preferences and not is_allowed(names, preferences):
                continue
            recipe_set = {n.lower() for n in names}

            input_score = self._overlap(recipe_set, input_set)
            preference_score = self._overlap(recipe_set, preference_set)

            viewed_score = view_counts.get(recipe.id, 0) / max_views if max_views else 0.0
            searched_score = (
                sum(count for name, count in searched.items() if name in recipe_set) / searched_total
                if searched_total else 0.0
            )
            history_score = 0.5 * viewed_score + 0.5 * searched_score

            total = (
                INPUT_WEIGHT * input_score
                + PREFERENCE_WEIGHT * preference_score
                + HISTORY_WEIGHT * history_score
            )
            # When the user picked ingredients, only recommend recipes that use one
            if input_set and input_score == 0:
                continue
            if has_profile and total == 0:
                continue

            summary = recipe_summary(recipe)
            summary.update({
                "match_ratio": round(float(total / max_score), 4) if max_score else 0.0,
                "input_score": round(float(input_score), 4),
                "preference_score": round(float(preference_score), 4),
                "history_score": round(float(history_score), 4),
            })
            results.append(summary)

        # Brand-new users have no signals yet, so everything scores 0 and they
        # simply get the first recipes that fit their diet.
        results.sort(key=lambda r: (-r["match_ratio"], r["recipe_id"]))
        return results[:top_n]
