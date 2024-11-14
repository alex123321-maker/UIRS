from enum import nonmember

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.schemas.user import UserBase, UserInSignIn, UserInDB, UserFromDB
from src.core import security


async def _get_user_by_login(db: AsyncSession, login: str) -> User | None:
    """Получить пользователя по логину из базы данных"""
    result = await db.execute(select(User).filter(User.login == login))
    user = result.scalars().first()
    return user

async def get_user_by_login(db: AsyncSession, login: str) -> UserFromDB | None:
    """Получить пользователя по логину из базы данных"""
    return UserFromDB.model_validate(_get_user_by_login(db,login))

async def authenticate_user(db: AsyncSession, user_in: UserInSignIn) -> UserFromDB | None:
    """Аутентифицирует пользователя по логину и паролю"""
    user: User = await _get_user_by_login(db, user_in.login)
    if user is None:
        return None

    # Проверяем пароль пользователя
    if user.check_password(user_in.password):
        return UserFromDB.model_validate(user)
    else:
        return None


