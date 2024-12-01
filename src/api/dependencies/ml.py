from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_session
from src.core.constant import FAIL_VALIDATION_MATCHED_EVENT, FAIL_VALIDATION_MATCHED_EMPLOYEE, FAIL_USER_ALREADY_EXISTS, \
    FAIL_FORBIDDEN
from src.models import Event, Employee, IntervalEmployee, VisitInterval
from src.schemas.ml import Employee_visit, requestMlBase
from src.schemas.user import UserFromDB


def only_ml_access(
    current_user: Annotated[UserFromDB, Depends(get_current_user)]
):
    if current_user.id != -1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=FAIL_FORBIDDEN,
        )


async def validate_employee_visit(
    visit_info: requestMlBase,
    db: AsyncSession = Depends(get_session),
) -> requestMlBase:
    # Проверка существования ивента
    event = await db.scalar(
        select(Event).where(Event.id == visit_info.event_id)
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=FAIL_VALIDATION_MATCHED_EVENT,
        )

    # Проверка существования сотрудника



    # Возвращаем исходную информацию, если проверки пройдены
    return visit_info