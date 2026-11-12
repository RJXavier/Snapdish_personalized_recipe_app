import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import User, UserCollectRecipe, UserIngredients, UserRecipe
from models.user import UserSignUp
from utils.password import hash_password, is_legacy_hash, verify_password

logger = logging.getLogger(__name__)


class UserService:
    def user_login(self, session: Session, username: str, password: str):
        user = session.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, str(user.password)):
            return None
        if is_legacy_hash(str(user.password)):
            # transparently upgrade old MD5 hashes to bcrypt
            user.password = hash_password(password)
            session.commit()
        return user

    def get_user(self, session: Session, user_id: int):
        return session.query(User).filter(User.id == user_id).first()

    def sign_up(self, session: Session, user: UserSignUp) -> Optional[str]:
        """Create the account. Returns an error message, or None on success."""
        if session.query(User).filter(User.username == user.username).first():
            return "Username already exists"
        if session.query(User).filter(User.email == user.email).first():
            return "Email already exists"
        if session.query(User).filter(User.nickname == user.nickname).first():
            return "Nickname already exists"
        session.add(User(
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            birthday=user.birthday,
            password=hash_password(user.password),
            gender=user.gender,
            food_preferences=",".join(user.food_preferences),
        ))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return "Username, nickname or email already exists"
        return None

    def update_user(self, session: Session, user_id: int, nickname: str, email: str,
                    gender: str, birthday: str, food_preferences: str) -> Optional[str]:
        """Update profile fields. Returns an error message, or None on success."""
        user = self.get_user(session, user_id)
        if not user:
            return "User not found"
        if session.query(User).filter(User.nickname == nickname, User.id != user_id).first():
            return "Nickname already exists"
        if session.query(User).filter(User.email == email, User.id != user_id).first():
            return "Email already exists"
        user.nickname = nickname
        user.email = email
        user.gender = gender
        user.birthday = birthday
        user.food_preferences = food_preferences
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return "Nickname or email already exists"
        return None

    def change_password(self, session: Session, user_id: int, current_password: str,
                        new_password: str) -> Optional[str]:
        user = self.get_user(session, user_id)
        if not user:
            return "User not found"
        if not verify_password(current_password, str(user.password)):
            return "Current password is incorrect"
        user.password = hash_password(new_password)
        session.commit()
        return None

    def collect_or_cancelCollect_recipe(self, session: Session, user_id: int, recipe_id: int,
                                        is_collect: bool) -> bool:
        try:
            row = (
                session.query(UserCollectRecipe)
                .filter(UserCollectRecipe.user_id == user_id,
                        UserCollectRecipe.recipe_id == recipe_id)
                .first()
            )
            if row:
                row.is_collect = 1 if is_collect else 0
            elif is_collect:
                session.add(UserCollectRecipe(user_id=user_id, recipe_id=recipe_id, is_collect=1))
            else:
                return False
            session.commit()
            return True
        except Exception:
            logger.exception("Failed to update saved recipe")
            session.rollback()
            return False

    def count_user_recipesAndIngredients(self, session: Session, user_id: int):
        recipes = (session.query(func.sum(UserRecipe.count))
                   .filter(UserRecipe.user_id == user_id).scalar())
        ingredients = (session.query(func.sum(UserIngredients.count))
                       .filter(UserIngredients.user_id == user_id).scalar())
        return int(recipes or 0), int(ingredients or 0)

    def count_user_collect_recipes(self, session: Session, user_id: int) -> int:
        count = (session.query(func.count(UserCollectRecipe.id))
                 .filter(UserCollectRecipe.user_id == user_id,
                         UserCollectRecipe.is_collect == 1).scalar())
        return int(count or 0)
