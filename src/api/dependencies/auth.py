from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from src.core import settings,token as t
from src.core.constant import FAIL_AUTH_CHECK

from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status
from typing import Optional




oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token", auto_error=False)

def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)]
):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=FAIL_AUTH_CHECK,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return t.get_user_from_token(token, settings.secret_key.get_secret_value())
