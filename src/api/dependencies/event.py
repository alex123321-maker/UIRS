from sqlalchemy.future import select

from typing import List, Tuple

from fastapi import Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_session
from src.core.constant import  FAIL_VALIDATION_MATCHED_EVENT
from src.models import Employee, Event
from src.schemas.event import EventCreate

async def check_participants(
    event: EventCreate,
    db: AsyncSession = Depends(get_session),
) -> EventCreate:
    # Запрос к базе данных для проверки существующих ID
    query = select(Employee.id).where(Employee.id.in_(event.participants))
    result = await db.execute(query)
    existing_ids = {row[0] for row in result.fetchall()}

    # Определяем найденные и не найденные ID
    found_ids = list(existing_ids)
    missing_ids = list(set(event.participants) - existing_ids)
    if missing_ids:

        raise HTTPException(
            status_code=404,
            detail=f"Не нашли сотрудников с id: {missing_ids}"
        )
    return event



async def validate_event_exists(
    event_id: int, db: AsyncSession = Depends(get_session)
) -> Event:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail=FAIL_VALIDATION_MATCHED_EVENT)
    return event

