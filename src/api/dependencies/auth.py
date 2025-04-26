from typing import Annotated, Optional
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from src.core import settings,token as t
from src.core.constant import FAIL_AUTH_CHECK, FAIL_INVALID_TOKEN
from fastapi import status
from src.schemas.user import UserFromDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token", auto_error=False)

def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)]
)->UserFromDB:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=FAIL_AUTH_CHECK,
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        response = t.get_user_from_token(token, settings.secret_key.get_secret_value())
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = FAIL_INVALID_TOKEN +f"({str(e)})",
        )

def get_current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_scheme)]
) -> Optional[UserFromDB]:
    if not token:
        return None
    try:
        response = t.get_user_from_token(token, settings.secret_key.get_secret_value())
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=FAIL_INVALID_TOKEN + f"({str(e)})",
        )
