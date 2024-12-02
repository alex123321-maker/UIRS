from typing import Annotated, List, Tuple, Union

from fastapi import APIRouter, Depends, Form, Body, UploadFile, File, Path, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_session
from src.api.dependencies.event import check_participants, validate_event_exists
from src.models import Event
from src.schemas.event import EventCreate, EventBase, EventFullInfo, EventUpdate, EventListResponse, EventFilterRequest
from src.schemas.user import UserFromDB
from src.services.event import create_event_in_db, delete_event_by_id, update_event_by_id, get_event_by_id, get_events, \
    add_participant_to_event, remove_participant_from_event, update_event_video

router = APIRouter()


@router.post("/list", response_model=EventListResponse)
async def list_events(
        auth_user: Annotated[UserFromDB, Depends(get_current_user)],
        filters: EventFilterRequest | None = Body(None),
        db: AsyncSession = Depends(get_session),
):
    # Если фильтры не переданы, задаем значения по умолчанию
    filters = filters or EventFilterRequest(page=1, page_size=10)

    return await get_events(
        db=db,
        page=filters.page,
        page_size=filters.page_size,
        search=filters.search,
        date_from=filters.date_from,
        date_to=filters.date_to,
        employee_data=filters.employee_data if filters.employee_data else None,
    )

@router.post("/", response_model=EventFullInfo, status_code=HTTP_201_CREATED)
async def create_new_event(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),
    event: EventCreate = Body(...),  # Явно указываем, что данные приходят в теле запроса
    video: UploadFile = File(None),
):
    # Проверка участников вынесена в обработчик
    await check_participants(event, db)
    created_event = await create_event_in_db(event, db, video)
    return created_event

@router.post("/{event_id}/participant/{employee_id}", status_code=HTTP_201_CREATED)
async def add_participants_employee(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    event: Event = Depends(validate_event_exists),
    employee_id: int = Path(...),
    db: AsyncSession = Depends(get_session),
):
    await add_participant_to_event(event.id, employee_id, db)
    return await get_event_by_id(event.id, db)


@router.delete("/{event_id}/participant/{employee_id}", status_code=HTTP_200_OK)
async def remove_participants_employee(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    event: Event = Depends(validate_event_exists),
    employee_id: int = Path(...),
    db: AsyncSession = Depends(get_session),
):
    await remove_participant_from_event(event.id, employee_id, db)
    return {"message": "Участник успешно удалён из мероприятия."}

@router.get("/{event_id}", response_model=EventFullInfo, status_code=HTTP_200_OK)
async def get_event(
    event: Event = Depends(validate_event_exists),
    auth_user: UserFromDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await get_event_by_id(event.id, db)

@router.patch("/{event_id}", response_model=EventFullInfo, status_code=HTTP_200_OK)
async def update_event(
    event_id: int,
    update_data: EventUpdate,
    event: Event = Depends(validate_event_exists),
    auth_user: UserFromDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await update_event_by_id(event_id, update_data, db)

@router.delete("/{event_id}", status_code=HTTP_200_OK)
async def delete_event(
    event: Event = Depends(validate_event_exists),
    auth_user: UserFromDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await delete_event_by_id(event.id, db)

@router.patch("/{event_id}/video", response_model=Union[EventFullInfo, dict], status_code=status.HTTP_200_OK)
async def update_event_video_endpoint(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    event: Event = Depends(validate_event_exists),
    db: AsyncSession = Depends(get_session),
    video: Union[UploadFile,str] = File(None),  # Файл может быть None
):
    """
    Добавляет, обновляет или удаляет видео для мероприятия.
    Если передан файл — добавляет или обновляет видео.
    Если файл не передан — удаляет видео.
    """
    if video:
        # Обработка добавления или изменения видео
        print(f"Добавление или изменение видео: {video.filename}")
        await update_event_video(event, video, db)
        return await get_event_by_id(event.id, db)

    # Обработка удаления видео
    print("Удаление видео")
    await update_event_video(event, None, db)
    return await get_event_by_id(event.id, db)
