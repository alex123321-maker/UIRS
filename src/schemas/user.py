from pydantic import BaseModel, ConfigDict, constr
from src.core import security
from enum import Enum

class RoleEnum(str, Enum):
    HR = "HR"
    USER = "USER"

class UserBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    login: str
    role: RoleEnum

class UserInDB(UserBase):
    salt: str | None = None
    hashed_password: str | None = None

    def check_password(self, password: str) -> bool:
        return security.verify_password(self.salt + password, self.hashed_password)

    def change_password(self, password: str) -> None:
        self.salt = security.generate_salt()
        self.hashed_password = security.get_password_hash(self.salt + password)

class UserFromDB(UserBase):
    id: int

class UserInSignIn(BaseModel):
    login: str
    password: str

class UserInCreate(BaseModel):
    login: str
    password: str
    role: RoleEnum

class UserTokenData(BaseModel):
    access_token: str | None = None
    token_type: str | None = None

class UserAuthOutData(UserBase):
    token: UserTokenData | None = None
