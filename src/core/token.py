from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from pydantic import ValidationError

from src.schemas.auth import TokenBase
from src.schemas.user import UserTokenData, UserFromDB

TOKEN_TYPE = "bearer"
JWT_SUBJECT = "access"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 12*60


def create_token(
    *,
    content: dict[str, str],
    secret_key: str,
    expires_delta: timedelta | None = timedelta(minutes=15),
):
    to_encode = content.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode.update(TokenBase(exp=expire, sub=JWT_SUBJECT).model_dump())

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_token_for_user(user: UserFromDB, secret_key: str) -> UserTokenData:
    token_user_dict = user.model_dump()
    created_token = create_token(
        content=token_user_dict,
        secret_key=secret_key,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return UserTokenData(access_token=created_token, token_type=TOKEN_TYPE)


def get_user_from_token(token: str, secret_key: str) -> UserFromDB:
    try:
        decoded_user = jwt.decode(token, secret_key, algorithms=ALGORITHM)
        return UserFromDB(**decoded_user)

    except JWTError as decode_error:
        raise ValueError("unable to decode") from decode_error
    except ValidationError as validation_error:
        raise ValueError("invalid token") from validation_error