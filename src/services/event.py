import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from sqlalchemy import or_, and_

from src.core.constant import SUCCESS_DELETE_EVENT
from src.database.events import logger
from src.schemas.event import EventCreate, EventFullInfo, EventDeleteResponse, EventInfo, EmployeeFilterRequest, \
    EventUpdate

from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError

from src.models import Event, PlannedParticipant, Employee, VisitInterval
from src.schemas.employee import EmployeeInfoPhoto, DepartmentInfo, PositionInfo, PhotoInfo
from src.schemas.event import EventCreate, EventFullInfo


async def save_video_file(video, event_id: int) -> str:
    """
    Сохраняет видеофайл на диск и возвращает путь к файлу.

    :param video: Загружаемый файл (UploadFile)
    :param event_id: ID мероприятия
    :return: Путь к сохраненному файлу
    """
    if not video:
        return None

    # Создаем директорию для хранения видео
    event_dir = Path(f"media/events/video/")
    event_dir.mkdir(parents=True, exist_ok=True)

    # Формируем имя файла и путь
    video_extension = video.filename.split(".")[-1]
    video_path = event_dir / f"{event_id}.{video_extension}"

    # Сохраняем видео
    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    return str(video_path)

async def create_event_in_db(
    event: EventCreate,
    db: AsyncSession,
    video: UploadFile = None,
) -> EventFullInfo:
    # Создаем событие
    new_event = Event(
        name=event.name,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
    )
    db.add(new_event)

    try:
        await db.commit()
        await db.refresh(new_event)

        # Добавляем участников
        if event.participants:
            participants_to_add = [
                PlannedParticipant(event_id=new_event.id, employee_id=participant_id)
                for participant_id in event.participants
            ]
            db.add_all(participants_to_add)
            await db.commit()
        if video:
            video_path = await save_video_file(video, new_event.id)
            new_event.video = video_path
            db.add(new_event)
            await db.commit()
        # Запрашиваем событие и связанные данные
        await db.refresh(new_event)
        return await get_event_by_id(new_event.id, db)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ошибка при добавлении мероприятия в базу данных",
        )

async def get_event_by_id(event_id: int, db: AsyncSession) -> EventFullInfo:
    # Запрос события с участниками
    result = await db.execute(
        select(Event)
        .options(
            joinedload(Event.participants).joinedload(PlannedParticipant.employee),
            joinedload(Event.participants).joinedload(PlannedParticipant.employee).joinedload(Employee.department),
            joinedload(Event.participants).joinedload(PlannedParticipant.employee).joinedload(Employee.position),
            joinedload(Event.participants).joinedload(PlannedParticipant.employee).joinedload(Employee.photos),
        )
        .where(Event.id == event_id)
    )
    event_with_data = result.scalars().first()

    if not event_with_data:
        raise HTTPException(status_code=404, detail="Событие не найдено")

    # Формируем список участников
    participants = [
        EmployeeInfoPhoto(
            id=participant.employee.id,
            name=participant.employee.name,
            surname=participant.employee.surname,
            patronymic=participant.employee.patronymic,
            department=DepartmentInfo(
                id=participant.employee.department.id,
                name=participant.employee.department.name,
            ) if participant.employee.department else None,
            position=PositionInfo(
                id=participant.employee.position.id,
                name=participant.employee.position.name,
            ) if participant.employee.position else None,
            photos=[
                PhotoInfo(id=photo.id, path=photo.photo)
                for photo in participant.employee.photos
            ],
        )
        for participant in event_with_data.participants
    ]

    return EventFullInfo(
        id=event_with_data.id,
        name=event_with_data.name,
        video=event_with_data.video,
        start_datetime=event_with_data.start_datetime,
        end_datetime=event_with_data.end_datetime,
        participants=participants,
    )
async def update_event_by_id(
    event_id: int,
    update_data: EventUpdate,
    db: AsyncSession
) -> EventFullInfo:
    # Получаем событие
    result = await db.execute(select(Event).where(Event.id == event_id))
    event_to_update = result.unique().scalar_one_or_none()

    if not event_to_update:
        raise HTTPException(status_code=404, detail="Событие не найдено")

    try:
        # Применяем обновления
        update_data_dict = update_data.model_dump(exclude_unset=True)  # Используем model_dump для Pydantic 2
        for key, value in update_data_dict.items():
            # Обрабатываем даты, если переданы в формате строки
            if key in ["start_datetime", "end_datetime"] and isinstance(value, str):
                value = datetime.strptime(value, "%d.%m.%Y %H:%M")
            setattr(event_to_update, key, value)  # Обновляем атрибут модели

        # Сохраняем изменения в базе данных
        await db.commit()
        await db.refresh(event_to_update)

        # Возвращаем обновленное мероприятие
        return await get_event_by_id(event_id, db)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка при обновлении события: {str(e)}"
        )

async def delete_event_by_id(event_id: int, db: AsyncSession):
    # Удаляем всех участников, связанных с событием
    result = await db.execute(
        select(Event)
        .options(
            joinedload(Event.visit_intervals).joinedload(VisitInterval.employees)
        )
        .where(Event.id == event_id)
    )
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    # Удаляем связанные файлы
    if event.video:
        try:
            os.remove(event.video)
        except FileNotFoundError:
            pass

    for interval in event.visit_intervals:
        if interval.max_unregistered_photo:
            try:
                os.remove(interval.max_unregistered_photo)
            except FileNotFoundError:
                pass

        for employee in interval.employees:
            if employee.photo:
                try:
                    os.remove(employee.photo)
                except FileNotFoundError:
                    pass

    # Удаляем мероприятие (каскадное удаление связанных записей)
    await db.delete(event)
    await db.commit()

    return EventDeleteResponse(message=SUCCESS_DELETE_EVENT)

async def get_events(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    employee_data: Optional[EmployeeFilterRequest] = None,
):
    # Базовый запрос для событий
    query = select(Event).options(
        joinedload(Event.participants).joinedload(PlannedParticipant.employee),
        joinedload(Event.participants).joinedload(PlannedParticipant.employee).joinedload(Employee.department),
        joinedload(Event.participants).joinedload(PlannedParticipant.employee).joinedload(Employee.position),
    )
    # Фильтрация по названию мероприятия
    if search:
        query = query.where(Event.name.ilike(f"%{search}%"))

    # Фильтрация по диапазону дат
    if date_from or date_to:
        if date_from and date_to:
            query = query.where(and_(
                Event.start_datetime >= date_from,
                Event.end_datetime <= date_to
            ))
        elif date_from:
            query = query.where(Event.start_datetime >= date_from)
        elif date_to:
            query = query.where(Event.end_datetime <= date_to)

    if employee_data:
        emp_conditions = []
        if employee_data.surname:
            emp_conditions.append(Employee.surname.ilike(f"%{employee_data.surname}%"))
        if employee_data.name:
            emp_conditions.append(Employee.name.ilike(f"%{employee_data.name}%"))
        if employee_data.patronymic:
            emp_conditions.append(Employee.patronymic.ilike(f"%{employee_data.patronymic}%"))
        if employee_data.department:
            emp_conditions.append(Employee.department.has(name=employee_data.department))
        if employee_data.position:
            emp_conditions.append(Employee.position.has(name=employee_data.position))

        if emp_conditions:
            query = query.join(Event.participants).join(PlannedParticipant.employee).where(and_(*emp_conditions))

    # Считаем общее количество результатов
    count_query = query.with_only_columns(Event.id)

    total_count_result = await db.execute(count_query)
    total_count = len(total_count_result.scalars().all())

    # Пагинация
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Выполнение запроса
    result = await db.execute(query)
    events = result.scalars().unique().all()

    # Формируем ответ
    return {
        "total_count": total_count,
        "events": [
            EventInfo(
                id=event.id,
                name=event.name,
                video = event.video,
                start_datetime=event.start_datetime,
                end_datetime=event.end_datetime,
                participants_count=len(event.participants),
            )
            for event in events
        ],
    }

async def add_participant_to_event(event_id: int, employee_id: int, db: AsyncSession):
    # Проверяем, существует ли участник уже
    query = select(PlannedParticipant).where(
        PlannedParticipant.event_id == event_id,
        PlannedParticipant.employee_id == employee_id,
    )
    result = await db.execute(query)
    existing_participant = result.scalars().first()

    if existing_participant:
        raise HTTPException(
            status_code=400, detail="Участник уже добавлен в мероприятие."
        )

    # Добавляем нового участника
    new_participant = PlannedParticipant(
        event_id=event_id,
        employee_id=employee_id,
    )
    db.add(new_participant)

    try:
        await db.commit()
        await db.refresh(new_participant)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при добавлении участника: {str(e)}"
        )

async def remove_participant_from_event(event_id: int, employee_id: int, db: AsyncSession):
    # Проверяем, существует ли участник
    query = select(PlannedParticipant).where(
        PlannedParticipant.event_id == event_id,
        PlannedParticipant.employee_id == employee_id,
    )
    result = await db.execute(query)
    participant = result.scalars().first()

    if not participant:
        raise HTTPException(
            status_code=404, detail="Участник не найден в мероприятии."
        )

    # Удаляем участника
    try:
        await db.delete(participant)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении участника: {str(e)}"
        )


async def update_event_video(event: Event, video: UploadFile | None, db: AsyncSession):
    """
    Обновляет видео для мероприятия. Если video = None, удаляет существующее видео.

    :param event: Экземпляр мероприятия
    :param video: Загружаемый файл или None
    :param db: Сессия базы данных
    """
    # Если передано новое видео
    if video:
        # Удаляем старое видео, если оно существует
        if event.video:
            try:
                os.remove(event.video)
            except FileNotFoundError:
                pass

        # Создаем путь для нового видео
        video_dir = "media/events/video/"
        os.makedirs(video_dir, exist_ok=True)
        video_extension = video.filename.split(".")[-1]
        video_path = os.path.join(video_dir, f"{event.id}.{video_extension}")

        # Сохраняем новое видео
        with open(video_path, "wb") as f:
            f.write(await video.read())

        # Обновляем путь в базе данных
        event.video = video_path
    else:
        # Если видео не передано, удаляем существующее
        if event.video:
            try:
                os.remove(event.video)
            except FileNotFoundError:
                pass
            event.video = None

    # Сохраняем изменения в базе
    try:
        db.add(event)
        await db.commit()
        await db.refresh(event)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении видео: {str(e)}"
        )