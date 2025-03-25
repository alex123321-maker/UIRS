from fastapi import HTTPException,status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import verify_password
from src.models.user import User
from src.schemas.user import UserInCreate, UserBase, UserFromDB


async def create_user(db: AsyncSession, user_in: UserInCreate) -> UserFromDB:
    """Создать нового пользователя с указанной ролью"""
    user = User(
        login=user_in.login,
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
    data_to_update = user_update.model_dump(exclude_unset=True)
    new_login = data_to_update.get("login")
    if new_login:
        stmt = select(User).where(User.login == new_login)
        existing_user = (await db.execute(stmt)).scalar_one_or_none()
        if existing_user and existing_user.id != user_id:
            # Если в БД есть другой пользователь с таким логином, выбрасываем ошибку
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Этот логин уже используется другим пользователем."
            )

    # Если логин свободен или мы его не меняем – обновляем остальные поля
    for key, value in data_to_update.items():
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


