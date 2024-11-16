from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.schemas.user import UserInCreate, UserBase, UserFromDB


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
