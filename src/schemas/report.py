from typing import List

from pydantic import BaseModel, Field, ConfigDict

from src.schemas.employee import EmployeeInfoPhoto
from src.schemas.event import EventBase, IntervalInfo
from src.schemas.ml import Unregistered_visit


class IntervalUnregisteredInfo(IntervalInfo):
    max_unregistered: int = Field(..., description="Максимальное количество не зарегистрированных")
    max_unregistered_photo: str | None

class IntervalFullInfo(IntervalInfo):
    photo: str
    first_spot_datetime: str = Field(..., description="Дата и время первого (для интервала) появления в кадре")
    employee_info: EmployeeInfoPhoto

class EmployeeVisit(EmployeeInfoPhoto):
    intervals: List[IntervalFullInfo]= Field(..., description="Интервалы присутствия")


class ReportResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )
    event_info: EventBase
    participants: List[EmployeeInfoPhoto] = Field(..., description="Участники мероприятия")
    visits: List[EmployeeVisit]
    unregistered: List[IntervalUnregisteredInfo]