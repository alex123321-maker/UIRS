from datetime import datetime

from pydantic import BaseModel


class TokenBase(BaseModel):
    exp: datetime
    sub: str


