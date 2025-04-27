
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_session
from src.services.mealplan import get_plan_by_id

async def get_user_mealplan(
    plan_id: int,
    db: AsyncSession = Depends(get_session),
    user = Depends(get_current_user)
):
    plan = await get_plan_by_id(db, plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Такого плана не существует или вы не являетесь владельцем плана."
        )
    return plan
