import re
from typing import List, Union

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.mysql import get_db
from models.error import BusinessException
from models.response import ResponseModel
from models.user import UserSignUp
from services.diet import parse_preferences
from services.user_service import UserService
from utils.auth_token import TokenUtils
from utils.date_convert import calculate_age, is_valid_birthday

router = APIRouter()
user_service = UserService()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 6


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UpdateProfileRequest(BaseModel):
    nickname: str
    gender: str
    birthday: str  # YYYY-MM-DD
    email: str
    food_preferences: Union[str, List[str]] = ""


class SignUpUserInfo(BaseModel):
    username: str
    nickname: str
    email: str
    password: str
    gender: str
    birthday: str  # YYYY-MM-DD
    food_preferences: List[str] = []


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserCollectRecipe(BaseModel):
    recipe_id: int
    is_collect: bool


def _validate_profile_fields(nickname: str, email: str, gender: str, birthday: str):
    if len(nickname.strip()) < 2:
        raise BusinessException(1000, "Name must be at least 2 characters")
    if not _EMAIL_RE.match(email.strip()):
        raise BusinessException(1004, "Please enter a valid email address")
    if not gender.strip():
        raise BusinessException(1000, "Gender is required")
    if not is_valid_birthday(birthday):
        raise BusinessException(1011, "Birthday must be a valid date (YYYY-MM-DD)")


def _current_user(request: Request, db: Session):
    user = user_service.get_user(db, request.state.user.get("user_id"))
    if not user:
        raise BusinessException(1002)
    return user


@router.post("/login", response_model=ResponseModel)
def auth_login(request: UserLoginRequest, db: Session = Depends(get_db)):
    user = user_service.user_login(db, request.username.strip(), request.password)
    if not user:
        return ResponseModel.common_error(message="Invalid username or password")
    return ResponseModel.success_with_data(data={
        "access_token": TokenUtils.create_user_token(user.id, user.username),
        "token_type": "bearer",
    })


@router.get("/me", response_model=ResponseModel)
def read_users_me(request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    recipe_count, ingredient_count = user_service.count_user_recipesAndIngredients(db, user.id)
    return ResponseModel.success_with_data(data={
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "gender": user.gender,
        "birthday": user.birthday or "",
        "age": calculate_age(user.birthday),
        "user_recipe_count": recipe_count,
        "user_ingredient_count": ingredient_count,
        "user_collect_recipe_count": user_service.count_user_collect_recipes(db, user.id),
        "food_preferences": ",".join(parse_preferences(user.food_preferences)),
    })


@router.post("/signup", response_model=ResponseModel)
def signup(user_info: SignUpUserInfo, db: Session = Depends(get_db)):
    if len(user_info.username.strip()) < 3:
        raise BusinessException(1000, "Username must be at least 3 characters")
    if len(user_info.password) < MIN_PASSWORD_LENGTH:
        raise BusinessException(1003, f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    _validate_profile_fields(user_info.nickname, user_info.email, user_info.gender,
                             user_info.birthday)
    error = user_service.sign_up(db, UserSignUp(
        username=user_info.username.strip(),
        nickname=user_info.nickname.strip(),
        email=user_info.email.strip(),
        password=user_info.password,
        gender=user_info.gender.strip(),
        birthday=user_info.birthday.strip(),
        food_preferences=parse_preferences(user_info.food_preferences),
    ))
    if error:
        return ResponseModel.common_error(message=error)
    return ResponseModel.success_no_data()


@router.post("/updateProfile", response_model=ResponseModel)
def update_profile(request: Request, profile: UpdateProfileRequest,
                   db: Session = Depends(get_db)):
    user = _current_user(request, db)
    _validate_profile_fields(profile.nickname, profile.email, profile.gender, profile.birthday)
    error = user_service.update_user(
        db,
        user_id=user.id,
        nickname=profile.nickname.strip(),
        email=profile.email.strip(),
        gender=profile.gender.strip(),
        birthday=profile.birthday.strip(),
        food_preferences=",".join(parse_preferences(profile.food_preferences)),
    )
    if error:
        return ResponseModel.common_error(message=error)
    return ResponseModel.success_no_data()


@router.post("/changePassword", response_model=ResponseModel)
def change_password(request: Request, payload: ChangePasswordRequest,
                    db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if len(payload.new_password) < MIN_PASSWORD_LENGTH:
        raise BusinessException(1003, f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    error = user_service.change_password(db, user.id, payload.current_password,
                                         payload.new_password)
    if error:
        return ResponseModel.common_error(message=error)
    return ResponseModel.success_no_data()


@router.post("/collectRecipe", response_model=ResponseModel)
def collect_recipe(request: Request, payload: UserCollectRecipe, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    user_service.collect_or_cancelCollect_recipe(
        db, user_id=user.id, recipe_id=payload.recipe_id, is_collect=payload.is_collect)
    return ResponseModel.success_no_data()
