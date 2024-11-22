from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class ParticipantInfo(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )
    event_id:int = Field(...,description="ID мероприятия")
    # employee:EmployeeInfo = Field(...,description="Информация о сотруднике")


class EventBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        datetime_format="%d.%m.%Y %H:%M",
    )

    name:str = Field(...,description="Название мероприятия")
    start_datetime:datetime = Field(...,description="Дата и время начала мероприятия",example='20.01.2000 12:20')
    end_datetime:datetime = Field(...,description="Дата и время окончания мероприятия",example='20.01.2000 16:00')

    @field_validator("start_datetime", "end_datetime", mode="before")
    def parse_datetime(cls, value: str) -> datetime:
        try:
            return datetime.strptime(value, "%d.%m.%Y %H:%M")
        except ValueError:
            raise ValueError("Неверный формат даты. Используйте формат ДД.ММ.ГГГГ ЧЧ:ММ.")


class EventCreate(EventBase):
    participants: List[int] | None = Field(
        default=None, description="Участники мероприятия"
    )

class EventInfo(EventBase):
    id:int = Field(...,description="Идентификатор мероприятия")
    participants_count:int = Field(...,description="Количество участников мероприятия")

class EventFullInfo(EventBase):
    id: int = Field(..., description="Идентификатор мероприятия")
    participants:List[ParticipantInfo] = Field(...,description="Участники мероприятия")

