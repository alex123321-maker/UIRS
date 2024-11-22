from fastapi import APIRouter

from src.api.v1 import auth,user, employee, event

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
# api_router.include_router(event.router, prefix="/event", tags=["event"])
api_router.include_router(employee.router, prefix="/employee", tags=["employee"])
