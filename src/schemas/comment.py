from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
import datetime

from src.schemas.user import UserFromDB


class CommentCreate(BaseModel):
    text: str = Field(..., min_length=1)
    rating: int = Field(..., ge=1, le=5)
    reply_to: Optional[int] = None

class CommentUpdate(BaseModel):
    text: Optional[str] = Field(None, min_length=1)
    rating: Optional[int] = Field(None, ge=1, le=5)

class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    rating: int
    author: UserFromDB
    reply_to: Optional[int]
    created_at: datetime.datetime

class DeletedComment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str = "Комментарий удалён"
    rating: int = 0
    reply_to: Optional[int]
