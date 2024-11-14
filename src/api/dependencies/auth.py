from typing import Annotated

from anyio import get_current_task
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from src.core import settings,token as t

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token")

def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)]
):
    return t.get_user_from_token(token,settings.secret_key.get_secret_value())
