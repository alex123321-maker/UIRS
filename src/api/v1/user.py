from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Body, Form
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies.auth import get_current_user
from src.schemas.user import UserInCreate, UserBase, UserFromDB, UserDeleteResponse
from src.api.dependencies.database import get_session
from src.services.auth import _get_user_by_login
from src.services.users import create_user, update_user_service, delete_user_service,change_user_password
from src.core.constant import FAIL_USER_ALREADY_EXISTS, SUCCESS_DELETE_USER

router = APIRouter()

@router.post("/sign-up", response_model=UserFromDB, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in:Annotated[UserInCreate,Body()],
    db: AsyncSession = Depends(get_session)
)->UserFromDB:
    existing_user = await _get_user_by_login(db, user_in.login)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=FAIL_USER_ALREADY_EXISTS
        )

    user = await create_user(db, user_in)
    return user



# TODO Удаление доступно только своего аккаунта
@router.delete("/", response_model=UserDeleteResponse, status_code=status.HTTP_200_OK)
async def delete_user(
        user_in: Annotated[UserFromDB, Depends(get_current_user)],
        db: AsyncSession = Depends(get_session)
)->UserDeleteResponse:
    existing_user: bool | None = await delete_user_service(db, user_in.id)
    if existing_user:
        return UserDeleteResponse(message=SUCCESS_DELETE_USER)
    else:
        return UserDeleteResponse(message="Произошла ошибка при удалении пользователя")

@router.patch("/", response_model=UserFromDB, status_code=status.HTTP_200_OK)
async def update_user(
        user_in: Annotated[UserFromDB, Depends(get_current_user)],
        user_update: UserBase = Form(...),

        db: AsyncSession = Depends(get_session)

)->UserBase:

    existing_user: UserBase = await update_user_service(db,user_in.id,user_update)


    return existing_user


@router.get("/", response_model=UserFromDB, status_code=status.HTTP_200_OK)
async def get_me(
    user_in:Annotated[UserFromDB,Depends(get_current_user)],
    db: AsyncSession = Depends(get_session)
)->UserFromDB:
    return user_in


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    current_password: str,
    new_password: str,
    db: AsyncSession = Depends(get_session),
    current_user: UserFromDB = Depends(get_current_user),
)->dict:
    """
    Эндпоинт для смены пароля пользователя.

    :param current_password: Текущий пароль.
    :param new_password: Новый пароль.
    """
    success = await change_user_password(
        db=db,
        user_id=current_user.id,
        current_password=current_password,
        new_password=new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный пароль"
        )

    return {"message": "Пароль успешно изменен"}