from site import USER_BASE
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status, Body, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import ForUpdateParameter

from src.api.dependencies.auth import get_current_user
from src.schemas.user import UserInCreate, UserBase, UserFromDB, UserDeleteResponse, RoleEnum, PaginatedResponse
from src.api.dependencies.database import get_session
from src.services.auth import _get_user_by_login
from src.services.users import create_user, get_user_by_id, update_user_service, delete_user_service, get_users
from src.core.constant import FAIL_USER_ALREADY_EXISTS, FAIL_VALIDATION_MATCHED_USER_ID, SUCCESS_DELETE_USER

router = APIRouter()


from typing import List, Optional
from fastapi import Query



@router.get("/", response_model=PaginatedResponse, status_code=status.HTTP_200_OK)
async def get_user_list(
        user_in: Annotated[UserFromDB, Depends(get_current_user)],
        db: AsyncSession = Depends(get_session),
        role: RoleEnum | None = Query(None, description="Фильтр по роли пользователя"),
        login: str | None= Query(None, description="Фильтр по логину пользователя"),
        size: int = Query(10, ge=1, description="Количество пользователей на странице"),
        page: int = Query(1, ge=1, description="Номер страницы")
):
    # Пересчитываем offset
    offset = (page - 1) * size

    # Получаем пользователей с учётом пагинации
    total, users = await get_users(db, role=role, login=login, limit=size, offset=offset)

    return PaginatedResponse(total=total, items=users)



@router.post("/", response_model=UserFromDB, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in:Annotated[UserInCreate,Depends()],
    db: AsyncSession = Depends(get_session)
):
    existing_user = await _get_user_by_login(db, user_in.login)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=FAIL_USER_ALREADY_EXISTS
        )

    user = await create_user(db, user_in)
    return user


@router.patch("/{user_id}", response_model=UserFromDB, status_code=status.HTTP_200_OK)
async def update_user(
        user_id:int,
        user_in: Annotated[UserFromDB, Depends(get_current_user)],
        user_update: UserBase = Form(...),

        db: AsyncSession = Depends(get_session)
):
    existing_user: UserBase | None= await update_user_service(db, user_id,user_update)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=FAIL_VALIDATION_MATCHED_USER_ID
        )

    return existing_user

@router.delete("/{user_id}", response_model=UserDeleteResponse, status_code=status.HTTP_200_OK)
async def delete_user(
        user_id:int,
        user_in: Annotated[UserFromDB, Depends(get_current_user)],
        db: AsyncSession = Depends(get_session)
):
    existing_user: bool | None = await delete_user_service(db, user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=FAIL_VALIDATION_MATCHED_USER_ID
        )

    return UserDeleteResponse(message=SUCCESS_DELETE_USER)

@router.get("/me", response_model=UserFromDB, status_code=status.HTTP_200_OK)
async def get_me(
    user_in:Annotated[UserFromDB,Depends(get_current_user)],
    db: AsyncSession = Depends(get_session)
):
    return user_in
