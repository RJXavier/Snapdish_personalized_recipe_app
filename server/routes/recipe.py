import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import UPLOAD_DIR
from core.mysql import get_db
from models import User
from models.error import BusinessException
from models.response import ResponseModel
from services.detection import DetectionUnavailable, FoodIngredientDetector
from services.diet import parse_preferences
from services.recipe_service import RecipeService
from services.recommend_service import RecipeRecommender

logger = logging.getLogger(__name__)
router = APIRouter()

recipe_service = RecipeService()
detection_ingredient = FoodIngredientDetector()
recipe_recommender = RecipeRecommender()


class RecipeSearchRequest(BaseModel):
    ingredients: List[str]
    page: int = 1
    page_size: int = 5


class DetectionIngredients(BaseModel):
    # file name returned by POST /upload
    ingredients_img: str


class RecommendationIngredients(BaseModel):
    ingredients: List[str] = []


def _user_id(request: Request) -> int:
    return request.state.user.get("user_id")


def _preferences(request: Request, db: Session) -> List[str]:
    """Dietary preferences of the logged-in user."""
    user = db.query(User).filter(User.id == _user_id(request)).first()
    return parse_preferences(user.food_preferences) if user else []


@router.get("/recipeIngredients/{recipe_id}", response_model=ResponseModel)
def get_recipe_ingredients(request: Request, recipe_id: int, db: Session = Depends(get_db)):
    user_id = _user_id(request)
    recipe = recipe_service.get_recipe_ingredients(recipe_id=recipe_id, user_id=user_id, db=db)
    if not recipe:
        raise BusinessException(1013)
    recipe_service.add_recipe_view(user_id=user_id, recipe_id=recipe_id, db=db)
    return ResponseModel.success_with_data(data=recipe)


@router.post("/recipesByIngredients", response_model=ResponseModel)
def get_recipes_by_ingredients(request: Request, recipe_data: RecipeSearchRequest,
                               db: Session = Depends(get_db)):
    recipes = recipe_service.get_recipes_by_ingredients(
        ingredients=recipe_data.ingredients,
        page=recipe_data.page,
        page_size=recipe_data.page_size,
        db=db,
        preferences=_preferences(request, db),
    )
    if recipe_data.page <= 1:
        recipe_service.add_ingredients_view(
            user_id=_user_id(request), ingredients=recipe_data.ingredients, db=db)
    return ResponseModel.success_with_data(data=recipes)


@router.get("/recipesList", response_model=ResponseModel)
def get_recipes_list(request: Request, page: int = 1, page_size: int = 5,
                     db: Session = Depends(get_db)):
    recipes = recipe_service.get_recipes_list(
        page=page, page_size=page_size, db=db, preferences=_preferences(request, db))
    return ResponseModel.success_with_data(data=recipes)


@router.get("/ingredientsCategories", response_model=ResponseModel)
def get_ingredients_categories(db: Session = Depends(get_db)):
    return ResponseModel.success_with_data(data=recipe_service.get_ingredients_categories(db=db))


@router.get("/allIngredientsWithCategories", response_model=ResponseModel)
def get_all_ingredients_with_categories(db: Session = Depends(get_db)):
    return ResponseModel.success_with_data(
        data=recipe_service.get_all_ingredients_with_categories(db=db))


@router.post("/detectionIngredients", response_model=ResponseModel)
def detection_ingredients(payload: DetectionIngredients):
    # Only files inside the upload folder may be analysed
    file_name = Path(payload.ingredients_img.replace("\\", "/")).name
    image_path = (UPLOAD_DIR / file_name).resolve()
    if not file_name or image_path.parent != UPLOAD_DIR.resolve() or not image_path.is_file():
        raise BusinessException(1000, "Image not found, please upload it again")
    try:
        detections = detection_ingredient.detect_image(image_path=image_path)
    except DetectionUnavailable as exc:
        logger.error("Ingredient detection unavailable: %s", exc)
        raise BusinessException(1016)
    finally:
        image_path.unlink(missing_ok=True)
    return ResponseModel.success_with_data(data=detections)


@router.post("/feedRecipe", response_model=ResponseModel)
def feed_recipe(request: Request, payload: RecommendationIngredients,
                db: Session = Depends(get_db)):
    user_id = _user_id(request)
    data = recipe_recommender.get_recommendations(
        user_id=user_id,
        input_ingredients=payload.ingredients,
        db=db,
        preferences=_preferences(request, db),
    )
    recipe_service.add_ingredients_view(user_id=user_id, ingredients=payload.ingredients, db=db)
    return ResponseModel.success_with_data(data={"recipes": data, "total": len(data)})


@router.get("/historyRecipes", response_model=ResponseModel)
def get_history_recipes(request: Request, db: Session = Depends(get_db)):
    return ResponseModel.success_with_data(
        data=recipe_service.get_history_recipes(user_id=_user_id(request), db=db))


@router.get("/collectRecipes", response_model=ResponseModel)
def get_collect_recipes(request: Request, db: Session = Depends(get_db)):
    return ResponseModel.success_with_data(
        data=recipe_service.get_collected_recipes(user_id=_user_id(request), db=db))


@router.get("/historyIngredients", response_model=ResponseModel)
def get_history_ingredients(request: Request, db: Session = Depends(get_db)):
    return ResponseModel.success_with_data(
        data=recipe_service.get_history_ingredients(user_id=_user_id(request), db=db))
