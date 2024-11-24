import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator, field_serializer
from pydantic_core.core_schema import SerializationInfo, ValidationInfo

from src.core.constant import SUCCESS_DELETE_EVENT
from src.schemas.employee import EmployeeInfoPhoto



class EventBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        datetime_format="%d.%m.%Y %H:%M",
    )

    name: str = Field(..., description="Название мероприятия")
    start_datetime: datetime = Field(..., description="Дата и время начала мероприятия", example='20.01.2000 12:20')
    end_datetime: datetime = Field(..., description="Дата и время окончания мероприятия", example='20.01.2000 16:00')

    @field_validator("start_datetime", "end_datetime", mode="before")
    def parse_datetime(cls, value):
        if isinstance(value, datetime):
            # Если уже datetime, возвращаем как есть
            return value
        if isinstance(value, str):
            # Преобразуем строку в datetime
            try:
                return datetime.strptime(value, "%d.%m.%Y %H:%M")
            except ValueError:
                raise ValueError("Неверный формат даты. Используйте формат ДД.ММ.ГГГГ ЧЧ:ММ.")
        raise TypeError("Некорректный тип данных для даты")

    @model_validator(mode="before")
    def validate_event_dates(cls, values):
        if isinstance(values, str):
            try:
                values = json.loads(values)
            except json.JSONDecodeError:
                raise ValueError("Входные данные должны быть в формате JSON.")
        start = values.get('start_datetime')
        end = values.get('end_datetime')
        if start and end and start >= end:
            raise ValueError("Дата окончания должна быть позже даты начала.")
        return values

    @field_serializer("start_datetime", "end_datetime")
    def serialize_datetime(self, value: datetime, _info) -> str:
        return value.strftime("%d.%m.%Y %H:%M")

class EventCreate(EventBase):
    participants: List[int] | None = Field(
        default=None, description="ID сотрудников, которые будут участвовать в мероприятии"
    )

class EventInfo(EventBase):
    id:int = Field(...,description="Идентификатор мероприятия")
    video: str | None= Field(None, description="Ссылка на видео")

    participants_count:int = Field(...,description="Количество участников мероприятия")

    @field_serializer("start_datetime", "end_datetime")
    def serialize_datetime(self, value: datetime, _info) -> str:
        return value.strftime("%d.%m.%Y %H:%M")

class EventFullInfo(EventBase):
    id: int = Field(..., description="Идентификатор мероприятия")
    video: str |None= Field(None, description="Ссылка на видео")
    participants:List[EmployeeInfoPhoto] = Field(...,description="Участники мероприятия")

class EventUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Название мероприятия")
    start_datetime: datetime |None= Field(None, description="Дата и время начала мероприятия", example='20.01.2000 12:20')
    end_datetime: datetime |None= Field(None, description="Дата и время окончания мероприятия", example='20.01.2000 16:00')



class EventDeleteResponse(BaseModel):
    message: str = Field(..., example=SUCCESS_DELETE_EVENT)



class EmployeeFilterRequest(BaseModel):
    surname: Optional[str] = Field(None, description="Фамилия сотрудника")
    name: Optional[str] = Field(None, description="Имя сотрудника")
    patronymic: Optional[str] = Field(None, description="Отчество сотрудника")
    department: Optional[str] = Field(None, description="Название отдела")
    position: Optional[str] = Field(None, description="Название должности")

class EventFilterRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        datetime_format="%d.%m.%Y %H:%M",
    )
    page: int = Field(1, ge=1, description="Номер страницы")
    page_size: int = Field(10, ge=1, le=100, description="Количество элементов на странице")
    search: Optional[str] = Field(None, description="Поиск по названию мероприятия")
    date_from: Optional[datetime] = Field(None, description="Дата начала отрезка",example='20.01.2000 12:20')
    date_to: Optional[datetime] = Field(None, description="Дата окончания отрезка",example='20.01.2000 16:00')
    employee_data: Optional[EmployeeFilterRequest] = Field(
        None, description="Данные для фильтрации по сотруднику"
    )

    @field_validator("date_to", "date_from", mode="before")
    def parse_datetime(cls, value):
        if isinstance(value, datetime):
            # Если уже datetime, возвращаем как есть
            return value
        if isinstance(value, str):
            # Преобразуем строку в datetime
            try:
                return datetime.strptime(value, "%d.%m.%Y %H:%M")
            except ValueError:
                raise ValueError("Неверный формат даты. Используйте формат ДД.ММ.ГГГГ ЧЧ:ММ.")
        raise TypeError("Некорректный тип данных для даты")


class EventListResponse(BaseModel):
    total_count: int = Field(..., description="Общее количество найденных мероприятий")
    events: List[EventInfo] = Field(..., description="Список мероприятий")