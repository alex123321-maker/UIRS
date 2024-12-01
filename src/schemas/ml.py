from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from src.core.constant import SUCCESS_RESPONSE_ML


class MlResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )
    message: str = Field(..., example=SUCCESS_RESPONSE_ML)


class requestMlBase(BaseModel):
    event_id: int
    order: int
    sending_time: datetime

class Employee_visit(requestMlBase):
    employee_id: int
    visit_time: timedelta


class Unregistered_visit(requestMlBase):
    unregistered_max: int

