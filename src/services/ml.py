import os
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette import status

from src.core.constant import FAIL_VALIDATION_MATCHED_EMPLOYEE
from src.models import Employee
from src.models.event import VisitInterval, IntervalEmployee, Event
from src.schemas.ml import Employee_visit, Unregistered_visit
from pathlib import Path
from fastapi import UploadFile, HTTPException


async def create_interval_and_add_employee(
    visit_info: Employee_visit,
    photo_file: UploadFile,
    db: AsyncSession,
):
    employee = await db.scalar(
        select(Employee).where(Employee.id == visit_info.employee_id)
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=FAIL_VALIDATION_MATCHED_EMPLOYEE,
        )
    # Определяем базовый путь для сохранения фото
    base_media_path = Path("media/intervals")
    event_folder = f"{visit_info.event_id}_{visit_info.order}"
    photo_folder = base_media_path / event_folder / "photo/employee"
    photo_folder.mkdir(parents=True, exist_ok=True)
    extension = os.path.splitext(photo_file.filename)[1]
    photo_path = photo_folder / f"{visit_info.employee_id}{extension}"

    event_start_datetime = await db.scalar(
        select(Event.start_datetime).where(Event.id == visit_info.event_id)
    )

    # Вычисляем начало и конец интервала
    interval_start = event_start_datetime + timedelta(minutes=5 * (visit_info.order))
    interval_end = interval_start + timedelta(minutes=5)
    visit_time = interval_start + visit_info.visit_time

    # Проверяем, существует ли интервал
    interval = await db.scalar(
        select(VisitInterval).where(
            VisitInterval.event_id == visit_info.event_id,
            VisitInterval.order == visit_info.order,
        )
    )

    # Если интервала нет, создаём новый
    if not interval:
        interval = VisitInterval(
            event_id=visit_info.event_id,
            order=visit_info.order,
            start_datetime=interval_start,
            end_datetime=interval_end,
            max_unregistered=0,
            max_unregistered_photo=None,
        )
        db.add(interval)
        await db.commit()  # Сохраняем изменения, чтобы интервал получил ID
        await db.refresh(interval)  # Обновляем объект для доступа к ID

    # Сохраняем файл фото
    with open(photo_path, "wb") as f:
        f.write(await photo_file.read())

    # Проверяем, существует ли запись о сотруднике в интервале
    existing_employee = await db.scalar(
        select(IntervalEmployee).where(
            IntervalEmployee.interval_id == interval.id,
            IntervalEmployee.employee_id == visit_info.employee_id,
        )
    )

    # Если сотрудника нет, добавляем его с указанием пути к фото
    if not existing_employee:
        interval_employee = IntervalEmployee(
            interval_id=interval.id,
            employee_id=visit_info.employee_id,
            photo=str(photo_path),
            first_spot_datetime=visit_time
        )
        db.add(interval_employee)
        await db.commit()

    return interval


async def add_unregistered_visit(
    visit_info: Unregistered_visit,
    file: UploadFile,
    db: AsyncSession,
):
    # Определяем базовый путь для хранения медиа
    base_media_path = Path("media/intervals")
    event_folder = f"{visit_info.event_id}_{visit_info.order}"
    photo_folder = base_media_path / event_folder / "photo/unregistered"
    photo_folder.mkdir(parents=True, exist_ok=True)

    event_start_datetime = await db.scalar(
        select(Event.start_datetime).where(Event.id == visit_info.event_id)
    )

    interval_start = event_start_datetime + timedelta(minutes=5 * (visit_info.order - 1))
    interval_end = interval_start + timedelta(minutes=5)
    # Проверяем, существует ли интервал
    interval = await db.scalar(
        select(VisitInterval).where(
            VisitInterval.event_id == visit_info.event_id,
            VisitInterval.order == visit_info.order,
        )
    )


    extension = Path(file.filename).suffix.lower()
    photo_path = photo_folder / f"unregistered_{visit_info.unregistered_max}{extension}"
    with open(photo_path, "wb") as f:
        f.write(await file.read())

    if not interval:
        # Если интервала нет, создаём новый
        interval = VisitInterval(
            event_id=visit_info.event_id,
            order=visit_info.order,
            start_datetime=interval_start,  # Здесь можно указать начальное время, если требуется
            end_datetime=interval_end,    # Здесь можно указать конечное время, если требуется
            max_unregistered=visit_info.unregistered_max,
            max_unregistered_photo=str(photo_path),
        )
        db.add(interval)
        await db.commit()
        await db.refresh(interval)

    # Сохраняем файл фото


    interval.max_unregistered = visit_info.unregistered_max
    interval.max_unregistered_photo = str(photo_path)
    db.add(interval)
    await db.commit()