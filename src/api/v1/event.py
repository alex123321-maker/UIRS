from typing import Annotated

from fastapi import APIRouter, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_session
from src.schemas.event import EventCreate
from src.schemas.user import UserFromDB

router = APIRouter()


@router.get("/" ,status_code=HTTP_200_OK)
async def get_event_list(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),
):
    ...

@router.post("/" ,status_code=HTTP_201_CREATED)
async def create_new_event(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),
    event: EventCreate = Form(...),

):
    ...

@router.post("/{event_id}/participant/" ,status_code=HTTP_201_CREATED)
async def add_participants_employee(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),

):
    ...
@router.delete("/{event_id}/participant/{participant_id}" ,status_code=HTTP_200_OK)
async def remove_participants_employee(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),

):
    ...
@router.patch("/{event_id}/participant/{participant_id}" ,status_code=HTTP_200_OK)
async def update_participants_employee(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),

):
    ...

@router.get("/{event_id}" ,status_code=HTTP_200_OK)
async def get_event(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),

):
    ...


@router.patch("/{event_id}" ,status_code=HTTP_200_OK)
async def update_event(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),

):
    ...

@router.delete("/{event_id}" ,status_code=HTTP_200_OK)
async def delete_event(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    db: AsyncSession = Depends(get_session),

):
    ...