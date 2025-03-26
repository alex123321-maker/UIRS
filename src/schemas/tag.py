from pydantic import BaseModel, Field
from typing import List

tag_pattern = r"^[a-zA-Z0-9_а-яА-Я]+$"

class TagCreate(BaseModel):
    title: str = Field(...,
        examples=["ПодПиво"],
        pattern=tag_pattern,
        description="Название тега (латиница/кириллица, цифры, подчёркивание)."
    )

# Базовая модель для отображения
class TagBase(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True

class TagList(BaseModel):
    tags: List[TagBase]

class PaginatedTagList(TagList):
    results: int = 0
    current_page: int = 0
    total_pages: int = 0
