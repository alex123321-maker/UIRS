from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.api.dependencies.database import get_session
from src.core import settings
from src.core.constant import FAIL_AUTH_VALIDATION_CREDENTIAL
from src.core.token import create_token_for_user
from src.schemas.user import UserTokenData, UserInSignIn, UserBase, UserFromDB
from src.services.auth import authenticate_user

router = APIRouter()



from fastapi.security import OAuth2PasswordRequestForm

@router.post("/token", response_model=UserTokenData, status_code=200)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_session)
):
    user: UserBase = await authenticate_user(db, UserInSignIn(login=form_data.username, password=form_data.password))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=FAIL_AUTH_VALIDATION_CREDENTIAL
        )

    token = create_token_for_user(user, settings.secret_key.get_secret_value())
    return token


