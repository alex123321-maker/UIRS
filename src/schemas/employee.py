from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from src.core.constant import SUCCESS_DELETE_EMPLOYEE, SUCCESS_DELETE_PHOTO


class DepartmentInfo(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )
    id: int
    name: str = Field(...,description='Название отдела')

class PhotoInfo(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )
    id: int
    path: str = Field(...,description='Ссылка на фото')

class PositionInfo(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )
    id: int
    name: str = Field(..., description='Название должности')


class EmployeeBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    name: str = Field(...,description='Имя сотрудника', example='Иван')
    surname: str = Field(...,description='Фамилия сотрудника', example='Иванов')
    patronymic: str | None = Field(...,description='Отчество сотрудника', example='Иванович')

class EmployeeCreate(EmployeeBase):
    department: str = Field(...,description="Название отдела")
    position: str = Field(...,description="Название должности")


class EmployeeInfo(EmployeeBase):
    id: int =Field(...,description='Идентификатор сотрудника')
    department: DepartmentInfo= Field(...,description='Отдел сотрудника')
    position: PositionInfo = Field(...,description='Должность сотрудника')

class EmployeeInfoPhoto(EmployeeInfo):
    photos: List[PhotoInfo] = Field(..., description="Фотографии сотрудника")

class EmployeeUpdate(BaseModel):
    name: str | None = Field(None, description="Имя сотрудника")
    surname: str | None = Field(None, description="Фамилия сотрудника")
    patronymic: str | None = Field(None, description="Отчество сотрудника")
    department: str | None = Field(None, description="Название отдела")
    position: str | None = Field(None, description="Название должности")

class EmployeeDeleteResponse(BaseModel):
    message: str = Field(..., example=SUCCESS_DELETE_EMPLOYEE)

class PhotoDeleteResponse(BaseModel):
    message: str = Field(..., example=SUCCESS_DELETE_PHOTO)


class PaginatedEmployeeResponse(BaseModel):
    total: int = Field(..., description="Общее количество сотрудников")
    employees: List[EmployeeInfo] = Field(..., description="Список сотрудников")
