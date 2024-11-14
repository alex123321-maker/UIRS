from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.schemas.user import UserInCreate, UserBase, UserFromDB
from src.api.dependencies.database import get_session
from src.services.auth import _get_user_by_login
from src.services.users import create_user
from src.core.constant import FAIL_USER_ALREADY_EXISTS

router = APIRouter()

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

@router.get("/me", response_model=UserFromDB, status_code=status.HTTP_200_OK)
async def get_me(
    user_in:Annotated[UserFromDB,Depends(get_current_user)],
    db: AsyncSession = Depends(get_session)
):
    return user_in
