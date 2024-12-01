from datetime import timedelta, datetime

from fastapi import APIRouter, Depends, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_session
from src.api.dependencies.ml import validate_employee_visit
from src.core.constant import SUCCESS_RESPONSE_ML
from src.schemas.ml import MlResponse, Employee_visit, requestMlBase, Unregistered_visit
from src.services.ml import create_interval_and_add_employee,add_unregistered_visit

router = APIRouter(
    responses={
        200: {"description": "Успешный ответ", "model": MlResponse}
    }
)

@router.post("/employee_visit", response_model=MlResponse)
async def employee_visit(
    event_id: int = Form(..., description="ID мероприятия"),
    order: int = Form(..., description="Порядок интервала"),
    sending_time: datetime = Form(..., description="Время отправки"),
    employee_id: int = Form(..., description="ID сотрудника"),
    visit_time: int = Form(..., description="Время визита в секундах"),
    file: UploadFile = File(..., description="Фото сотрудника"),
    db: AsyncSession = Depends(get_session),
):
    # Формируем объект `Employee_visit` из данных формы
    visit_info = Employee_visit(
        event_id=event_id,
        order=order,
        sending_time=sending_time,
        employee_id=employee_id,
        visit_time=timedelta(seconds=visit_time),
    )
    await validate_employee_visit(
        requestMlBase(
            event_id=event_id,
            order=order,
            sending_time=sending_time
        ),
        db
    )
    # Создаём интервал и добавляем сотрудника
    await create_interval_and_add_employee(visit_info, file, db)

    return MlResponse(message=SUCCESS_RESPONSE_ML)

@router.post("/unregistered_visit", response_model=MlResponse)
async def unregistered_visit(
        event_id: int = Form(..., description="ID мероприятия"),
        order: int = Form(..., description="Порядок интервала"),
        sending_time: datetime = Form(..., description="Время отправки"),
        max_unregistered: int = Form(..., description="Максимальное количество незарегистрированных лиц в кадре"),
        file: UploadFile = File(..., description="Фото сотрудника"),
        db: AsyncSession = Depends(get_session),
):
    await validate_employee_visit(
        requestMlBase(
            event_id=event_id,
            order=order,
            sending_time=sending_time
        ),
        db
    )
    visit_info = Unregistered_visit(event_id=event_id, order=order, sending_time=sending_time, unregistered_max=max_unregistered)
    await add_unregistered_visit(visit_info, file, db)

    return MlResponse(message=SUCCESS_RESPONSE_ML)


