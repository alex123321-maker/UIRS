from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_session
from src.core.constant import FAIL_VALIDATION_MATCHED_EVENT
from src.schemas.user import UserFromDB
from src.services.report import fetch_event_statistics

router = APIRouter()


@router.get('/event/{event_id}')
async def get_event_report(
    event_id: int,
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),

):
    try:
        return await fetch_event_statistics(event_id, db)
    except ValueError as e:
        # raise HTTPException(status_code=404, detail=FAIL_VALIDATION_MATCHED_EVENT)
        raise HTTPException(status_code=404, detail=str(e))
