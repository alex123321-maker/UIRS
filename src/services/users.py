from enum import Enum
from typing import List, Tuple
from enum import Enum

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import verify_password
from src.models.user import User
from src.schemas.user import UserInCreate, UserBase, UserFromDB, RoleEnum


async def get_users(
        db: AsyncSession,
        role: RoleEnum | None,
        login: str | None,
        limit: int = 10,
        offset: int = 0
) -> Tuple[int, List[UserFromDB]]:
    """Получить пользователей с фильтрацией, сортировкой и пагинацией"""
    query = select(User)

    # Фильтрация
    if role:
        query = query.where(User.role == role)
    if login:
        query = query.where(User.login.ilike(f"%{login}%"))

    # Получение общего количества записей
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Применение пагинации
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    users = result.scalars().all()

    return total, [UserFromDB.model_validate(user) for user in users]


async def create_user(db: AsyncSession, user_in: UserInCreate) -> UserFromDB:
    """Создать нового пользователя с указанной ролью"""
    user = User(
        login=user_in.login,
        role=user_in.role,
    )
    user.change_password(user_in.password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserFromDB.model_validate(user)

async def get_user_by_id(db: AsyncSession, user_id: int) -> UserFromDB | None:
    """Получить пользователя по id"""
    user = await db.get(User, user_id)
    if not user:
        return None
    return UserFromDB.model_validate(user)


async def update_user_service(db: AsyncSession, user_id: int, user_update: UserBase) -> UserFromDB | None:
    """
    Обновить данные пользователя.
    """
    user = await db.get(User, user_id)
    if user is None:
        return None

    for key, value in user_update.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return UserFromDB.model_validate(user)


async def delete_user_service(db: AsyncSession, user_id: int) -> bool | None:
    """
    Удалить пользователя по id.
    """
    user = await db.get(User, user_id)
    if user is None:
        return None

    await db.delete(user)
    await db.commit()
    return True

async def change_user_password(
    db: AsyncSession,
    user_id: int,
    current_password: str,
    new_password: str
) -> bool:
    """
    Изменяет пароль пользователя, если текущий пароль указан корректно.

    :param db: Асинхронная сессия базы данных.
    :param user_id: Идентификатор пользователя.
    :param current_password: Текущий пароль.
    :param new_password: Новый пароль.
    :return: True, если пароль успешно изменен, иначе False.
    """
    try:
        user: User | None = await db.get(User, user_id)
        if not user:
            return False

        # Проверяем текущий пароль
        if not verify_password(user.salt + current_password, user.hashed_password):
            return False

        # Обновляем пароль
        user.change_password(new_password)
        await db.commit()
        await db.refresh(user)

        return True
    except SQLAlchemyError as e:
        # Логирование ошибок
        print(f"Database error: {e}")
        return False


